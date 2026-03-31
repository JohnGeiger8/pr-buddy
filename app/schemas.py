from __future__ import annotations

import hashlib
import json
from typing import Any, List, Literal
from pydantic import BaseModel, Field


Severity = Literal["low", "medium", "high"]
Category = Literal["bug", "missing_test", "maintainability", "security"]
RiskLevel = Literal["low", "medium", "high"]
ConfidenceLevel = Literal["low", "medium", "high"]
RunStatus = Literal["reviewed", "skipped", "unchanged", "no_changes", "error"]


class Finding(BaseModel):
    file: str = Field(..., description="Path to the changed file")
    severity: Severity = Field(..., description="Severity of the issue")
    category: Category = Field(..., description="Type of issue")
    confidence: ConfidenceLevel = Field(..., description="Confidence in the finding")
    line_hint: str = Field(..., description="Approximate changed location")
    issue: str = Field(..., description="Short description of the problem")
    suggestion: str = Field(..., description="Practical recommendation")

    @property
    def label(self) -> str:
        if self.category == "missing_test":
            return "Missing tests"
        if self.confidence == "high":
            return "Likely bug"
        return "Possible issue"


class ReviewResult(BaseModel):
    summary: str = Field(..., description="Short overall summary")
    risk_level: RiskLevel = Field(..., description="Overall PR risk")
    findings: List[Finding] = Field(default_factory=list)
    missing_tests: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = Field(..., description="Confidence in this review")

    def normalized_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_markdown(self) -> str:
        lines: list[str] = []
        lines.append("## PR Review Agent")
        lines.append("")
        lines.append(f"**Summary:** {self.summary}")
        lines.append(f"**Overall Risk:** {self.risk_level}")
        lines.append(f"**Confidence:** {self.confidence}")
        lines.append("")

        if self.findings:
            lines.append("### Findings")
            lines.append("")
            for idx, finding in enumerate(self.findings, start=1):
                lines.append(
                    f"{idx}. **{finding.label}** (`{finding.severity}`) in `{finding.file}`"
                )
                lines.append(f"   - Location: {finding.line_hint}")
                lines.append(f"   - Issue: {finding.issue}")
                lines.append(f"   - Suggestion: {finding.suggestion}")
                lines.append("")
        else:
            lines.append("### Findings")
            lines.append("")
            lines.append("No high-signal findings identified in the provided diff.")
            lines.append("")

        lines.append("### Missing Tests")
        lines.append("")
        if self.missing_tests:
            for test in self.missing_tests:
                lines.append(f"- {test}")
        else:
            lines.append("- None identified")
        lines.append("")

        return "\n".join(lines)


class ReviewRun(BaseModel):
    status: RunStatus
    review: ReviewResult | None = None
    skip_reason: str | None = None
    message: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)

    def normalized_payload(self) -> dict[str, Any]:
        if self.review is not None:
            return {
                "status": self.status,
                "review": self.review.normalized_payload(),
            }

        return {
            "status": self.status,
            "skip_reason": self.skip_reason,
            "message": self.message,
        }

    def fingerprint(self) -> str:
        payload = json.dumps(self.normalized_payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_markdown(self) -> str:
        if self.review is not None:
            return self.review.to_markdown()

        lines = ["## PR Review Agent", ""]

        if self.status == "skipped":
            lines.append(f"Skipped review: {self.skip_reason or 'No reason provided.'}")
        elif self.status == "unchanged":
            lines.append(self.message or "Review output was unchanged, so no comment was posted.")
        elif self.status == "no_changes":
            lines.append(self.message or "No relevant changed files found.")
        else:
            lines.append(self.message or "The review did not produce a rendered result.")

        return "\n".join(lines)
