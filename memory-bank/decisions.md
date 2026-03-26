# Decisions (ADRs-lite)

## Existing Decisions Inferred From Current Codebase

### Use Anthropic as the review engine
- The application currently depends on the Anthropic Messages API for generating PR reviews.
- Rationale: simple integration and low-cost model default for routine review tasks.

### Enforce structured model output with Pydantic
- Review output is requested as JSON and validated against `ReviewResult`/`Finding` schemas.
- Rationale: prevents free-form model output from directly driving comments without validation.

### Review only the diff, not the full repository
- The prompt is built from changed files, repository rules, and a unified diff.
- Rationale: reduce cost, keep feedback relevant, and fit the PR-review use case.

### Keep repository policy in text files
- System prompt and review rules are stored as editable text/markdown files.
- Rationale: easier iteration on AI behavior without changing Python code.
