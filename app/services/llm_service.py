from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    OpenAIError,
    RateLimitError,
)
from openai.types.chat import ChatCompletionMessage

from app.core.config import settings

logger = logging.getLogger(__name__)

Message = dict[str, Any]  # Any, not str — tool_calls is a list


class LLMError(Exception):
    """Vendor failure, translated. status_code is what the client sees."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# One client per process — owns an httpx connection pool. Same reason there is one Engine.
client = AsyncOpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.LLM_BASE_URL,
    timeout=settings.LLM_TIMEOUT_SECONDS,
    max_retries=settings.LLM_MAX_RETRIES,      # retries 429/5xx with backoff + jitter, invisibly
    default_headers={
        "HTTP-Referer": settings.APP_URL,      # optional; OpenRouter leaderboards only
        "X-Title": settings.APP_NAME,
    },
)


def resolve_model(requested: str | None) -> str:
    """A client-supplied model string is a cost vector. Allowlist it."""
    if requested is None:
        return settings.LLM_MODEL
    if requested not in settings.ALLOWED_MODELS:
        raise LLMError(f"Model '{requested}' is not available.", 400)
    return requested


def _prepend_system(messages: list[Message]) -> list[Message]:
    """Runs AFTER trimming, so the system prompt can never be trimmed away."""
    if messages and messages[0]["role"] == "system":
        return messages
    return [{"role": "system", "content": settings.SYSTEM_PROMPT}, *messages]


def _extra_body() -> dict[str, Any]:
    """OpenRouter-only fields. The OpenAI SDK forwards extra_body verbatim."""
    body: dict[str, Any] = {"provider": {"require_parameters": True}}   # refuse providers that'd drop `tools`
    if settings.LLM_FALLBACK_MODELS:
        body["models"] = settings.LLM_FALLBACK_MODELS
    return body


def _translate(exc: OpenAIError) -> LLMError:
    """Subclasses first, or the specific branches are dead code."""
    if isinstance(exc, RateLimitError):        # ⊂ APIStatusError
        return LLMError("LLM rate limit exceeded.", 429)
    if isinstance(exc, APITimeoutError):       # ⊂ APIConnectionError
        return LLMError("LLM request timed out.", 504)
    if isinstance(exc, APIConnectionError):
        return LLMError("Could not reach the LLM provider.", 503)
    if isinstance(exc, APIStatusError):
        return LLMError(f"LLM provider returned {exc.status_code}.", 502)
    return LLMError("Unexpected LLM error.", 502)


async def complete_raw(
    messages: list[Message],
    *,
    model: str | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> ChatCompletionMessage:
    """Raw message object, so callers can inspect tool_calls."""
    try:
        resp = await client.chat.completions.create(
            model=resolve_model(model),
            messages=_prepend_system(messages),
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            extra_body=_extra_body(),
            **({"tools": tools} if tools else {}),   # never send tools=None; some providers reject it
        )
    except OpenAIError as exc:
        raise _translate(exc) from exc

    usage = resp.usage
    logger.info(
        "llm_call",
        extra={
            "model_requested": model or settings.LLM_MODEL,
            "model_served": resp.model,                    # fallbacks can swap it. cost anomalies live here.
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
        },
    )
    return resp.choices[0].message


async def complete(messages: list[Message], *, model: str | None = None) -> str:
    msg = await complete_raw(messages, model=model)
    content = msg.content or ""                            # None when the model calls a tool
    if not content.strip():
        raise LLMError("LLM returned an empty response.", 502)
    return content


async def stream(messages: list[Message], *, model: str | None = None) -> AsyncIterator[str]:
    """Yields text deltas. No tools — see tool_service for why."""
    try:
        chunks = await client.chat.completions.create(     # await ONCE to get the iterator
            model=resolve_model(model),
            messages=_prepend_system(messages),
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            extra_body=_extra_body(),
            stream=True,
        )
        async for chunk in chunks:
            if not chunk.choices:                          # usage-only final chunk on some providers
                continue
            delta = chunk.choices[0].delta.content         # `delta`, not `message` — only what's new
            if delta:                                      # "" on the role chunk, None on the stop chunk
                yield delta
    except OpenAIError as exc:
        raise _translate(exc) from exc


async def aclose() -> None:
    await client.close()