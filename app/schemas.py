from __future__ import annotations

from typing import List, Literal
from pydantic import BaseModel, Field


Severity = Literal["low", "medium", "high"]
Category = Literal["bug", "missing_test", "maintainability", "security"]
RiskLevel = Literal["low", "medium", "high"]
ConfidenceLevel = Literal["low", "medium", "high"]


class Finding(BaseModel):
    file: str = Field(..., description="Path to the changed file")
    severity: Severity = Field(..., description="Severity of the issue")
    category: Category = Field(..., description="Type of issue")
    line_hint: str = Field(..., description="Approximate changed location")
    issue: str = Field(..., description="Short description of the problem")
    suggestion: str = Field(..., description="Practical recommendation")


class ReviewResult(BaseModel):
    summary: str = Field(..., description="Short overall summary")
    risk_level: RiskLevel = Field(..., description="Overall PR risk")
    findings: List[Finding] = Field(default_factory=list)
    missing_tests: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = Field(..., description="Confidence in this review")

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
                lines.append(f"{idx}. **{finding.category}** (`{finding.severity}`) in `{finding.file}`")
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