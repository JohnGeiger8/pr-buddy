# Tech Context

## Stack
- Python 3.11 in CI
- Anthropic Python SDK
- Pydantic v2 for response schema validation
- python-dotenv for local environment loading
- requests for GitHub REST API calls

## Project Structure
- `app/`: runtime source code
- `config/review_rules.md`: repository-specific review guidance
- `prompts/system.txt`: system prompt for the LLM
- `.github/workflows/pr-review-agent.yml`: automation entrypoint
- `memory-bank/`: project knowledge and working context

## Environment Variables
- `ANTHROPIC_API_KEY`: required for review generation
- `GITHUB_TOKEN`: required when posting PR comments

## Operational Details
- Uses `git diff base...head` and `git diff --name-only` to inspect PR changes
- Diff is truncated after 800 lines by default
- Default model is `claude-haiku-4-5`

## Dependencies
- `anthropic>=0.40.0`
- `pydantic>=2.8.0`
- `python-dotenv>=1.0.1`
- `requests>=2.32.0`
