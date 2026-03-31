from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import main as main_module
from app.schemas import Finding, ReviewResult, ReviewRun


PATCH_TEXT = """diff --git a/app/main.py b/app/main.py
index 1111111..2222222 100644
--- a/app/main.py
+++ b/app/main.py
@@ -1,2 +1,2 @@
-old
+new
"""


def build_review_result() -> ReviewResult:
    return ReviewResult(
        summary="Looks good overall.",
        risk_level="low",
        confidence="medium",
        findings=[
            Finding(
                file="app/main.py",
                severity="low",
                category="bug",
                confidence="high",
                line_hint="1",
                issue="Guard clause missing.",
                suggestion="Add a simple guard clause.",
            )
        ],
        missing_tests=["Add a regression test for the updated branch."],
    )


class MainTests(unittest.TestCase):
    def test_patch_file_review_path_uses_context_and_writes_usage_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            patch_file = repo / "review.patch"
            patch_file.write_text(PATCH_TEXT, encoding="utf-8")
            usage_file = repo / "artifacts" / "usage.json"
            summary_file = repo / "artifacts" / "summary.md"

            args = SimpleNamespace(
                base="main",
                head="HEAD",
                repo_path=tmp_dir,
                config_file=".pr-buddy.yml",
                patch_file=str(patch_file),
                provider=None,
                model=None,
                max_diff_lines=None,
                max_output_tokens=None,
                post_comment=False,
                usage_output_file=str(usage_file),
                summary_output_file=str(summary_file),
                owner=None,
                repo=None,
                pr_number=None,
            )

            with (
                patch.object(main_module, "parse_args", return_value=args),
                patch.object(main_module, "load_dotenv"),
                patch.object(main_module, "load_text_file") as load_text_file,
                patch.object(main_module, "run_review", return_value=(build_review_result(), {
                    "provider": "anthropic",
                    "model": "claude-haiku-4-5",
                    "input_tokens": 100,
                    "output_tokens": 50,
                })) as run_review,
                patch.object(main_module, "load_relevant_context", return_value=[("README.md", "Context")]),
            ):
                load_text_file.side_effect = lambda path: (
                    "system prompt" if path == "prompts/system.txt"
                    else "repo rules" if path.endswith("config/review_rules.md")
                    else Path(path).read_text(encoding="utf-8")
                )

                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main_module.main()

            self.assertEqual(exit_code, 0)
            self.assertIn("Likely bug", stdout.getvalue())
            self.assertTrue(usage_file.exists())
            self.assertTrue(summary_file.exists())
            run_review.assert_called_once()

    def test_no_changed_files_emits_no_changes_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            usage_file = Path(tmp_dir) / "usage.json"
            args = SimpleNamespace(
                base="main",
                head="HEAD",
                repo_path=tmp_dir,
                config_file=".pr-buddy.yml",
                patch_file=None,
                provider=None,
                model=None,
                max_diff_lines=None,
                max_output_tokens=None,
                post_comment=False,
                usage_output_file=str(usage_file),
                summary_output_file=None,
                owner=None,
                repo=None,
                pr_number=None,
            )

            with (
                patch.object(main_module, "parse_args", return_value=args),
                patch.object(main_module, "load_dotenv"),
                patch.object(main_module, "load_text_file", side_effect=["system prompt", "repo rules"]),
                patch.object(main_module, "get_changed_files", return_value=[]),
            ):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main_module.main()

            self.assertEqual(exit_code, 0)
            self.assertIn("No relevant changed files found.", stdout.getvalue())
            self.assertIn('"status": "no_changes"', usage_file.read_text(encoding="utf-8"))

    def test_oversized_diff_reports_skip_and_suppressed_comment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            usage_file = Path(tmp_dir) / "usage.json"
            args = SimpleNamespace(
                base="main",
                head="HEAD",
                repo_path=tmp_dir,
                config_file=".pr-buddy.yml",
                patch_file=None,
                provider=None,
                model=None,
                max_diff_lines=None,
                max_output_tokens=None,
                post_comment=True,
                usage_output_file=str(usage_file),
                summary_output_file=None,
                owner="owner",
                repo="repo",
                pr_number=1,
            )

            with (
                patch.object(main_module, "parse_args", return_value=args),
                patch.object(main_module, "load_dotenv"),
                patch.object(main_module, "load_text_file", side_effect=["system prompt", "repo rules"]),
                patch.object(main_module, "get_changed_files", return_value=["app/main.py"]),
                patch.object(main_module, "get_diff_for_files", return_value="\n".join(str(i) for i in range(900))),
                patch.object(main_module, "sync_pr_comment", return_value=False),
            ):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main_module.main()

            self.assertEqual(exit_code, 0)
            self.assertIn("Review output was unchanged", stdout.getvalue())
            self.assertIn('"status": "unchanged"', usage_file.read_text(encoding="utf-8"))
            self.assertIn('"comment_action": "suppressed_unchanged"', usage_file.read_text(encoding="utf-8"))

    def test_maybe_sync_comment_returns_posted_and_suppressed_states(self) -> None:
        args = SimpleNamespace(
            post_comment=True,
            owner="owner",
            repo="repo",
            pr_number=1,
        )
        run = ReviewRun(status="skipped", skip_reason="Too large.")

        with patch.object(main_module, "sync_pr_comment", return_value=True):
            posted_run, posted_action = main_module.maybe_sync_comment(args, run)

        self.assertEqual(posted_run.status, "skipped")
        self.assertEqual(posted_action, "posted")

        with patch.object(main_module, "sync_pr_comment", return_value=False):
            unchanged_run, unchanged_action = main_module.maybe_sync_comment(args, run)

        self.assertEqual(unchanged_run.status, "unchanged")
        self.assertEqual(unchanged_action, "suppressed_unchanged")


if __name__ == "__main__":
    unittest.main()
