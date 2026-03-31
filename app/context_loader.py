from __future__ import annotations

from pathlib import Path
from typing import Iterable


PYTHON_CONFIG_CANDIDATES = [
    "README.md",
    "README.rst",
    "README.txt",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements/base.txt",
    "setup.py",
    "setup.cfg",
    "tox.ini",
]

NODE_CONFIG_CANDIDATES = [
    "README.md",
    "README.mdx",
    "README.txt",
    "package.json",
    "tsconfig.json",
    "tsconfig.base.json",
    "jsconfig.json",
    "vite.config.ts",
    "vite.config.js",
    "next.config.js",
    "next.config.mjs",
    "webpack.config.js",
    "webpack.config.ts",
    "eslint.config.js",
    "eslint.config.mjs",
    ".eslintrc",
    ".eslintrc.js",
    ".eslintrc.cjs",
]

PYTHON_SUFFIXES = {".py"}
NODE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}


def _detect_repo_kinds(changed_files: Iterable[str]) -> set[str]:
    kinds: set[str] = set()
    for file_path in changed_files:
        suffix = Path(file_path).suffix.lower()
        if suffix in PYTHON_SUFFIXES:
            kinds.add("python")
        if suffix in NODE_SUFFIXES:
            kinds.add("node")
    return kinds


def _build_candidates(changed_files: Iterable[str]) -> list[str]:
    kinds = _detect_repo_kinds(changed_files)
    candidates: list[str] = []

    if "python" in kinds:
        candidates.extend(PYTHON_CONFIG_CANDIDATES)
    if "node" in kinds:
        candidates.extend(NODE_CONFIG_CANDIDATES)

    unique_candidates: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            unique_candidates.append(candidate)
            seen.add(candidate)
    return unique_candidates


def _format_context_entry(path: str, text: str) -> str:
    return f"File: {path}\n{text.strip()}"


def load_relevant_context(
    *,
    repo_path: str,
    changed_files: list[str],
    max_files: int,
    max_chars: int,
) -> list[tuple[str, str]]:
    if max_files <= 0 or max_chars <= 0:
        return []

    repo_root = Path(repo_path)
    changed_set = set(changed_files)
    remaining_chars = max_chars
    selected: list[tuple[str, str]] = []

    for relative_path in _build_candidates(changed_files):
        if relative_path in changed_set:
            continue

        candidate = repo_root / relative_path
        if not candidate.exists() or not candidate.is_file():
            continue

        text = candidate.read_text(encoding="utf-8").strip()
        if not text:
            continue

        formatted = _format_context_entry(relative_path, text)
        if len(formatted) > remaining_chars:
            if not selected:
                trimmed = formatted[:remaining_chars].rstrip()
                if trimmed:
                    selected.append((relative_path, trimmed))
            break

        selected.append((relative_path, text))
        remaining_chars -= len(formatted)

        if len(selected) >= max_files:
            break

    return selected
