# One Point Fixer — Setup & Operations

An opt-in system where **Claude** (via your Anthropic key) fixes **approved,
one-story-point** issues on a schedule. It works on **its own branch** and opens a
**draft** pull request for human review. It never commits to `main`, never merges,
and never deploys.

- Agent: [`scripts/one_point_fixer.py`](../scripts/one_point_fixer.py)
- Workflow: [`.github/workflows/one-point-fixer.yml`](../.github/workflows/one-point-fixer.yml)
- Shared helpers: [`scripts/github_utils.py`](../scripts/github_utils.py) · [`scripts/github_project.py`](../scripts/github_project.py)

## 1. What it does

On a schedule (or on demand) it finds one eligible issue in the **@akhilajags's
Resume** project (open, `Story Points == 1`, labelled `agent:approved`, no agent PR
yet), sends the issue plus the repository's source files to Claude, and asks for
the smallest surgical fix. Claude replies with one of four decisions:

- **implement** → the agent applies the edits on a new branch, runs cheap syntax
  checks, pushes, and opens a **draft** PR that `Closes #<issue>`.
- **needs_review** → the change is bigger than one point; it comments a recommended
  estimate and labels `agent:needs-review` (no PR).
- **needs_clarification** → it comments specific questions and labels
  `agent:needs-clarification` (no PR).
- **no_change** → it comments that nothing is needed and labels `agent:no-change`.

A human always decides: **approve & merge the draft PR, or close it and do it
yourself.**

## 2. The opt-in mechanism

Story Points = 1 establishes eligibility; the **`agent:approved`** label is the
explicit human permission. Only users who can apply labels can add it, so that
label is the opt-in gate. Remove it before the run to cancel.

## 3. Create the labels

Create these once (Issues → Labels), or let the workflow auto-create them:

| Label | Meaning |
|-------|---------|
| `agent:approved` | Maintainer opted this issue in |
| `agent:dispatched` | A draft PR was opened (prevents re-runs) |
| `agent:needs-review` | Claude judged it larger than one point |
| `agent:needs-clarification` | Claude needs more detail |
| `agent:no-change` | No production change required |

```bash
for l in approved dispatched needs-review needs-clarification no-change; do
  gh label create "agent:$l" --force
done
```

## 4–5. Approve an issue and set Story Points to 1

1. Add the issue to **@akhilajags's Resume**.
2. Set **Story Points** to **1** (the [story-point agent](story-point-agent.md) can
   do this, or set it by hand).
3. Add the **`agent:approved`** label.
4. Leave it open and wait for the schedule — or run it manually (below).

## 6. Change the scheduled time

Edit the `schedule` block in the workflow. Actions supports a per-schedule
`timezone` (IANA name) and handles daylight saving automatically:

```yaml
on:
  schedule:
    - cron: "30 9 * * 1-5"          # minute hour day-of-month month day-of-week
      timezone: "America/New_York"  # 9:30 AM Eastern, Mon–Fri
```

- **Minute / hour** — local time in `timezone`; keep the minute off `:00`.
- **Days** — `1-5` = Mon–Fri; `*` = every day.
- **Timezone** — any IANA name (`America/Los_Angeles`, `Europe/London`, …).

## 7. Run the workflow manually

**Actions → One Point Fixer → Run workflow.** Inputs:

- **issue_number** — optional; evaluate exactly this issue (never silently picks another).
- **dry_run** — default **true**; validate only.
- **force** — default **false**; for a specific issue, waive the `agent:approved` requirement.

## 8. Dry-run mode

With **dry_run = true** the workflow resolves the project, selects the eligible
issue, and prints a report — but makes **no model call** and **no** branch, PR, or
label change. Scheduled runs are never dry runs (the `true` default is only a
manual safety net). Example report:

```
Selected issue: #12
Story Points: 1
Approved: Yes
Existing PR: No
Action: Dry run
Reason: Eligible; dry_run=true so no model call, branch, PR, or label change.
```

## 9. Retry

- **A run failed (config/API):** fix the cause; `agent:approved` is left in place,
  so the next scheduled run retries. Or run manually with the **issue_number**.
- **Claude escalated** (`needs-review`/`needs-clarification`): address the comment,
  remove the escalation label, re-add `agent:approved`.
