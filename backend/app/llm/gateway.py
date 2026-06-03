"""
Nova AI — LLM Gateway
Primary: NVIDIA NIM (llama-3.3-70b-instruct via OpenAI-compatible API)
Circuit breaker for NVIDIA provider. Retry with backoff. Cost tracking.
"""
import asyncio
import time
import logging
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from openai import AsyncOpenAI, RateLimitError, APIStatusError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

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

# Cost tracking (rough estimates per 1M tokens)
NVIDIA_COST_PER_1M = 0.35   # llama-3.3-70b on NIM

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


def _format_api_error(e: Exception) -> str:
    """Extract meaningful error details from OpenAI SDK exceptions."""
    parts = [type(e).__name__]
    if isinstance(e, APIStatusError):
        parts.append(f"status={e.status_code}")
        try:
            body = e.response.text[:500] if hasattr(e, "response") and e.response else "no response body"
            parts.append(f"body={body}")
        except Exception:
            pass
    msg = str(e).strip()
    if msg:
        parts.append(msg)
    else:
        parts.append("No additional error message provided by exception")
    return " | ".join(parts)


@retry(
    retry=retry_if_exception_type((RateLimitError, asyncio.TimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _call_nvidia(prompt: str, system: str, max_tokens: int = 1024) -> str:
    client = _get_nvidia_client()
    start_t = time.time()
    response = await client.chat.completions.create(
        model=settings.nvidia_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    elapsed = time.time() - start_t
    usage = response.usage
    tokens_used = 0
    if usage:
        tokens_used = usage.total_tokens
        cost = (tokens_used / 1_000_000) * NVIDIA_COST_PER_1M
        global _total_cost_usd
        _total_cost_usd += cost
    content = response.choices[0].message.content or ""
    # Strip <think> tags from reasoning models
    if "<think>" in content:
        content = content.split("</think>")[-1].strip()
    logger.info(f"[Gateway] NVIDIA response: {elapsed:.1f}s, {tokens_used} tokens, {len(content)} chars")
    return content


async def llm_complete(
    prompt: str,
    system: str = "You are a professional marketing analyst. Return only valid JSON as instructed.",
    max_tokens: int = 1024,
    provider_hint: str = "auto",
) -> str:
    """
    Route an LLM completion through NVIDIA NIM.
    Returns the text response string.
    """
    if not settings.nvidia_available:
        raise RuntimeError("NVIDIA API Key is not configured. Add NVIDIA_API_KEY to .env")

    if not _nvidia_cb.is_available:
        raise RuntimeError(
            "NVIDIA circuit breaker is OPEN (temporarily disabled due to consecutive errors). "
            "Please check your API key or wait for recovery timeout (90s)."
        )

    try:
        logger.info(f"[Gateway] Calling NVIDIA ({settings.nvidia_model}) | prompt={len(prompt)} chars, max_tokens={max_tokens}")
        result = await asyncio.wait_for(_call_nvidia(prompt, system, max_tokens), timeout=45.0)
        _nvidia_cb.record_success()
        return result
    except (RateLimitError, APIStatusError, APITimeoutError, asyncio.TimeoutError) as e:
        error_detail = _format_api_error(e)
        logger.error(f"[Gateway] NVIDIA API error: {error_detail}")
        _nvidia_cb.record_failure()
        raise RuntimeError(f"NVIDIA LLM provider failed: {error_detail}") from e
    except Exception as e:
        error_detail = _format_api_error(e)
        logger.error(f"[Gateway] NVIDIA unexpected error: {error_detail}\n{traceback.format_exc()}")
        _nvidia_cb.record_failure()
        raise RuntimeError(f"NVIDIA LLM provider unexpected error: {error_detail}") from e


def get_gateway_stats() -> dict:
    return {
        "total_cost_usd": round(_total_cost_usd, 6),
        "nvidia": {
            "state": _nvidia_cb.state.value,
            "failures": _nvidia_cb._failures,
            "available": settings.nvidia_available,
            "model": settings.nvidia_model,
        },
    }

