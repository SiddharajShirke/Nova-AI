"""
Nova AI — LLM Gateway
Primary: NVIDIA NIM (llama-3.3-70b-instruct via OpenAI-compatible API)
Fallback: Google Gemini (gemini-1.5-flash-latest)
Circuit breaker per provider. 30s timeout. Cost tracking.
"""
import asyncio
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import google.generativeai as genai
from openai import AsyncOpenAI, RateLimitError, APIStatusError, APITimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Provider failed — skip
    HALF_OPEN = "half_open" # Testing recovery


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 90.0
    _failures: int = field(default=0, repr=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, repr=False)
    _opened_at: float = field(default=0.0, repr=False)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._opened_at > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self):
        self._failures = 0
        self._state = CircuitState.CLOSED

    def record_failure(self):
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.time()
            logger.warning(f"[CircuitBreaker] {self.name} OPENED after {self._failures} failures")

    @property
    def is_available(self) -> bool:
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)


# Singleton circuit breakers
_nvidia_cb = CircuitBreaker("nvidia")
_gemini_cb = CircuitBreaker("gemini")

# Cost tracking (rough estimates per 1M tokens)
NVIDIA_COST_PER_1M = 0.35   # llama-3.3-70b on NIM
GEMINI_COST_PER_1M = 0.075  # gemini-1.5-flash

_total_cost_usd: float = 0.0
_nvidia_client: Optional[AsyncOpenAI] = None


def _get_nvidia_client() -> AsyncOpenAI:
    global _nvidia_client
    if _nvidia_client is None:
        _nvidia_client = AsyncOpenAI(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            timeout=30.0,
        )
    return _nvidia_client


def _setup_gemini():
    if settings.gemini_available:
        genai.configure(api_key=settings.google_api_key)


_setup_gemini()


async def _call_nvidia(prompt: str, system: str, max_tokens: int = 1024) -> str:
    client = _get_nvidia_client()
    response = await client.chat.completions.create(
        model=settings.nvidia_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    usage = response.usage
    if usage:
        cost = (usage.total_tokens / 1_000_000) * NVIDIA_COST_PER_1M
        global _total_cost_usd
        _total_cost_usd += cost
    content = response.choices[0].message.content or ""
    # Strip <think> tags from reasoning models
    if "<think>" in content:
        content = content.split("</think>")[-1].strip()
    return content


async def _call_gemini(prompt: str, system: str, max_tokens: int = 1024) -> str:
    loop = asyncio.get_event_loop()
    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=system,
    )

    def _sync_call():
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.3,
            ),
        )
        return response.text

    text = await asyncio.wait_for(loop.run_in_executor(None, _sync_call), timeout=45.0)
    # Rough cost estimate
    tokens = len(prompt.split()) + len(text.split())
    global _total_cost_usd
    _total_cost_usd += (tokens / 1_000_000) * GEMINI_COST_PER_1M
    return text


async def llm_complete(
    prompt: str,
    system: str = "You are a professional marketing analyst. Return only valid JSON as instructed.",
    max_tokens: int = 1024,
    provider_hint: str = "auto",  # "nvidia" | "gemini" | "auto"
) -> str:
    """
    Route an LLM completion through NVIDIA first, Gemini as fallback.
    Returns the text response string.
    """
    providers = []

    if provider_hint == "gemini":
        providers = ["gemini", "nvidia"]
    elif provider_hint == "nvidia":
        providers = ["nvidia", "gemini"]
    else:
        # Auto: prefer NVIDIA if available
        if settings.nvidia_available:
            providers.append("nvidia")
        if settings.gemini_available:
            providers.append("gemini")

    if not providers:
        raise RuntimeError("No LLM providers configured. Add NVIDIA_API_KEY or GOOGLE_API_KEY to .env")

    last_error = None
    for provider in providers:
        cb = _nvidia_cb if provider == "nvidia" else _gemini_cb
        if not cb.is_available:
            logger.info(f"[Gateway] {provider} circuit OPEN — skipping")
            continue
        try:
            logger.info(f"[Gateway] Calling {provider} ({settings.nvidia_model if provider == 'nvidia' else settings.gemini_model})")
            if provider == "nvidia":
                result = await asyncio.wait_for(_call_nvidia(prompt, system, max_tokens), timeout=35.0)
            else:
                result = await _call_gemini(prompt, system, max_tokens)
            cb.record_success()
            return result
        except (RateLimitError, APIStatusError, APITimeoutError, asyncio.TimeoutError) as e:
            logger.warning(f"[Gateway] {provider} failed: {type(e).__name__}: {e}")
            cb.record_failure()
            last_error = e
        except Exception as e:
            logger.error(f"[Gateway] {provider} unexpected error: {e}")
            cb.record_failure()
            last_error = e

    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")


def get_gateway_stats() -> dict:
    return {
        "total_cost_usd": round(_total_cost_usd, 6),
        "nvidia": {
            "state": _nvidia_cb.state.value,
            "failures": _nvidia_cb._failures,
            "available": settings.nvidia_available,
        },
        "gemini": {
            "state": _gemini_cb.state.value,
            "failures": _gemini_cb._failures,
            "available": settings.gemini_available,
        },
    }
