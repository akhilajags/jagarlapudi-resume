"""
GitHub Projects v2 (GraphQL) helpers for the story-point estimation agent.

These talk to the GraphQL API using PROJECT_TOKEN — a personal access token with
permission to read/write the user's Projects. The default GITHUB_TOKEN cannot
modify user-owned (personal) Projects, which is why a separate token is required.

Node IDs (project, field, item) are always discovered dynamically; nothing is
hardcoded. Tokens are never logged.
"""
import os

import requests

GRAPHQL_URL = "https://api.github.com/graphql"


class ProjectError(RuntimeError):
    """Raised when a project, field, or item can't be found or updated."""


def _token() -> str:
    token = os.environ.get("PROJECT_TOKEN")
    if not token:
        raise ProjectError(
            "PROJECT_TOKEN is not set. Create a personal access token with "
            "Projects read/write access and store it as the PROJECT_TOKEN secret."
        )
    return token


def graphql(query: str, variables: dict) -> dict:
    resp = requests.post(
        GRAPHQL_URL,
        headers={"Authorization": f"Bearer {_token()}"},
        json={"query": query, "variables": variables},
        timeout=30,
    )
    # Surface HTTP-level auth/scope problems clearly without echoing the token.
    if resp.status_code in (401, 403):
        raise ProjectError(
            f"PROJECT_TOKEN was rejected (HTTP {resp.status_code}). Check that the "
            "token is valid and has Projects (read & write) permission for the owner."
        )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("errors"):
        raise ProjectError(f"GraphQL error: {payload['errors']}")
    return payload["data"]


def find_user_project(login: str, title: str) -> str:
    """Returns the node ID of the personal project owned by `login` titled `title`."""
    query = """
    query($login: String!, $cursor: String) {
      user(login: $login) {
        projectsV2(first: 50, after: $cursor) {
          nodes { id title }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
    """
    cursor = None
    seen = []
    while True:
        data = graphql(query, {"login": login, "cursor": cursor})
        user = data.get("user")
        if not user:
            raise ProjectError(
                f"No user found with login '{login}'. Verify the owner and that "
                "PROJECT_TOKEN belongs to (or can see) that account."
            )
        projects = user["projectsV2"]
        for node in projects["nodes"]:
            seen.append(node["title"])
            if node["title"] == title:
                return node["id"]
        if projects["pageInfo"]["hasNextPage"]:
            cursor = projects["pageInfo"]["endCursor"]
        else:
            break
    raise ProjectError(
        f"Project titled '{title}' not found for user '{login}'. "
        f"Projects visible to PROJECT_TOKEN: {seen or '(none)'}."
    )


def find_number_field(project_id: str, field_name: str) -> str:
    """Returns the node ID of the NUMBER field named `field_name` on the project."""
    query = """
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 100) {
            nodes { ... on ProjectV2FieldCommon { id name dataType } }
          }
        }
      }
    }
    """
    data = graphql(query, {"projectId": project_id})
    node = data.get("node") or {}
    fields = [f for f in node.get("fields", {}).get("nodes", []) if f]
    for field in fields:
        if field.get("name") == field_name:
            if field.get("dataType") != "NUMBER":
                raise ProjectError(
                    f"Field '{field_name}' exists but has type {field.get('dataType')}, "
                    "not NUMBER. Story points must be stored in a number field."
                )
            return field["id"]
    raise ProjectError(
        f"Number field '{field_name}' not found on the project. "
        f"Available fields: {[f.get('name') for f in fields]}."
    )


def get_issue_node_and_item(owner, repo, issue_number, project_id, field_name):
    """Returns (issue_node_id, item_id_or_None, current_value_or_None).

    item_id is None when the issue is not yet an item in the project.
    current_value is None when the item exists but the number field is unset.
    """
    query = """
    query($owner: String!, $repo: String!, $number: Int!, $fieldName: String!) {
      repository(owner: $owner, name: $repo) {
        issue(number: $number) {
          id
          projectItems(first: 50) {
            nodes {
              id
              project { id }
              value: fieldValueByName(name: $fieldName) {
                ... on ProjectV2ItemFieldNumberValue { number }
              }
            }
          }
        }
      }
    }
    """
    data = graphql(
        query,
        {"owner": owner, "repo": repo, "number": issue_number, "fieldName": field_name},
    )
    repository = data.get("repository") or {}
    issue = repository.get("issue")
    if not issue:
        raise ProjectError(
            f"Issue #{issue_number} not found in {owner}/{repo}, or PROJECT_TOKEN "
            "cannot read it."
        )
    for item in issue["projectItems"]["nodes"]:
        if item.get("project", {}).get("id") == project_id:
            value = item.get("value") or {}
            return issue["id"], item["id"], value.get("number")
    return issue["id"], None, None


def list_project_issues(project_id: str, field_name: str) -> list:
    """Returns every issue in the project with its Story Points value and issue metadata.

    Each element: {number, node_id, story_points, state, locked, created_at, url,
    repo, labels}. Pull requests and draft items are skipped.
    """
    query = """
    query($projectId: ID!, $fieldName: String!, $cursor: String) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100, after: $cursor) {
            pageInfo { hasNextPage endCursor }
            nodes {
              value: fieldValueByName(name: $fieldName) {
                ... on ProjectV2ItemFieldNumberValue { number }
              }
              content {
                __typename
                ... on Issue {
                  number title state locked createdAt url
                  repository { nameWithOwner }
                  labels(first: 50) { nodes { name } }
                }
              }
            }
          }
        }
      }
    }
    """
    cursor = None
    issues = []
    while True:
        data = graphql(query, {"projectId": project_id, "fieldName": field_name, "cursor": cursor})
        items = (data.get("node") or {}).get("items")
        if not items:
            break
        for item in items["nodes"]:
            content = item.get("content") or {}
            if content.get("__typename") != "Issue":
                continue
            value = item.get("value") or {}
            issues.append(
                {
                    "number": content["number"],
                    "title": content["title"],
                    "story_points": value.get("number"),
                    "state": content["state"],
                    "locked": content["locked"],
                    "created_at": content["createdAt"],
                    "url": content["url"],
                    "repo": (content.get("repository") or {}).get("nameWithOwner"),
                    "labels": [l["name"] for l in content.get("labels", {}).get("nodes", [])],
                }
            )
        if items["pageInfo"]["hasNextPage"]:
            cursor = items["pageInfo"]["endCursor"]
        else:
            break
    return issues


def add_item_to_project(project_id: str, content_id: str) -> str:
    """Adds an issue (by its node ID) to the project; returns the new item ID."""
    mutation = """
    mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
        item { id }
      }
    }
    """
    data = graphql(mutation, {"projectId": project_id, "contentId": content_id})
    return data["addProjectV2ItemById"]["item"]["id"]


def set_number_field(project_id: str, item_id: str, field_id: str, value) -> None:
    """Writes `value` into the given number field.

    Story points are whole Fibonacci numbers, so send an integer (e.g. 3, not
    3.0). GraphQL still declares the argument as Float! (the field's type) and
    coerces the integer, so the stored value has no trailing decimal.
    """
    numeric = int(value) if float(value).is_integer() else float(value)
    mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: Float!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId,
        itemId: $itemId,
        fieldId: $fieldId,
        value: { number: $value }
      }) { projectV2Item { id } }
    }
    """
    graphql(
        mutation,
        {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": field_id,
            "value": numeric,
        },
    )
