"""
Shared helpers for talking to the GitHub REST API from our agent scripts.
All three agents (classifier, story analyzer, PR agent) import from here.
"""
import os
import requests

GITHUB_API = "https://api.github.com"


def _headers(accept="application/vnd.github+json"):
    token = os.environ["GITHUB_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_repo():
    """Returns (owner, repo) from the GITHUB_REPOSITORY env var GitHub Actions sets automatically."""
    owner, repo = os.environ["GITHUB_REPOSITORY"].split("/")
    return owner, repo


def post_comment(issue_or_pr_number: int, body: str):
    """Posts a comment on an issue OR a pull request (PRs are just issues under the hood in the API)."""
    owner, repo = get_repo()
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_or_pr_number}/comments"
    resp = requests.post(url, headers=_headers(), json={"body": body})
    resp.raise_for_status()
    return resp.json()


def find_comment_by_marker(issue_or_pr_number: int, marker: str):
    """Returns the id of the first comment containing `marker`, or None if there isn't one."""
    owner, repo = get_repo()
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_or_pr_number}/comments"
    resp = requests.get(url, headers=_headers())
    resp.raise_for_status()
    for comment in resp.json():
        if marker in comment.get("body", ""):
            return comment["id"]
    return None


def update_comment(comment_id: int, body: str):
    """Edits an existing issue/PR comment in place."""
    owner, repo = get_repo()
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/comments/{comment_id}"
    resp = requests.patch(url, headers=_headers(), json={"body": body})
    resp.raise_for_status()
    return resp.json()


def upsert_comment(issue_or_pr_number: int, body: str, marker: str):
    """Updates the existing comment containing `marker` if one exists, otherwise posts a new comment."""
    comment_id = find_comment_by_marker(issue_or_pr_number, marker)
    if comment_id is not None:
        return update_comment(comment_id, body)
    return post_comment(issue_or_pr_number, body)


def ensure_label_exists(label: str, color: str = "ededed"):
    """Creates the label in the repo if it doesn't already exist. Safe to call every run."""
    owner, repo = get_repo()
    url = f"{GITHUB_API}/repos/{owner}/{repo}/labels/{label}"
    resp = requests.get(url, headers=_headers())
    if resp.status_code == 404:
        create_url = f"{GITHUB_API}/repos/{owner}/{repo}/labels"
        requests.post(create_url, headers=_headers(), json={"name": label, "color": color})


def add_label(issue_number: int, label: str):
    """Applies a label to an issue (creating the label first if needed)."""
    ensure_label_exists(label)
    owner, repo = get_repo()
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/labels"
    resp = requests.post(url, headers=_headers(), json={"labels": [label]})
    resp.raise_for_status()
    return resp.json()


def remove_label(issue_number: int, label: str):
    """Removes a label from an issue. No-ops if the label isn't present."""
    owner, repo = get_repo()
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/labels/{label}"
    resp = requests.delete(url, headers=_headers())
    if resp.status_code not in (200, 404):
        resp.raise_for_status()


def get_issue(issue_number: int) -> dict:
    """Fetches the full issue object (title, body, labels, ...) from the REST API.

    Used so agents can read fresh issue content on any trigger (including
    workflow_dispatch, where the event payload has no issue body).
    """
    owner, repo = get_repo()
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}"
    resp = requests.get(url, headers=_headers())
    resp.raise_for_status()
    return resp.json()


def get_issue_labels(issue_number: int) -> list:
    """Returns the current label names on an issue."""
    return [l["name"] for l in get_issue(issue_number).get("labels", [])]


def create_pull_request(title: str, head: str, base: str, body: str, draft: bool = True) -> dict:
    """Opens a pull request. Defaults to a draft so a human must mark it ready and merge."""
    owner, repo = get_repo()
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
    resp = requests.post(
        url,
        headers=_headers(),
        json={"title": title, "head": head, "base": base, "body": body, "draft": draft},
    )
    resp.raise_for_status()
    return resp.json()


def request_reviewers(pr_number: int, reviewers: list) -> None:
    """Requests review from the given users. Tolerates 422 (e.g. reviewer is the PR author)."""
    owner, repo = get_repo()
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers"
    resp = requests.post(url, headers=_headers(), json={"reviewers": reviewers})
    if resp.status_code not in (200, 201, 422):
        resp.raise_for_status()


def find_open_pr_for_branch_prefix(prefix: str):
    """Returns the first open PR whose head branch starts with `prefix`, else None.

    Used for idempotency: skip an issue that already has an agent-opened PR.
    """
    owner, repo = get_repo()
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
    resp = requests.get(url, headers=_headers(), params={"state": "open", "per_page": 100})
    resp.raise_for_status()
    for pr in resp.json():
        if pr["head"]["ref"].startswith(prefix):
            return pr
    return None


def get_pr_diff(pr_number: int, max_chars: int = 12000) -> str:
    """Fetches the unified diff for a PR, truncated so we don't blow the LLM context/cost on huge PRs."""
    owner, repo = get_repo()
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}"
    resp = requests.get(url, headers=_headers(accept="application/vnd.github.v3.diff"))
    resp.raise_for_status()
    diff = resp.text
    if len(diff) > max_chars:
        diff = diff[:max_chars] + "\n\n... [diff truncated for length] ..."
    return diff