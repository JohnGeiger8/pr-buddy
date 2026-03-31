from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError


DEFAULT_CONFIG_FILE = ".pr-buddy.yml"


class AppConfig(BaseModel):
    provider: Literal["anthropic"] = "anthropic"
    model: str = "claude-haiku-4-5"
    max_diff_lines: int = Field(default=800, ge=1)
    max_output_tokens: int = Field(default=1400, ge=1)
    max_context_files: int = Field(default=4, ge=0)
    max_context_chars: int = Field(default=6000, ge=0)
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    rules_path: str = "config/review_rules.md"
    max_findings: int = Field(default=5, ge=0)
    max_missing_tests: int = Field(default=3, ge=0)


def _parse_scalar(value: str) -> Any:
    text = value.strip()
    if not text:
        return ""

    if text.startswith(("'", '"')) and text.endswith(("'", '"')) and len(text) >= 2:
        return text[1:-1]

    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None

    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        if line.startswith("-"):
            raise ValueError(
                f"Unsupported YAML list syntax on line {line_number}. "
                "Use key/value pairs in .pr-buddy.yml for now."
            )

        if ":" not in line:
            raise ValueError(f"Invalid config line {line_number}: {raw_line}")

        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Missing key on line {line_number}: {raw_line}")

        data[key] = _parse_scalar(value)

    return data


def load_app_config(repo_path: str = ".", config_file: str = DEFAULT_CONFIG_FILE) -> AppConfig:
    config_path = Path(repo_path) / config_file
    if not config_path.exists():
        return AppConfig()

    raw_data = parse_simple_yaml(config_path.read_text(encoding="utf-8"))

    try:
        return AppConfig.model_validate(raw_data)
    except ValidationError as exc:
        raise RuntimeError(f"Invalid config in {config_path}: {exc}") from exc
