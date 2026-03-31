from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.schemas import Finding, ReviewResult, ReviewRun
from app.usage_reporting import build_usage_report, estimate_cost_usd, write_job_summary, write_usage_report


class UsageReportingTests(unittest.TestCase):
    def test_estimate_cost_for_known_model(self) -> None:
        cost = estimate_cost_usd(
            provider="anthropic",
            model="claude-haiku-4-5",
            input_tokens=1000,
            output_tokens=500,
        )

        self.assertIsNotNone(cost)
        self.assertGreater(cost, 0.0)

    def test_build_usage_report_reads_run_usage(self) -> None:
        run = ReviewRun(
            status="reviewed",
            review=ReviewResult(
                summary="Looks good.",
                risk_level="low",
                confidence="high",
                findings=[
                    Finding(
                        file="app/main.py",
                        severity="low",
                        category="bug",
                        confidence="high",
                        line_hint="10",
                        issue="Guard clause missing",
                        suggestion="Add it",
                    )
                ],
                missing_tests=[],
            ),
            usage={
                "provider": "anthropic",
                "model": "claude-haiku-4-5",
                "input_tokens": 1200,
                "output_tokens": 300,
            },
        )

        report = build_usage_report(
            run=run,
            changed_files_count=2,
            diff_line_count=120,
            context_files_count=1,
            comment_action="posted",
        )

        self.assertEqual(report.status, "reviewed")
        self.assertEqual(report.input_tokens, 1200)
        self.assertEqual(report.output_tokens, 300)
        self.assertEqual(report.comment_action, "posted")
        self.assertIsNotNone(report.estimated_cost_usd)

    def test_usage_outputs_write_files(self) -> None:
        report = build_usage_report(
            run=ReviewRun(status="skipped", skip_reason="Too large."),
            changed_files_count=5,
            diff_line_count=900,
            context_files_count=0,
            comment_action="suppressed_unchanged",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            usage_path = Path(tmp_dir) / "usage.json"
            summary_path = Path(tmp_dir) / "summary.md"

            write_usage_report(str(usage_path), report)
            write_job_summary(str(summary_path), report)

            usage_payload = json.loads(usage_path.read_text(encoding="utf-8"))
            summary_text = summary_path.read_text(encoding="utf-8")

        self.assertEqual(usage_payload["status"], "skipped")
        self.assertIn("PR Review Agent Usage", summary_text)


if __name__ == "__main__":
    unittest.main()
