"""LLM Query Generator.

Calls the configured LLM provider (Azure OpenAI or Anthropic) with the
assembled prompt and returns the raw text response.

Handles retries with exponential backoff and model fallback.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field

import structlog

from app.config import Settings
from app.models.enums import LLMProvider

logger = structlog.get_logger(__name__)


@dataclass
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    attempt: int


class LLMError(Exception):
    """Raised when all LLM attempts fail."""


async def _call_azure_openai(
    system_prompt: str,
    user_message: str,
    deployment: str,
    settings: Settings,
) -> tuple[str, int, int]:
    """Call Azure OpenAI and return (text, prompt_tokens, completion_tokens)."""
    try:
        from openai import AsyncAzureOpenAI
    except ImportError:
        raise LLMError("openai package not installed")

    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_ai_endpoint,
        api_key=settings.azure_ai_api_key,
        api_version=settings.azure_openai_api_version,
    )
    response = await client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
        max_tokens=2048,
        stop=["```", "EXPLANATION:", "NOTE:"],
    )
    text = response.choices[0].message.content or ""
    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0
    return text, pt, ct


async def _call_anthropic(
    system_prompt: str,
    user_message: str,
    model: str,
    settings: Settings,
) -> tuple[str, int, int]:
    """Call Anthropic Claude and return (text, prompt_tokens, completion_tokens)."""
    try:
        import anthropic
    except ImportError:
        raise LLMError("anthropic package not installed")

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=model,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
        temperature=0.0,
        max_tokens=2048,
        stop_sequences=["```", "EXPLANATION:", "NOTE:"],
    )
    text = response.content[0].text if response.content else ""
    pt = response.usage.input_tokens
    ct = response.usage.output_tokens
    return text, pt, ct


async def generate(
    system_prompt: str,
    user_message: str,
    settings: Settings,
    is_complex: bool = False,
) -> LLMResponse:
    """Generate SQL via the configured LLM with retry and model fallback."""
    provider = LLMProvider(settings.llm_provider)
    max_retries = settings.llm_max_retries
    timeout = settings.llm_timeout_seconds

    # Model selection
    if provider == LLMProvider.AZURE_OPENAI:
        primary_model = settings.azure_openai_deployment
        fallback_model = settings.azure_openai_fallback_deployment
    else:
        primary_model = settings.anthropic_primary_model
        fallback_model = settings.anthropic_fallback_model

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 2):  # attempts: 1, 2, 3
        model = fallback_model if attempt > 1 else primary_model
        start_ts = time.monotonic()
        try:
            async with asyncio.timeout(timeout):
                if provider == LLMProvider.AZURE_OPENAI:
                    text, pt, ct = await _call_azure_openai(
                        system_prompt, user_message, model, settings
                    )
                else:
                    text, pt, ct = await _call_anthropic(
                        system_prompt, user_message, model, settings
                    )

            latency_ms = (time.monotonic() - start_ts) * 1000
            logger.info("LLM call succeeded", model=model, attempt=attempt,
                        latency_ms=f"{latency_ms:.1f}")
            return LLMResponse(
                text=text,
                model=model,
                prompt_tokens=pt,
                completion_tokens=ct,
                latency_ms=latency_ms,
                attempt=attempt,
            )

        except (TimeoutError, asyncio.TimeoutError) as e:
            last_error = e
            logger.warning("LLM timeout", model=model, attempt=attempt, timeout=timeout)
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            # Non-retriable errors
            if any(x in error_str for x in ["401", "authentication", "api key"]):
                raise LLMError(f"LLM auth failure: {e}") from e
            logger.warning("LLM call failed", model=model, attempt=attempt, error=str(e))

        if attempt <= max_retries:
            backoff = (0.5 * (2 ** (attempt - 1))) + random.uniform(0, 0.2)
            await asyncio.sleep(backoff)

    raise LLMError(f"All LLM attempts failed. Last error: {last_error}")
