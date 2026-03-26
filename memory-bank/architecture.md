# Architecture

## High-Level Flow
1. `app.main` loads environment variables and CLI arguments
2. It reads the system prompt and repository review rules from disk
3. `app.diff_reader` computes changed files and filtered unified diff via git
4. `app.prompt_builder` assembles a user prompt containing rules, changed files, diff, and JSON schema instructions
5. `app.reviewer` calls the Anthropic Messages API and validates the JSON response with Pydantic schemas
6. `app.schemas` converts the structured result into markdown
7. `app.github_comment` optionally posts the markdown to a GitHub PR comment

## Main Modules
- `app/main.py`: CLI entrypoint and orchestration
- `app/diff_reader.py`: git diff/file discovery and diff truncation
- `app/prompt_builder.py`: prompt composition from repository inputs
- `app/reviewer.py`: model invocation, JSON extraction, and schema validation
- `app/schemas.py`: Pydantic response schema and markdown rendering
- `app/github_comment.py`: GitHub Issues comments API integration for PR comments

## External Interfaces
- Git CLI for changed file and diff retrieval
- Anthropic API for review generation
- GitHub REST API for posting PR comments
- GitHub Actions workflow for CI execution on pull request events

## Runtime Modes
- Local CLI run against refs like `main...HEAD`
- GitHub Actions run against pull request base/head SHAs with comment posting enabled
