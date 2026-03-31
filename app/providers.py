from __future__ import annotations

from typing import Protocol

from anthropic import Anthropic
from pydantic import BaseModel, Field

from app.schemas import ReviewResult


DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-haiku-4-5"


class ProviderUsage(BaseModel):
    provider: str
    model: str
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)


class ProviderResponse(BaseModel):
    review: ReviewResult
    usage: ProviderUsage


class ReviewProvider(Protocol):
    def review(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_output_tokens: int,
        temperature: float,
    ) -> ProviderResponse:
        ...


class AnthropicReviewProvider:
    def __init__(self, api_key: str) -> None:
        self._client = Anthropic(api_key=api_key)

    def review(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_output_tokens: int,
        temperature: float,
    ) -> ProviderResponse:
        from app.reviewer import extract_json, parse_review_result

        response = self._client.messages.create(
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
        review = parse_review_result(extract_json(raw_text), raw_text=raw_text)
        usage = ProviderUsage(
            provider=DEFAULT_PROVIDER,
            model=model,
            input_tokens=getattr(response.usage, "input_tokens", None),
            output_tokens=getattr(response.usage, "output_tokens", None),
        )
        return ProviderResponse(review=review, usage=usage)


def build_provider(name: str, api_key: str) -> ReviewProvider:
    if name == DEFAULT_PROVIDER:
        return AnthropicReviewProvider(api_key=api_key)

    raise RuntimeError(f"Unsupported provider: {name}")
