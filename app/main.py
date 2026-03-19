from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from app.diff_reader import get_changed_files, get_diff_for_files, limit_diff_size
from app.github_comment import post_pr_comment
from app.prompt_builder import build_user_prompt, load_text_file
from app.reviewer import run_review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cheap PR Review Agent")

    parser.add_argument("--base", default="main", help="Base git ref (default: main)")
    parser.add_argument("--head", default="HEAD", help="Head git ref (default: HEAD)")
    parser.add_argument(
        "--model",
        default="claude-3-5-haiku-latest",
        help="Anthropic model name",
    )
    parser.add_argument(
        "--max-diff-lines",
        type=int,
        default=800,
        help="Maximum diff lines sent to model",
    )
    parser.add_argument(
        "--post-comment",
        action="store_true",
        help="Post result as GitHub PR comment",
    )
    parser.add_argument("--owner", help="GitHub repo owner")
    parser.add_argument("--repo", help="GitHub repo name")
    parser.add_argument("--pr-number", type=int, help="GitHub PR number")

    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()

    try:
        system_prompt = load_text_file("prompts/system.txt")
        repo_rules = load_text_file("config/review_rules.md")

        changed_files = get_changed_files(args.base, args.head)
        if not changed_files:
            print("No relevant changed files found.")
            return 0

        diff_text = get_diff_for_files(args.base, args.head, changed_files)
        if not diff_text.strip():
            print("No diff content found after filtering.")
            return 0

        diff_text = limit_diff_size(diff_text, max_lines=args.max_diff_lines)

        user_prompt = build_user_prompt(
            repo_rules=repo_rules,
            changed_files=changed_files,
            diff_text=diff_text,
        )

        review = run_review(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=args.model,
        )

        markdown = review.to_markdown()
        print(markdown)

        if args.post_comment:
            missing = [name for name in ("owner", "repo", "pr_number") if getattr(args, name) is None]
            if missing:
                raise RuntimeError(
                    f"--post-comment requires: {', '.join('--' + m.replace('_', '-') for m in missing)}"
                )

            post_pr_comment(
                owner=args.owner,
                repo=args.repo,
                pr_number=args.pr_number,
                body=markdown,
                github_token=os.getenv("GITHUB_TOKEN"),
            )
            print("\nPosted review as GitHub PR comment.")

        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())