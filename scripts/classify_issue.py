"""
Agent 1 - Issue Classifier
Reads the issue title/body, asks Claude to classify it, and applies a matching label.
Triggered by: .github/workflows/issue-classifier.yml on issues [opened, edited]
"""
import json
import os

import anthropic
from github_utils import add_label, get_issue_labels, remove_label, upsert_comment

ALLOWED_LABELS = ["feature", "bug", "refactor", "docs", "question", "chore"]
COMMENT_MARKER = "🤖 **Issue Classifier Agent**"

SYSTEM_PROMPT = f"""You are an issue triage assistant for a software project.
Classify the GitHub issue into exactly one of these categories: {', '.join(ALLOWED_LABELS)}.

Respond with ONLY valid JSON, no markdown fences, no extra text, in this exact shape:
{{"label": "one of the allowed categories", "confidence": 0.0-1.0, "reasoning": "one short sentence"}}
"""


def classify(title: str, body: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Title: {title}\n\nBody:\n{body or '(no description provided)'}"}
        ],
    )
    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model did not return valid JSON: {text!r}") from exc

    label = str(result.get("label", "")).strip().lower()
    if label not in ALLOWED_LABELS:
        raise ValueError(f"Model returned an unexpected label: {label!r}")
    result["label"] = label
    return result


def main():
    issue_number = int(os.environ["ISSUE_NUMBER"])
    title = os.environ.get("ISSUE_TITLE", "")
    body = os.environ.get("ISSUE_BODY", "")

    try:
        result = classify(title, body)
    except ValueError as exc:
        print(f"Skipping label application: {exc}")
        return

    label = result["label"]

    # Reclassification on `edited` can change the label; drop any other
    # classifier-owned label first so they don't pile up on the issue.
    for existing in get_issue_labels(issue_number):
        if existing in ALLOWED_LABELS and existing != label:
            remove_label(issue_number, existing)

    add_label(issue_number, label)
    print(f"Applied label '{label}' (confidence {result.get('confidence')}) to issue #{issue_number}")

    # Leave a short, transparent comment so humans can see the agent's reasoning and correct it if wrong.
    # Re-edits update this same comment in place rather than piling up new ones.
    comment = (
        f"{COMMENT_MARKER}\n\n"
        f"Classified this as **`{label}`** (confidence: {result.get('confidence', 'n/a')}).\n"
        f"> {result.get('reasoning', '')}\n\n"
        f"_If this is wrong, just change the label — the agent won't overwrite manual edits._"
    )
    upsert_comment(issue_number, comment, COMMENT_MARKER)


if __name__ == "__main__":
    main()