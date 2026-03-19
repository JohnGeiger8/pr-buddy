from __future__ import annotations

from pathlib import Path


def load_text_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def build_user_prompt(
    repo_rules: str,
    changed_files: list[str],
    diff_text: str,
    max_findings: int = 5,
    max_missing_tests: int = 3,
) -> str:
    changed_files_text = "\n".join(f"- {f}" for f in changed_files) if changed_files else "- None"

    schema_description = f"""
Return JSON with exactly this shape:

{{
  "summary": "string",
  "risk_level": "low | medium | high",
  "findings": [
    {{
      "file": "string",
      "severity": "low | medium | high",
      "category": "bug | missing_test | maintainability | security",
      "line_hint": "string",
      "issue": "string",
      "suggestion": "string"
    }}
  ],
  "missing_tests": ["string"],
  "confidence": "low | medium | high"
}}

Rules:
- Return at most {max_findings} findings
- Return at most {max_missing_tests} missing_tests entries
- Only include findings supported by the provided diff
- Keep summary to 1-3 sentences
- Return valid JSON only
""".strip()

    return f"""
Repository rules:
{repo_rules}

Changed files:
{changed_files_text}

Diff:
{diff_text}

{schema_description}
""".strip()