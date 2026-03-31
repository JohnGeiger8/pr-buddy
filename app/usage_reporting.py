from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.schemas import ReviewRun


ANTHROPIC_PRICING_USD_PER_MILLION_TOKENS: dict[str, dict[str, float]] = {
    "claude-haiku-4-5": {
        "input": 1.0,
        "output": 5.0,
    }
}


class UsageReport(BaseModel):
    status: str
    provider: str | None = None
    model: str | None = None
    changed_files_count: int = Field(default=0, ge=0)
    diff_line_count: int = Field(default=0, ge=0)
    context_files_count: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    comment_action: str = "not_requested"

    def to_summary_markdown(self) -> str:
        cost_text = (
            f"${self.estimated_cost_usd:.6f}" if self.estimated_cost_usd is not None else "unavailable"
        )
        lines = [
            "## PR Review Agent Usage",
            "",
            f"- Status: `{self.status}`",
            f"- Provider: `{self.provider or 'n/a'}`",
            f"- Model: `{self.model or 'n/a'}`",
            f"- Changed files: `{self.changed_files_count}`",
            f"- Diff lines: `{self.diff_line_count}`",
            f"- Context files: `{self.context_files_count}`",
            f"- Input tokens: `{self.input_tokens}`",
            f"- Output tokens: `{self.output_tokens}`",
            f"- Estimated cost (USD): `{cost_text}`",
            f"- Comment action: `{self.comment_action}`",
        ]
        return "\n".join(lines)


def estimate_cost_usd(*, provider: str | None, model: str | None, input_tokens: int, output_tokens: int) -> float | None:
    if provider != "anthropic" or model is None:
        return None

    pricing = ANTHROPIC_PRICING_USD_PER_MILLION_TOKENS.get(model)
    if pricing is None:
        return None

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 8)


def build_usage_report(
    *,
    run: ReviewRun,
    changed_files_count: int,
    diff_line_count: int,
    context_files_count: int,
    comment_action: str,
) -> UsageReport:
    provider = run.usage.get("provider")
    model = run.usage.get("model")
    input_tokens = int(run.usage.get("input_tokens") or 0)
    output_tokens = int(run.usage.get("output_tokens") or 0)

    return UsageReport(
        status=run.status,
        provider=provider if isinstance(provider, str) else None,
        model=model if isinstance(model, str) else None,
        changed_files_count=changed_files_count,
        diff_line_count=diff_line_count,
        context_files_count=context_files_count,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimate_cost_usd(
            provider=provider if isinstance(provider, str) else None,
            model=model if isinstance(model, str) else None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
        comment_action=comment_action,
    )


def write_usage_report(path: str, report: UsageReport) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )


def write_job_summary(path: str, report: UsageReport) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report.to_summary_markdown() + "\n", encoding="utf-8")


def append_github_step_summary(report: UsageReport) -> None:
    import os

    raw_summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not raw_summary_path:
        return
    summary_path = Path(raw_summary_path)
    if not summary_path.exists():
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text("", encoding="utf-8")
    with summary_path.open("a", encoding="utf-8") as handle:
        handle.write(report.to_summary_markdown() + "\n")
