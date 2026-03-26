# AI Contract

## Prime Directive
Make small, testable changes that keep the repo green.

## Required Workflow
- Always propose a Plan (files touched + commands to run) before editing.
- Prefer the smallest diff that satisfies the requirement.
- Do not refactor unrelated code.

## Coding Standards
### Python
- Adherence to PEP 8: Follow the official Python style guide for formatting, naming conventions (e.g., snake_case for functions/variables, PascalCase for classes), and overall code layout.
- Type Hinting: Use explicit type hints for function signatures and variables to improve code clarity and enable static analysis tools.
- Docstrings: Include consistent docstrings (e.g., Google style or NumPy style) for all public functions, classes, and modules to document behavior and interfaces.
- Specific Error Handling: Catch specific exceptions instead of using broad except Exception blocks, and include contextual information in error messages using the built-in logging module instead of print() statements.
- Modern Python Features: Prefer modern features like f-strings for string formatting and pathlib for file path manipulations over older methods like os.path and string concatenation.

## Testing Rules
- If you touch a file that doesn't have tests written for it, write them for at least 75% code coverage
- Always run:
  - `pytest`

## Forbidden
- Introducing new frameworks without a decision record.
- Large rewrites “for cleanliness.”
- Adding auth/accounts unless explicitly required.

## Definition of Done (per task)
- Code compiles
- Tests pass
- Docs updated if behavior or interfaces changed

## Task Closeout (Required)
- Summarize changes in 5 bullets
- List commands run + results
- Update memory-bank:
  - progress.md (always)
  - activeContext.md (if priorities changed)
  - decisions.md (if a new decision was made)
  - architecture.md (if interfaces/structure changed)
