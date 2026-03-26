# Active Context

## Read First
- memory-bank/aiContract.md
- memory-bank/architecture.md
- memory-bank/decisions.md

## Current Focus
- Initialize the memory bank with an accurate understanding of the current repository.
- Capture the system's architecture, product intent, technical stack, and current workflow constraints.

## Recent Decisions
- The repo currently uses a lightweight CLI-first architecture with GitHub Actions integration.
- Review logic is constrained to changed-file diffs and repository review rules.
- Structured JSON validation via Pydantic is a core safeguard around LLM output.

## Next Steps
- Keep memory-bank documents in sync as implementation expands.
- Add testing and logging improvements if future tasks modify runtime behavior.
- Record decisions when introducing new providers, workflows, or architecture changes.

## Notes
- `memory-bank/aiContract.md` defines the expected workflow and closeout requirements for future tasks.
- The `memory-bank/` directory is currently untracked in git on this branch.
