from __future__ import annotations

import os
import requests


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
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    response = requests.post(url, headers=headers, json={"body": body}, timeout=30)

    if response.status_code >= 300:
        raise RuntimeError(
            f"Failed to post PR comment: {response.status_code} {response.text}"
        )