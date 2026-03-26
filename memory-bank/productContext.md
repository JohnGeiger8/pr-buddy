# Product Context

## Purpose
Help developers get fast, actionable PR feedback without running a heavyweight code review platform.

## Target Workflow
- Developer opens or updates a pull request
- GitHub Actions runs the agent on the PR diff
- The agent filters irrelevant files, builds a prompt, and sends the diff to Anthropic
- The model returns structured JSON describing summary, findings, risk, missing tests, and confidence
- The agent renders that output as markdown and optionally posts it as a PR comment

## Value Proposition
- Cheap and simple to run
- Focused on high-signal review comments rather than style nitpicks
- Repository-specific review rules can be customized in markdown
- Works locally for experimentation and in CI for automation

## Current Constraints
- Review quality is limited to the provided diff and prompt context
- No deep repository-wide semantic analysis beyond changed files/diff
- Currently centered around Anthropic as the model provider
