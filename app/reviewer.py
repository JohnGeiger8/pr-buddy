from __future__ import annotations

import json
import os

from pydantic import ValidationError

from app.providers import DEFAULT_MODEL, build_provider
from app.schemas import ReviewResult


def extract_json(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()

    return text


def parse_review_result(json_text: str, *, raw_text: str) -> ReviewResult:
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Model did not return valid JSON.\n\nRaw output:\n{raw_text}") from exc

    try:
        return ReviewResult.model_validate(parsed)
    except ValidationError as exc:
        raise RuntimeError(f"Model returned invalid schema.\n\nParsed output:\n{parsed}") from exc


def run_review(
    system_prompt: str,
    user_prompt: str,
    provider: str,
    model: str = DEFAULT_MODEL,
    max_output_tokens: int = 1400,
    temperature: float = 0.1,
) -> tuple[ReviewResult, dict[str, int | str | None]]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    client = build_provider(provider, api_key)
    response = client.review(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
    )
    return response.review, response.usage.model_dump()
