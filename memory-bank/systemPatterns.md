# System Patterns

## Architectural Patterns
- Thin orchestration layer in `main.py`
- Small single-purpose modules for IO boundaries
- Structured AI output enforced with a Pydantic schema
- Prompt-driven behavior using checked-in text assets (`prompts/`, `config/`)

## Key Implementation Patterns
- File-based configuration: review behavior is shaped by markdown/text prompt files instead of hardcoding policy in Python
- Diff scoping: only changed files and their diff are sent to the model to reduce cost and noise
- Ignore filtering: binary/generated/lock artifacts are excluded before prompt creation
- Response validation: model output is parsed as JSON and validated before rendering
- Optional side effect boundary: comment posting is isolated behind a flag and dedicated module

## Error Handling Pattern
- Lower-level modules raise `RuntimeError` with contextual messages
- Entry point catches broad failures and exits non-zero after printing an error

## Cost/Signal Pattern
- Default model is a lower-cost Anthropic model
- Diff lines are capped to limit token usage
- Prompt explicitly limits count of findings and missing test suggestions
