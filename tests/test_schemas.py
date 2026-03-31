from __future__ import annotations

import unittest

from app.schemas import Finding, ReviewResult, ReviewRun


class SchemaTests(unittest.TestCase):
    def test_finding_labels_reflect_confidence_and_category(self) -> None:
        likely_bug = Finding(
            file="app/main.py",
            severity="high",
            category="bug",
            confidence="high",
            line_hint="42",
            issue="Bug",
            suggestion="Fix it",
        )
        possible_issue = Finding(
            file="app/main.py",
            severity="medium",
            category="maintainability",
            confidence="low",
            line_hint="43",
            issue="Maybe a bug",
            suggestion="Check it",
        )
        missing_tests = Finding(
            file="tests/test_main.py",
            severity="low",
            category="missing_test",
            confidence="medium",
            line_hint="10",
            issue="No test coverage",
            suggestion="Add tests",
        )

        self.assertEqual(likely_bug.label, "Likely bug")
        self.assertEqual(possible_issue.label, "Possible issue")
        self.assertEqual(missing_tests.label, "Missing tests")

    def test_review_run_renders_non_review_states(self) -> None:
        skipped = ReviewRun(status="skipped", skip_reason="Diff exceeded 800 lines.")
        unchanged = ReviewRun(status="unchanged", message="Nothing materially changed.")

        self.assertIn("Skipped review", skipped.to_markdown())
        self.assertIn("Nothing materially changed.", unchanged.to_markdown())

    def test_review_result_markdown_uses_fixed_labels(self) -> None:
        result = ReviewResult(
            summary="Looks mostly good.",
            risk_level="medium",
            confidence="medium",
            findings=[
                Finding(
                    file="app/main.py",
                    severity="medium",
                    category="bug",
                    confidence="high",
                    line_hint="12",
                    issue="State can drift",
                    suggestion="Guard the branch",
                )
            ],
            missing_tests=["Add a regression test for the changed path."],
        )

        markdown = result.to_markdown()

        self.assertIn("Likely bug", markdown)
        self.assertIn("Missing Tests", markdown)


if __name__ == "__main__":
    unittest.main()
