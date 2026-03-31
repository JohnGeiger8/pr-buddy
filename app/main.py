from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.config import DEFAULT_CONFIG_FILE, load_app_config
from app.context_loader import load_relevant_context
from app.diff_reader import diff_line_count, get_changed_files, get_diff_for_files, is_diff_oversized
from app.github_comment import sync_pr_comment
from app.prompt_builder import build_user_prompt, load_text_file
from app.providers import DEFAULT_MODEL, DEFAULT_PROVIDER
from app.reviewer import run_review
from app.schemas import ReviewRun
from app.usage_reporting import append_github_step_summary, build_usage_report, write_job_summary, write_usage_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cheap PR Review Agent")

    parser.add_argument("--base", default="main", help="Base git ref (default: main)")
    parser.add_argument("--head", default="HEAD", help="Head git ref (default: HEAD)")
    parser.add_argument("--repo-path", default=".", help="Path to the target git repository to review")
    parser.add_argument(
        "--config-file",
        default=DEFAULT_CONFIG_FILE,
        help=f"Repo config file to load relative to repo-path (default: {DEFAULT_CONFIG_FILE})",
    )
    parser.add_argument("--patch-file", help="Optional path to a saved patch file")
    parser.add_argument(
        "--provider",
        default=None,
        help=f"Review provider override (default from config: {DEFAULT_PROVIDER})",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"Model override (default from config: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--max-diff-lines",
        type=int,
        default=None,
        help="Maximum diff lines sent to model (default from config)",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=None,
        help="Maximum output tokens requested from the provider (default from config)",
    )
    parser.add_argument(
        "--post-comment",
        action="store_true",
        help="Post result as GitHub PR comment",
    )
    parser.add_argument("--usage-output-file", help="Optional path to write a JSON usage report")
    parser.add_argument("--summary-output-file", help="Optional path to write a markdown run summary")
    parser.add_argument("--owner", help="GitHub repo owner")
    parser.add_argument("--repo", help="GitHub repo name")
    parser.add_argument("--pr-number", type=int, help="GitHub PR number")

    return parser.parse_args()


def extract_changed_files_from_patch(diff_text: str) -> list[str]:
    files: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            files.append(line.removeprefix("+++ b/").strip())
    return sorted(set(files))


def resolve_rules_path(repo_path: str, rules_path: str) -> str:
    candidate = Path(repo_path) / rules_path
    if candidate.exists():
        return str(candidate)
    return rules_path


def validate_comment_args(args: argparse.Namespace) -> None:
    missing = [name for name in ("owner", "repo", "pr_number") if getattr(args, name) is None]
    if missing:
        raise RuntimeError(
            f"--post-comment requires: {', '.join('--' + m.replace('_', '-') for m in missing)}"
        )


def maybe_sync_comment(args: argparse.Namespace, run: ReviewRun) -> tuple[ReviewRun, str]:
    if not args.post_comment:
        return run, "not_requested"

    validate_comment_args(args)
    posted = sync_pr_comment(
        owner=args.owner,
        repo=args.repo,
        pr_number=args.pr_number,
        run=run,
        github_token=os.getenv("GITHUB_TOKEN"),
    )
    if posted:
        print("\nPosted review as GitHub PR comment.")
        return run, "posted"

    return (
        ReviewRun(
            status="unchanged",
            message="Review output was unchanged, so no new PR comment was posted.",
            usage=run.usage,
        ),
        "suppressed_unchanged",
    )


def emit_usage_outputs(
    *,
    args: argparse.Namespace,
    run: ReviewRun,
    changed_files_count: int,
    diff_lines: int,
    context_files_count: int,
    comment_action: str,
) -> None:
    report = build_usage_report(
        run=run,
        changed_files_count=changed_files_count,
        diff_line_count=diff_lines,
        context_files_count=context_files_count,
        comment_action=comment_action,
    )
    append_github_step_summary(report)

    if args.usage_output_file:
        write_usage_report(args.usage_output_file, report)
    if args.summary_output_file:
        write_job_summary(args.summary_output_file, report)


def main() -> int:
    load_dotenv()
    args = parse_args()
    config = load_app_config(repo_path=args.repo_path, config_file=args.config_file)

    provider = args.provider or config.provider
    model = args.model or config.model
    max_diff_lines = args.max_diff_lines or config.max_diff_lines
    max_output_tokens = args.max_output_tokens or config.max_output_tokens

    try:
        system_prompt = load_text_file("prompts/system.txt")
        repo_rules = load_text_file(resolve_rules_path(args.repo_path, config.rules_path))

        if args.patch_file:
            diff_text = load_text_file(args.patch_file)
            changed_files = extract_changed_files_from_patch(diff_text)
        else:
            changed_files = get_changed_files(args.base, args.head, repo_path=args.repo_path)
            if not changed_files:
                run = ReviewRun(
                    status="no_changes",
                    message="No relevant changed files found.",
                )
                emit_usage_outputs(
                    args=args,
                    run=run,
                    changed_files_count=0,
                    diff_lines=0,
                    context_files_count=0,
                    comment_action="not_requested",
                )
                print(run.to_markdown())
                return 0

            diff_text = get_diff_for_files(
                args.base,
                args.head,
                changed_files,
                repo_path=args.repo_path,
            )

        if not diff_text.strip():
            run = ReviewRun(
                status="no_changes",
                message="No diff content found after filtering.",
            )
            emit_usage_outputs(
                args=args,
                run=run,
                changed_files_count=len(changed_files),
                diff_lines=0,
                context_files_count=0,
                comment_action="not_requested",
            )
            print(run.to_markdown())
            return 0

        diff_lines = diff_line_count(diff_text)

        if is_diff_oversized(diff_text, max_lines=max_diff_lines):
            run = ReviewRun(
                status="skipped",
                skip_reason=(
                    f"Diff exceeded the configured limit of {max_diff_lines} lines "
                    f"({diff_lines} lines)."
                ),
            )
            run, comment_action = maybe_sync_comment(args, run)
            emit_usage_outputs(
                args=args,
                run=run,
                changed_files_count=len(changed_files),
                diff_lines=diff_lines,
                context_files_count=0,
                comment_action=comment_action,
            )
            markdown = run.to_markdown()
            print(markdown)
            return 0

        relevant_context = load_relevant_context(
            repo_path=args.repo_path,
            changed_files=changed_files,
            max_files=config.max_context_files,
            max_chars=config.max_context_chars,
        )

        user_prompt = build_user_prompt(
            repo_rules=repo_rules,
            changed_files=changed_files,
            diff_text=diff_text,
            relevant_context=relevant_context,
            max_findings=config.max_findings,
            max_missing_tests=config.max_missing_tests,
        )

        review, usage = run_review(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            provider=provider,
            model=model,
            max_output_tokens=max_output_tokens,
            temperature=config.temperature,
        )

        run = ReviewRun(status="reviewed", review=review, usage=usage)
        run, comment_action = maybe_sync_comment(args, run)
        emit_usage_outputs(
            args=args,
            run=run,
            changed_files_count=len(changed_files),
            diff_lines=diff_lines,
            context_files_count=len(relevant_context),
            comment_action=comment_action,
        )
        markdown = run.to_markdown()
        print(markdown)

        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
