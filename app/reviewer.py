from __future__ import annotations

import json
import os

from anthropic import Anthropic
from pydantic import ValidationError

from app.schemas import ReviewResult


DEFAULT_MODEL = "claude-3-5-haiku-latest"


def extract_json(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()

    return text


def run_review(
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    max_output_tokens: int = 1400,
    temperature: float = 0.1,
) -> ReviewResult:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    client = Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=max_output_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": user_prompt,
            }
        ],
    )

    raw_text_parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            raw_text_parts.append(block.text)

    raw_text = "\n".join(raw_text_parts).strip()
    json_text = extract_json(raw_text)

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Model did not return valid JSON.\n\nRaw output:\n{raw_text}") from exc

    try:
        return ReviewResult.model_validate(parsed)
    except ValidationError as exc:
        raise RuntimeError(f"Model returned invalid schema.\n\nParsed output:\n{parsed}") from exc