- **Force a specific issue now:** run manually with **issue_number** (+ **force**).

## 10. Revoke approval before the run

Remove `agent:approved`. With no approval, the issue is skipped.

## 11. How the tokens are used

| Token | Used for |
|-------|----------|
| `PROJECT_TOKEN` (classic PAT, `repo` + `project`) | Read the personal Project's `Story Points` field via GraphQL — the default token can't read user Projects |
| `ANTHROPIC_API_KEY` | Claude's reasoning and edits |
| `GITHUB_TOKEN` (workflow token) | Push the agent branch, open the draft PR, apply labels, comment |

Neither PAT is ever printed. The Anthropic key is only read inside the model call.
The workflow's `GITHUB_TOKEN` has `contents: write` + `pull-requests: write` +
`issues: write` — enough to push a **branch** and open a **draft** PR, but there is
no merge step and draft PRs can't be merged without a human.

## 12. Enable Claude

You already use `ANTHROPIC_API_KEY` for the classifier and story-point agents — no
extra setup. There is **no** Copilot/coding-agent product to enable; Claude runs
inside the Action itself. To change the model, edit `model="claude-sonnet-5"` in
[`one_point_fixer.py`](../scripts/one_point_fixer.py).

## 13. How the change is made (safety model)

- Claude only ever returns **surgical edits** (exact `old_string` → `new_string`),
  which the agent applies and must match uniquely — no blind full-file rewrites.
- The agent **hard-blocks** any edit to `.github/` or `scripts/`, any absolute path,
  and any path escaping the repo — so a prompt-injected issue can't alter the
  automation, workflows, or secrets. (Verified by unit tests.)
- Changed `.js`/`.json` files get a cheap syntax check before a PR is opened; a
  failure escalates to `agent:needs-review` instead of opening a broken PR.
- Issue text is treated as untrusted and is never interpolated into a shell.

## 14. Review the draft pull request

The PR is titled `[One Point Fixer] Fix #N: …`, is a **draft**, requests review
from `@akhilajags`, and has Summary / Changes / Validation / Risk / Review Notes
plus `Closes #N`. Review the diff, run it locally if you like, then **mark it ready
and merge** — or **close it** to reject and implement the change yourself.

## 15. Why it never merges automatically

The agent only opens a **draft** PR and never marks it ready, approves, or merges.
The workflow has no merge step, and a draft PR structurally requires a human to
merge. A person is always the final gate.

## 16. Troubleshooting

| Symptom | Likely cause & fix |
|---------|--------------------|
| `Project titled '…' not found` | Title mismatch or PROJECT_TOKEN can't see it; the error lists visible projects. |
| `Field 'Story Points' … not NUMBER` | Create a **Number** field named exactly `Story Points`. |
| `GraphQL HTTP 401/403` | PROJECT_TOKEN expired or missing `repo`/`project` scope. |
| `Model output rejected` | Claude returned off-spec JSON; the run fails without guessing. Re-run; if persistent, the issue may be too complex for one point. |
| PR not opened, `agent:needs-review` added | The edit couldn't apply cleanly or failed syntax check — read the issue comment and handle manually. |
| `git push` fails | Ensure checkout keeps credentials (default) and `contents: write` is granted. |
| Nothing happens on schedule | No eligible issue, or the workflow is disabled (§17). Check the run's report. |
| Duplicate PRs | Prevented by `agent:dispatched`, the open-PR/branch check, and the concurrency group. |

## 17. Disable the workflow completely

- **Temporarily:** Actions → One Point Fixer → **⋯ → Disable workflow**.
- **Permanently:** delete `.github/workflows/one-point-fixer.yml`, or comment out
  the `schedule:` block to keep only manual runs.

---

### Eligibility, at a glance

Selected only if **all** hold: open · in `akhilajags/jagarlapudi-resume` · an item
in **@akhilajags's Resume** · `Story Points == 1` · has `agent:approved` · lacks
`agent:dispatched` / `agent:needs-review` / `agent:needs-clarification` /
`agent:no-change` · no open agent PR/branch · not locked · a genuine issue (not a
PR). When several qualify, the **oldest** is chosen; **at most one** issue is
processed per run.
