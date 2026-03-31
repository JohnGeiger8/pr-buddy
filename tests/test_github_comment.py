from __future__ import annotations

import unittest

from app.github_comment import (
    build_comment_metadata,
    embed_comment_metadata,
    extract_comment_metadata,
    is_managed_comment,
    should_post_run,
)
from app.schemas import Finding, ReviewResult, ReviewRun


def build_review_run() -> ReviewRun:
    return ReviewRun(
        status="reviewed",
        review=ReviewResult(
            summary="Looks okay.",
            risk_level="low",
            confidence="medium",
            findings=[
                Finding(
                    file="app/main.py",
                    severity="medium",
                    category="bug",
                    confidence="high",
                    line_hint="10",
                    issue="State mismatch",
                    suggestion="Guard the branch",
                )
            ],
            missing_tests=[],
        ),
    )


class GitHubCommentTests(unittest.TestCase):
    def test_metadata_round_trip(self) -> None:
        run = build_review_run()
        metadata = build_comment_metadata(run)
        body = embed_comment_metadata(run.to_markdown(), metadata)

        self.assertEqual(extract_comment_metadata(body), metadata)

    def test_should_not_post_when_latest_managed_comment_matches(self) -> None:
        run = build_review_run()
        comments = [
            {
                "body": embed_comment_metadata(
                    run.to_markdown(),
                    build_comment_metadata(run),
                )
                ,
                "user": {"login": "github-actions[bot]"},
            }
        ]

        self.assertFalse(should_post_run(run, comments))

    def test_should_post_when_status_changes(self) -> None:
        previous_run = ReviewRun(status="skipped", skip_reason="Diff exceeded 800 lines.")
        current_run = build_review_run()
        comments = [
            {
                "body": embed_comment_metadata(
                    previous_run.to_markdown(),
                    build_comment_metadata(previous_run),
                )
                ,
                "user": {"login": "github-actions[bot]"},
            }
        ]

        self.assertTrue(should_post_run(current_run, comments))

    def test_should_post_when_no_managed_comment_exists(self) -> None:
        run = build_review_run()
        comments = [{"body": "Human comment"}]

        self.assertTrue(should_post_run(run, comments))

    def test_metadata_marker_requires_expected_author(self) -> None:
        run = build_review_run()
        comment = {
            "body": embed_comment_metadata(
                run.to_markdown(),
                build_comment_metadata(run),
            ),
            "user": {"login": "octocat"},
        }

        self.assertFalse(is_managed_comment(comment))
        self.assertTrue(should_post_run(run, [comment]))


if __name__ == "__main__":
    unittest.main()
