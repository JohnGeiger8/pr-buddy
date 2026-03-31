from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable


IGNORED_PATTERNS = [
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "dist/",
    "build/",
    "coverage/",
    ".next/",
    "*.snap",
    "*.min.js",
    "*.svg",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.webp",
    "*.ico",
    "*.pdf",
]


def run_git_command(args: list[str], repo_path: str = ".") -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=repo_path,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git command failed: {' '.join(args)}")
    return result.stdout


def get_changed_files(base_ref: str, head_ref: str, repo_path: str = ".") -> list[str]:
    output = run_git_command(["diff", "--name-only", f"{base_ref}...{head_ref}"], repo_path=repo_path)
    files = [line.strip() for line in output.splitlines() if line.strip()]
    return [f for f in files if not should_ignore_file(f)]


def should_ignore_file(file_path: str) -> bool:
    path = Path(file_path)

    for pattern in IGNORED_PATTERNS:
        if "/" in pattern and pattern.endswith("/"):
            if pattern.rstrip("/") in path.parts:
                return True
        elif path.match(pattern):
            return True
        elif file_path == pattern:
            return True

    return False


def get_diff_for_files(base_ref: str, head_ref: str, files: Iterable[str], repo_path: str = ".") -> str:
    file_list = list(files)
    if not file_list:
        return ""

    return run_git_command(
        ["diff", "--unified=3", f"{base_ref}...{head_ref}", "--", *file_list],
        repo_path=repo_path,
    )


def diff_line_count(diff_text: str) -> int:
    return len(diff_text.splitlines())


def is_diff_oversized(diff_text: str, max_lines: int = 800) -> bool:
    return diff_line_count(diff_text) > max_lines


def limit_diff_size(diff_text: str, max_lines: int = 800) -> str:
    lines = diff_text.splitlines()
    if len(lines) <= max_lines:
        return diff_text

    truncated = lines[:max_lines]
    truncated.append("")
    truncated.append(f"... [truncated after {max_lines} lines]")
    return "\n".join(truncated)
