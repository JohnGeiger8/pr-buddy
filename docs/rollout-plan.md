# Rollout Plan

## What We Validated Locally

- Full test suite passes with `./venv/bin/python -m pytest -q`
- Oversized patch runs skip cleanly without calling the provider
- Skip runs write both `usage.json` and `summary.md`
- The reusable workflow and comment dedupe logic are covered by tests

## What Still Needs Live Validation

These checks require a real `ANTHROPIC_API_KEY` in a GitHub-hosted run:

- A non-skipped review posts a fresh PR comment
- A second run with unchanged output suppresses a duplicate comment
- A state transition from `skipped` to `reviewed` posts a new comment
- A provider-backed run writes real token usage and estimated cost

## Recommended Rollout Order

1. Enable the reusable workflow on this repository first.
2. Open one small PR with a diff well under the `800`-line limit.
3. Confirm the workflow:
   - posts one summary comment
   - uploads usage artifacts
   - shows a markdown usage summary in the Actions run
4. Push a no-op or low-impact update to the same PR and confirm unchanged output is suppressed.
5. Open one oversized PR or test with a saved large patch and confirm the skip comment appears once.
6. If those behaviors look good, enable the workflow in 1-2 small personal repos.
7. Watch estimated monthly cost and noise level for a week before broader rollout.

## Suggested First Repos

- This repo
- One small Python repo
- One small TypeScript/Node repo

Pick repos with:

- modest PR sizes
- straightforward test/setup expectations
- low risk if the agent comments imperfectly

## Per-Repo Setup Checklist

- Add `ANTHROPIC_API_KEY` to repo secrets
- Add a caller workflow that references `JohnGeiger8/pr-buddy/.github/workflows/pr-review-agent.yml@main`
- Optionally add `.pr-buddy.yml` if the repo needs custom rules or lower limits
- Open a test PR and inspect:
  - comment tone
  - missing-test suggestions
  - cost artifact output
  - unchanged-comment suppression

## Rollback Plan

If the agent is noisy or costs more than expected:

- disable the caller workflow in the affected repo
- lower `max_output_tokens`
- lower `max_diff_lines`
- tighten repo-specific rules in `.pr-buddy.yml`
- re-run the saved patch eval workflow before re-enabling automation

## Success Criteria For Wider Rollout

- Comments are usually helpful and rarely repetitive
- Oversized PRs skip predictably
- Unchanged pushes do not create new comments
- Estimated monthly cost stays under the target budget
- Python and Node/TypeScript repos both produce acceptable review quality
