from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.run_patch_evals import (
    discover_eval_bundles,
    extract_note_bullets,
    run_single_eval,
    write_summary_markdown,
)


class RunPatchEvalsTests(unittest.TestCase):
    def test_extract_note_bullets_reads_target_section(self) -> None:
        notes = """
## What a good review should catch
- Missing tests
- Regression risk

## What should NOT be flagged
- Style only
"""
        bullets = extract_note_bullets(notes, "What a good review should catch")
        self.assertEqual(bullets, ["Missing tests", "Regression risk"])

    def test_discover_eval_bundles_finds_patch_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            bundle_dir = Path(tmp_dir) / "demo_pr"
            bundle_dir.mkdir(parents=True)
            (bundle_dir / "pr.patch").write_text("diff --git", encoding="utf-8")
            (bundle_dir / "notes.md").write_text("# Notes", encoding="utf-8")

            bundles = discover_eval_bundles(Path(tmp_dir))

        self.assertEqual(len(bundles), 1)
        self.assertEqual(bundles[0].slug, "demo_pr")

    def test_run_single_eval_writes_outputs_and_summary_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            bundle_dir = base / "demo_pr"
            bundle_dir.mkdir(parents=True)
            patch_path = bundle_dir / "pr.patch"
            patch_path.write_text("diff --git", encoding="utf-8")
            notes_path = bundle_dir / "notes.md"
            notes_path.write_text(
                "\n".join(
                    [
                        "## What a good review should catch",
                        "- Missing tests",
                        "",
                        "## What should NOT be flagged",
                        "- Style only",
                    ]
                ),
                encoding="utf-8",
            )
            metadata_path = bundle_dir / "metadata.json"
            metadata_path.write_text(json.dumps({"title": "Demo PR"}), encoding="utf-8")
            output_dir = base / "results"

            def fake_run(command: list[str], capture_output: bool, text: bool, check: bool) -> SimpleNamespace:
                run_dir = output_dir / "demo_pr"
                run_dir.mkdir(parents=True, exist_ok=True)
                (run_dir / "usage.json").write_text(
                    json.dumps(
                        {
                            "status": "reviewed",
                            "comment_action": "not_requested",
                            "input_tokens": 10,
                            "output_tokens": 5,
                            "estimated_cost_usd": 0.000035,
                        }
                    ),
                    encoding="utf-8",
                )
                return SimpleNamespace(
                    returncode=0,
                    stdout="## PR Review Agent\n\n### Missing Tests\n\n- Missing tests\n",
                    stderr="",
                )

            with patch("scripts.run_patch_evals.subprocess.run", side_effect=fake_run):
                summary = run_single_eval(
                    bundle=discover_eval_bundles(base)[0],
                    output_dir=output_dir,
                    provider=None,
                    model=None,
                    max_diff_lines=None,
                    max_output_tokens=None,
                )

            self.assertEqual(summary["slug"], "demo_pr")
            self.assertEqual(summary["status"], "reviewed")
            self.assertTrue(summary["mentions_missing_tests"])
            self.assertTrue(summary["mentions_expected_phrase"])
            self.assertFalse(summary["mentions_forbidden_phrase"])

    def test_write_summary_markdown_creates_readable_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            write_summary_markdown(
                output_dir,
                [
                    {
                        "slug": "demo_pr",
                        "title": "Demo",
                        "exit_code": 0,
                        "status": "reviewed",
                        "comment_action": "posted",
                        "estimated_cost_usd": 0.0001,
                        "mentions_missing_tests": True,
                        "mentions_expected_phrase": True,
                        "mentions_forbidden_phrase": False,
                        "expected_catches": ["Missing tests"],
                        "forbidden_flags": ["Style only"],
                        "review_path": "/tmp/review.md",
                    }
                ],
            )

            summary_text = (output_dir / "summary.md").read_text(encoding="utf-8")

        self.assertIn("# Eval Summary", summary_text)
        self.assertIn("demo_pr", summary_text)


if __name__ == "__main__":
    unittest.main()
