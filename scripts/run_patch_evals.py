from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_EVALS_DIR = "evals/public_prs"
DEFAULT_OUTPUT_DIR = "evals/results/latest"


@dataclass
class EvalBundle:
    slug: str
    patch_path: Path
    notes_path: Path
    metadata_path: Path | None


def discover_eval_bundles(evals_dir: Path) -> list[EvalBundle]:
    bundles: list[EvalBundle] = []
    for patch_path in sorted(evals_dir.glob("*/pr.patch")):
        bundle_dir = patch_path.parent
        notes_path = bundle_dir / "notes.md"
        metadata_path = bundle_dir / "metadata.json"
        bundles.append(
            EvalBundle(
                slug=bundle_dir.name,
                patch_path=patch_path,
                notes_path=notes_path,
                metadata_path=metadata_path if metadata_path.exists() else None,
            )
        )
    return bundles


def extract_note_bullets(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    target = f"## {heading}".strip()
    bullets: list[str] = []
    collecting = False

    for line in lines:
        stripped = line.strip()
        if stripped == target:
            collecting = True
            continue
        if collecting and stripped.startswith("## "):
            break
        if collecting and stripped.startswith("- "):
            bullets.append(stripped[2:].strip())

    return [bullet for bullet in bullets if bullet]


def load_metadata_title(metadata_path: Path | None) -> str | None:
    if metadata_path is None:
        return None
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    title = payload.get("title")
    return title if isinstance(title, str) else None


def contains_any_phrase(text: str, phrases: list[str]) -> bool:
    lowered = text.lower()
    return any(phrase.lower() in lowered for phrase in phrases if phrase.strip())


def run_single_eval(
    *,
    bundle: EvalBundle,
    output_dir: Path,
    provider: str | None,
    model: str | None,
    max_diff_lines: int | None,
    max_output_tokens: int | None,
) -> dict[str, object]:
    run_dir = output_dir / bundle.slug
    run_dir.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "app.main",
        "--patch-file",
        str(bundle.patch_path),
        "--usage-output-file",
        str(run_dir / "usage.json"),
        "--summary-output-file",
        str(run_dir / "usage_summary.md"),
    ]

    if provider:
        command.extend(["--provider", provider])
    if model:
        command.extend(["--model", model])
    if max_diff_lines is not None:
        command.extend(["--max-diff-lines", str(max_diff_lines)])
    if max_output_tokens is not None:
        command.extend(["--max-output-tokens", str(max_output_tokens)])

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    (run_dir / "review.md").write_text(result.stdout, encoding="utf-8")
    (run_dir / "stderr.log").write_text(result.stderr, encoding="utf-8")
    (run_dir / "command.json").write_text(json.dumps(command, indent=2) + "\n", encoding="utf-8")

    notes_text = bundle.notes_path.read_text(encoding="utf-8") if bundle.notes_path.exists() else ""
    expected_catches = extract_note_bullets(notes_text, "What a good review should catch")
    forbidden_flags = extract_note_bullets(notes_text, "What should NOT be flagged")

    usage_payload: dict[str, object] = {}
    usage_path = run_dir / "usage.json"
    if usage_path.exists():
        try:
            usage_payload = json.loads(usage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            usage_payload = {}

    review_text = result.stdout.strip()
    review_lower = review_text.lower()
    mentions_missing_tests = "missing test" in review_lower or "missing tests" in review_lower
    mentions_expected_phrase = contains_any_phrase(review_text, expected_catches)
    mentions_forbidden_phrase = contains_any_phrase(review_text, forbidden_flags)

    summary = {
        "slug": bundle.slug,
        "title": load_metadata_title(bundle.metadata_path),
        "exit_code": result.returncode,
        "status": usage_payload.get("status"),
        "comment_action": usage_payload.get("comment_action"),
        "input_tokens": usage_payload.get("input_tokens"),
        "output_tokens": usage_payload.get("output_tokens"),
        "estimated_cost_usd": usage_payload.get("estimated_cost_usd"),
        "expected_catches": expected_catches,
        "forbidden_flags": forbidden_flags,
        "mentions_missing_tests": mentions_missing_tests,
        "mentions_expected_phrase": mentions_expected_phrase,
        "mentions_forbidden_phrase": mentions_forbidden_phrase,
        "review_path": str((run_dir / "review.md").resolve()),
        "usage_path": str(usage_path.resolve()) if usage_path.exists() else None,
    }
    return summary


def write_summary_markdown(output_dir: Path, results: list[dict[str, object]]) -> None:
    lines = ["# Eval Summary", ""]
    for item in results:
        lines.append(f"## {item['slug']}")
        title = item.get("title") or "Untitled"
        lines.append(f"- Title: {title}")
        lines.append(f"- Exit code: {item['exit_code']}")
        lines.append(f"- Status: {item.get('status')}")
        lines.append(f"- Comment action: {item.get('comment_action')}")
        lines.append(f"- Estimated cost (USD): {item.get('estimated_cost_usd')}")
        lines.append(f"- Mentioned missing tests: {item.get('mentions_missing_tests')}")
        lines.append(f"- Mentioned expected phrase: {item.get('mentions_expected_phrase')}")
        lines.append(f"- Mentioned forbidden phrase: {item.get('mentions_forbidden_phrase')}")
        expected = item.get("expected_catches") or []
        forbidden = item.get("forbidden_flags") or []
        lines.append(f"- Expected catches: {', '.join(expected) if expected else 'None listed'}")
        lines.append(f"- Forbidden flags: {', '.join(forbidden) if forbidden else 'None listed'}")
        lines.append(f"- Review output: {item.get('review_path')}")
        lines.append("")

    (output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PR review agent against saved patch evals")
    parser.add_argument("--evals-dir", default=DEFAULT_EVALS_DIR, help=f"Eval bundle directory (default: {DEFAULT_EVALS_DIR})")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help=f"Where to write eval results (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--provider", default=None, help="Optional provider override")
    parser.add_argument("--model", default=None, help="Optional model override")
    parser.add_argument("--max-diff-lines", type=int, default=None, help="Optional max diff lines override")
    parser.add_argument("--max-output-tokens", type=int, default=None, help="Optional max output tokens override")
    args = parser.parse_args()

    evals_dir = Path(args.evals_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    bundles = discover_eval_bundles(evals_dir)
    if not bundles:
        print(f"No eval bundles found in {evals_dir}", file=sys.stderr)
        return 1

    results: list[dict[str, object]] = []
    for bundle in bundles:
        print(f"Running eval for {bundle.slug}...")
        result = run_single_eval(
            bundle=bundle,
            output_dir=output_dir,
            provider=args.provider,
            model=args.model,
            max_diff_lines=args.max_diff_lines,
            max_output_tokens=args.max_output_tokens,
        )
        results.append(result)

    (output_dir / "summary.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    write_summary_markdown(output_dir, results)
    print(f"Wrote eval results to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
