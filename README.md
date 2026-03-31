# PR Review Agent

A cheap local PR review workflow using Python + Anthropic.

## Phase 1 Contract

- Repo-level overrides live in `.pr-buddy.yml`
- Anthropic is the only active provider today, with a provider abstraction ready for future expansion
- Runs now produce explicit states such as `reviewed`, `skipped`, `unchanged`, `no_changes`, and `error`
- Findings are rendered with fixed labels like `Likely bug`, `Possible issue`, and `Missing tests`
- Diffs over the configured line limit are skipped instead of truncated
- Extra repo context is limited to a few relevant docs/config files for Python and Node/TypeScript changes
- PR comments now carry hidden metadata so the agent can suppress unchanged output and avoid reposting the same skip state on every push

## Setup

1. Create and activate a virtual environment
2. Install dependencies
3. Copy `.env.example` to `.env`
4. Add your Anthropic API key

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Reusable Workflow

Other personal repositories can call this repo's workflow directly.

Example caller workflow:

```yaml
name: AI PR Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  review:
    uses: JohnGeiger8/pr-buddy/.github/workflows/pr-review-agent.yml@main
    permissions:
      pull-requests: write
      contents: read
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

Optional per-repo overrides live in `.pr-buddy.yml`. Optional workflow-call inputs can override `provider`, `model`, `config-file`, `max-diff-lines`, `max-output-tokens`, and `python-version`.

Managed PR comments are only considered for dedupe when they:

- include the hidden `pr-buddy` metadata marker
- are authored by `github-actions[bot]`

Each workflow run also writes:

- a JSON usage artifact with status, tokens, diff size, context count, comment action, and estimated cost
- a markdown summary that appears in the GitHub Actions step summary

## Eval Workflow

Saved PR patches in `evals/public_prs/` can be re-run through the current agent to sanity-check review usefulness and noise before rollout.

Example:

```bash
./venv/bin/python scripts/run_patch_evals.py --model claude-haiku-4-5
```

This writes:

- per-bundle outputs like `review.md`, `usage.json`, and `stderr.log` under `evals/results/latest/<slug>/`
- aggregate files at `evals/results/latest/summary.json` and `evals/results/latest/summary.md`

The summary intentionally stays lightweight. It highlights expected catches from `notes.md`, simple forbidden-phrase checks, missing-test mentions, run status, and estimated cost so you can quickly spot noisy or weak reviews before enabling broader automation.

## Rollout

The recommended rollout order and live validation checklist are documented in [docs/rollout-plan.md](/Users/JohnGeiger/Development/pr-buddy/docs/rollout-plan.md).
