from __future__ import annotations

import json
import os

import requests

from app.schemas import ReviewRun


METADATA_PREFIX = "<!-- pr-buddy:"
MANAGED_COMMENT_AUTHOR = "github-actions[bot]"


def _build_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def build_comment_metadata(run: ReviewRun) -> dict[str, str]:
    return {
        "status": run.status,
        "fingerprint": run.fingerprint(),
    }


def embed_comment_metadata(body: str, metadata: dict[str, str]) -> str:
    return f"{METADATA_PREFIX} {json.dumps(metadata, sort_keys=True)} -->\n{body}"


def extract_comment_metadata(body: str) -> dict[str, str] | None:
    first_line, _, _ = body.partition("\n")
    if not first_line.startswith(METADATA_PREFIX):
        return None

    raw_json = first_line.removeprefix(METADATA_PREFIX).removesuffix("-->").strip()
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    status = parsed.get("status")
    fingerprint = parsed.get("fingerprint")
    if not isinstance(status, str) or not isinstance(fingerprint, str):
        return None

    return {"status": status, "fingerprint": fingerprint}


def is_managed_comment(comment: dict) -> bool:
    body = comment.get("body", "")
    metadata = extract_comment_metadata(body) if isinstance(body, str) else None
    if metadata is None:
        return False

    user = comment.get("user")
    if not isinstance(user, dict):
        return False

    login = user.get("login")
    return login == MANAGED_COMMENT_AUTHOR


def find_latest_managed_comment(comments: list[dict]) -> dict | None:
    for comment in reversed(comments):
        if is_managed_comment(comment):
            return comment
    return None


def should_post_run(run: ReviewRun, comments: list[dict]) -> bool:
    latest_comment = find_latest_managed_comment(comments)
    if latest_comment is None:
        return True

    metadata = extract_comment_metadata(latest_comment.get("body", ""))
    if metadata is None:
        return True

    current = build_comment_metadata(run)
    return (
        metadata.get("status") != current["status"]
        or metadata.get("fingerprint") != current["fingerprint"]
    )


def list_pr_comments(
    owner: str,
    repo: str,
    pr_number: int,
    github_token: str | None = None,
) -> list[dict]:
    token = github_token or os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set")

    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    response = requests.get(url, headers=_build_headers(token), timeout=30)

    if response.status_code >= 300:
        raise RuntimeError(
            f"Failed to list PR comments: {response.status_code} {response.text}"
        )

    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError("Unexpected response while listing PR comments.")

    return payload


def post_pr_comment(
    owner: str,
    repo: str,
    pr_number: int,
    body: str,
    github_token: str | None = None,
) -> None:
    token = github_token or os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set")

    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = _build_headers(token)

    response = requests.post(url, headers=headers, json={"body": body}, timeout=30)

    if response.status_code >= 300:
        raise RuntimeError(
            f"Failed to post PR comment: {response.status_code} {response.text}"
        )


def sync_pr_comment(
    *,
    owner: str,
    repo: str,
    pr_number: int,
    run: ReviewRun,
    github_token: str | None = None,
) -> bool:
    comments = list_pr_comments(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        github_token=github_token,
    )
    if not should_post_run(run, comments):
        return False

    post_pr_comment(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        body=embed_comment_metadata(run.to_markdown(), build_comment_metadata(run)),
        github_token=github_token,
    )
    return True
