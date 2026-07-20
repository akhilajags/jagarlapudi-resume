# Story-Point Estimator Agent — Setup & Operations

An automated agent that reviews each GitHub issue against the current repository,
estimates its relative complexity on a Fibonacci scale, and writes the value into
the numeric **Story Points** field of the personal GitHub Project
**@akhilajags's Resume**.

- Workflow: [`.github/workflows/estimate-story-points.yml`](../.github/workflows/estimate-story-points.yml)
- Agent script: [`scripts/estimate_story_points.py`](../scripts/estimate_story_points.py)
- Project (GraphQL) helpers: [`scripts/github_project.py`](../scripts/github_project.py)

The agent **never** modifies application code, creates branches, or opens PRs. It
only reads the repo, analyzes the issue, updates the Project field, and posts one
explanatory comment.

---

## 1. Create the `PROJECT_TOKEN` secret

The default `GITHUB_TOKEN` **cannot update user-owned (personal) Projects**, so a
personal access token is required for the GraphQL Project mutations.

**Fine-grained PAT (recommended)**
1. GitHub → Settings → Developer settings → **Fine-grained tokens** → *Generate new token*.
2. Resource owner: **akhilajags**.
3. Permissions:
   - **Account permissions → Projects: Read and write** (required).
   - **Repository permissions → Issues: Read and write** and **Contents: Read** (so the
     token can resolve the issue node and read the repo through GraphQL).
4. Generate and copy the token.

**Classic PAT (alternative):** create a token with the **`project`** scope (and
**`repo`** for private repos).

**Store it as a secret**
- Repo → Settings → Secrets and variables → **Actions** → *New repository secret*.
- Name: **`PROJECT_TOKEN`**, value: the token.

You also need the existing **`ANTHROPIC_API_KEY`** secret (already used by the
classifier agent). `GITHUB_TOKEN` is provided automatically by Actions.

## 2. Required token scope / permissions (summary)

| Token | Scope / permission | Why |
|-------|--------------------|-----|
| `PROJECT_TOKEN` | Projects: read & write | Add issue to project + set the number field |
| `PROJECT_TOKEN` | Issues: read, Contents: read | Resolve the issue node & repo via GraphQL |
| `ANTHROPIC_API_KEY` | — | Model inference for the estimate |
| `GITHUB_TOKEN` (auto) | `issues: write`, `contents: read` | Comments, labels, checkout (set in the workflow) |

## 3. "GitHub AI model access"

This agent uses the **Anthropic API** directly (same pattern as the issue
classifier), so there is nothing to enable in GitHub Models — you only need the
`ANTHROPIC_API_KEY` secret. If you later switch to GitHub Models, you would add
`models: read` to the workflow permissions and enable Models for the repo instead.

## 4. Prerequisites in the Project

- The project **@akhilajags's Resume** must exist and be owned by `akhilajags`.
- It must have a **number** field named exactly **`Story Points`**
  (Project → **+** → New field → *Number*). The agent fails with a clear message
  if the field is missing or is not a number field.

---

## 5. Test with a single issue

1. Open a new issue (e.g. *"Left arrow key doesn't move Mario on mobile"*).
2. The workflow runs on `opened`. Check **Actions → Story-Point Estimator Agent**.
3. Confirm:
   - a bot comment appears with the estimate, reason, confidence, and relevant files;
   - the issue shows up in the project with **Story Points** set.

You can also run it on demand: **Actions → Story-Point Estimator Agent → Run
workflow**, enter the **issue number**, leave the toggles off.

## 6. Request a re-estimate

By design, an existing Story Points value is **not** overwritten on ordinary issue
edits. To force a fresh estimate:

- **Add the `re-estimate` label** to the issue. The agent recomputes, overwrites
  the value, and then removes the label; **or**
- **Run workflow** manually and set **`force_reestimate = true`**.

## 7. Dry-run mode

To preview an estimate without changing the Project field:

- **Actions → Run workflow →** set **`dry_run = true`** and enter the issue number.

The agent posts (or updates) its comment with a *"Dry run: the Story Points field
was NOT updated"* note and touches nothing in the Project.

---

## 8. Troubleshooting project / permission errors

| Symptom | Likely cause & fix |
|---------|--------------------|
| `PROJECT_TOKEN is not set` | Add the `PROJECT_TOKEN` repository secret (step 1). |
| `PROJECT_TOKEN was rejected (HTTP 401/403)` | Token expired or missing **Projects: read & write**. Regenerate. |
| `Project titled '…' not found` | Title mismatch, or token can't see the project. The error lists the projects it *can* see — match `PROJECT_TITLE` in the workflow exactly. |
| `Number field 'Story Points' not found` | Create a **Number** field named exactly `Story Points`; the error lists existing fields. |
| `Field 'Story Points' … not NUMBER` | The field exists but isn't a number field. Recreate it as *Number*. |
| `Issue #N not found …` | Wrong issue number on dispatch, or token can't read the issue. |
| Comment posts but field never updates | Almost always `PROJECT_TOKEN` scope. Confirm **Projects: read & write** for owner `akhilajags`. |
| Value present, edits don't change it | Expected — use the `re-estimate` label or `force_reestimate`. |

**Notes**
- Tokens are never printed to logs.
- Malformed or non-Fibonacci model output fails the run instead of guessing.
- Issue text is treated as untrusted: the model is told to ignore instructions
  inside it, and issue text is never passed to a shell or `eval`.
