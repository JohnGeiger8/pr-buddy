from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import requests


GITHUB_API_BASE = "https://api.github.com"
DEFAULT_OUTPUT_DIR = "evals/public_prs"
DEFAULT_MANIFEST = "scripts/pr_manifest.json"


@dataclass
class PRSpec:
    repo: str
    pr_number: int
    slug: str | None = None
    notes: str | None = None

    @property
    def owner(self) -> str:
        return self.repo.split("/")[0]

    @property
    def repo_name(self) -> str:
        return self.repo.split("/")[1]

    @property
    def safe_slug(self) -> str:
        if self.slug:
            return self.slug
        repo_slug = self.repo.replace("/", "__")
        return f"{repo_slug}__pr_{self.pr_number:04d}"


def load_manifest(path: Path) -> list[PRSpec]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    prs = raw.get("prs")
    if not isinstance(prs, list):
        raise ValueError("Manifest must contain a top-level 'prs' list.")

    items: list[PRSpec] = []
    for idx, item in enumerate(prs, start=1):
        try:
            repo = item["repo"]
            pr_number = int(item["pr_number"])
        except Exception as exc:
            raise ValueError(f"Invalid manifest entry at index {idx}: {item}") from exc

        items.append(
            PRSpec(
                repo=repo,
                pr_number=pr_number,
                slug=item.get("slug"),
                notes=item.get("notes"),
            )
        )
    return items


def github_session(token: str | None) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "User-Agent": "pr-review-agent-eval-downloader",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    return session


def sanitize_filename(value: str) -> str:
    value = value.strip().replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)


def fetch_pr_metadata(
    session: requests.Session,
    repo: str,
    pr_number: int,
    require_merged: bool = True,
) -> dict[str, Any]:
    url = f"{GITHUB_API_BASE}/repos/{repo}/pulls/{pr_number}"
    response = session.get(url, timeout=30)

    if response.status_code == 404:
        raise RuntimeError(f"PR not found: {repo}#{pr_number}")
    if response.status_code >= 300:
        raise RuntimeError(
            f"Failed to fetch metadata for {repo}#{pr_number}: "
            f"{response.status_code} {response.text}"
        )

    data = response.json()
    if "number" not in data or "diff_url" not in data:
        raise RuntimeError(f"Unexpected PR payload for {repo}#{pr_number}")

    if require_merged and not data.get("merged_at"):
        raise RuntimeError(f"PR is not merged: {repo}#{pr_number}")

    return data


def fetch_diff(session: requests.Session, diff_url: str) -> str:
    response = session.get(
        diff_url,
        headers={"Accept": "application/vnd.github.v3.diff"},
        timeout=60,
    )
    if response.status_code >= 300:
        raise RuntimeError(f"Failed to fetch diff: {response.status_code} {response.text}")

    diff_text = response.text
    if not diff_text.strip():
        raise RuntimeError("Downloaded diff was empty")

    return diff_text


def write_notes_stub(path: Path, metadata: dict[str, Any], spec: PRSpec) -> None:
    if path.exists():
        return

    body = f"""# Ground truth notes

Repo: {spec.repo}
PR: {spec.pr_number}
Title: {metadata.get("title", "")}
URL: {metadata.get("html_url", "")}

## Why this PR was selected
{spec.notes or "- Fill this in"}

## What a good review should catch
- Fill this in

## What humans actually caught
- Fill this in after reading discussion/comments

## What should NOT be flagged
- Fill this in

## What was missed (if anything)
- Fill this in

## Evaluation
- Caught key issues: yes / partial / no
- Noise level: low / medium / high
- Overall usefulness: 1-5
"""
    path.write_text(body, encoding="utf-8")


def save_pr_bundle(
    output_dir: Path,
    spec: PRSpec,
    metadata: dict[str, Any],
    diff_text: str,
) -> None:
    pr_dir = output_dir / spec.safe_slug
    pr_dir.mkdir(parents=True, exist_ok=True)

    patch_path = pr_dir / "pr.patch"
    meta_path = pr_dir / "metadata.json"
    notes_path = pr_dir / "notes.md"

    patch_path.write_text(diff_text, encoding="utf-8")
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    write_notes_stub(notes_path, metadata, spec)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download GitHub PR diffs for evals")
    parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST,
        help=f"Path to manifest JSON (default: {DEFAULT_MANIFEST})",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save diffs into (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Optional GitHub token. Recommended to avoid rate limits.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.25,
        help="Delay between requests to be polite (default: 0.25)",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        specs = load_manifest(manifest_path)
    except Exception as exc:
        print(f"ERROR: failed to load manifest: {exc}", file=sys.stderr)
        return 1

    session = github_session(args.token)

    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for spec in specs:
        label = f"{spec.repo}#{spec.pr_number}"
        print(f"Processing {label}...")

        try:
            metadata = fetch_pr_metadata(session, spec.repo, spec.pr_number, require_merged=True)            
            diff_text = fetch_diff(session, metadata["diff_url"])
            save_pr_bundle(output_dir, spec, metadata, diff_text)

            successes.append(
                {
                    "repo": spec.repo,
                    "pr_number": spec.pr_number,
                    "title": metadata.get("title"),
                    "html_url": metadata.get("html_url"),
                    "saved_to": str((output_dir / spec.safe_slug).resolve()),
                }
            )
            print(f"  OK: saved to {output_dir / spec.safe_slug}")
        except Exception as exc:
            failures.append(
                {
                    "repo": spec.repo,
                    "pr_number": spec.pr_number,
                    "error": str(exc),
                }
            )
            print(f"  FAILED: {exc}")

        time.sleep(args.sleep_seconds)

    (output_dir / "_download_successes.json").write_text(
        json.dumps(successes, indent=2),
        encoding="utf-8",
    )
    (output_dir / "_download_failures.json").write_text(
        json.dumps(failures, indent=2),
        encoding="utf-8",
    )

    print("")
    print(f"Done. Successes: {len(successes)} | Failures: {len(failures)}")
    print(f"Success log: {output_dir / '_download_successes.json'}")
    print(f"Failure log: {output_dir / '_download_failures.json'}")

    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())