# backend/app/ai/groq_client.py
"""
ObserVault Groq AI Client Gateway (Phase 3).
Encapsulates high-performance Groq API communication with:
- Asynchronous and synchronous completion interfaces
- Strict credential masking and safe logging (zero API keys or prompt contents logged)
- Bounded retries with exponential backoff for transient failures (429, connection, 5xx)
- Fail-fast handling for fatal authentication (401) and validation errors
- Explicit service availability status without startup network calls
- Strict refusal to fabricate fake responses when Groq is unavailable
"""

import os
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger("observault.ai.groq")


class GroqClientError(Exception):
    """Base exception for all Groq AI client operations."""
    pass


class GroqAuthenticationError(GroqClientError):
    """Raised when the Groq API key is missing, invalid, or revoked."""
    pass


class GroqRateLimitError(GroqClientError):
    """Raised when upstream rate limits (HTTP 429) are encountered and retries exhausted."""
    pass


class GroqTimeoutError(GroqClientError):
    """Raised when an API request exceeds the configured timeout window."""
    pass


class GroqServiceUnavailableError(GroqClientError):
    """Raised when the Groq service or network connectivity is unavailable."""
    pass


@dataclass
class GroqCompletionResult:
    """Structured response from a Groq completion call."""
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    finish_reason: Optional[str] = None


class GroqClient:
    """
    Production-grade Groq client gateway for ObserVault SaaS.
    """

    KNOWN_PLACEHOLDERS = {
        "",
        "gsk_your_groq_api_key_placeholder",
        "gsk_your_groq_api_key_here",
        "placeholder",
        "your-api-key-here"
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: int = 2
    ):
        self._api_key = api_key if api_key is not None else settings.GROQ_API_KEY
        self.default_model = default_model or settings.GROQ_MODEL
        self.timeout_seconds = timeout_seconds or settings.GROQ_TIMEOUT_SECONDS
        self.max_retries = max(0, max_retries)
        self._async_client = None

    @property
    def masked_key(self) -> Optional[str]:
        """Returns safe masked representation of API key for status inspection."""
        if not self._api_key or self._is_placeholder(self._api_key):
            return None
        clean_key = self._api_key.strip()
        if len(clean_key) <= 8:
            return "gsk_***"
        return f"{clean_key[:4]}...{clean_key[-4:]}"

    @classmethod
    def _is_placeholder(cls, key: str) -> bool:
        if not key or not isinstance(key, str):
            return True
        return key.strip().lower() in cls.KNOWN_PLACEHOLDERS

    def is_available(self) -> bool:
        """
        Explicit availability check: returns True only if a non-placeholder API key is configured.
        Does NOT make external network requests to check availability.
        """
        return bool(self._api_key and not self._is_placeholder(self._api_key))

    def get_status(self) -> Dict[str, Any]:
        """Returns sanitized status object for health checks and UI diagnostics."""
        available = self.is_available()
        return {
            "status": "available" if available else "unavailable",
            "model": self.default_model,
            "configured": available,
            "masked_key": self.masked_key,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries
        }

    def _get_async_client(self):
        """Lazy initializer for the underlying AsyncGroq client."""
        if not self.is_available():
            raise GroqAuthenticationError(
                "Groq API key is not configured or is a placeholder. AI intelligence service is unavailable."
            )
        if self._async_client is None:
            try:
                from groq import AsyncGroq
                self._async_client = AsyncGroq(
                    api_key=self._api_key,
                    timeout=self.timeout_seconds
                )
            except Exception as e:
                # Never expose credentials in init exceptions
                raise GroqClientError(f"Failed to initialize Groq SDK client: {e.__class__.__name__}")
        return self._async_client

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout_seconds: Optional[float] = None
    ) -> GroqCompletionResult:
        """
        Executes asynchronous chat completion with bounded retries on transient errors.

        Raises:
            GroqAuthenticationError: Missing/invalid key (HTTP 401).
            GroqRateLimitError: Rate limit exceeded (HTTP 429) after retries.
            GroqTimeoutError: Request exceeded deadline.
            GroqServiceUnavailableError: Upstream outage, network drop, or 5xx.
        """
        if not self.is_available():
            raise GroqAuthenticationError(
                "Groq API key is not configured or is a placeholder. AI intelligence service is unavailable."
            )

        if not messages or not isinstance(messages, list):
            raise GroqClientError("Messages parameter must be a non-empty list of message dictionaries.")

        target_model = model or self.default_model
        eff_temp = temperature if temperature is not None else settings.GROQ_TEMPERATURE
        eff_max_tokens = max_tokens if max_tokens is not None else settings.GROQ_MAX_TOKENS
        eff_timeout = timeout_seconds if timeout_seconds is not None else self.timeout_seconds

        client = self._get_async_client()

        # Import SDK error classes locally to handle mapped exceptions cleanly
        from groq import (
            AuthenticationError as SdkAuthError,
            RateLimitError as SdkRateLimitError,
            APITimeoutError as SdkTimeoutError,
            APIConnectionError as SdkConnectionError,
            InternalServerError as SdkInternalError,
            BadRequestError as SdkBadRequestError,
            APIError as SdkAPIError
        )

        attempts = self.max_retries + 1
        last_error = None
        start_time = time.perf_counter()

        for attempt in range(1, attempts + 1):
            try:
                call_start = time.perf_counter()
                response = await client.chat.completions.create(
                    model=target_model,
                    messages=messages,
                    temperature=eff_temp,
                    max_tokens=eff_max_tokens,
                    timeout=eff_timeout
                )
                latency_ms = (time.perf_counter() - call_start) * 1000.0

                choice = response.choices[0]
                content = choice.message.content or ""
                finish_reason = getattr(choice, "finish_reason", None)

                usage = getattr(response, "usage", None)
                p_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
                c_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
                t_tokens = getattr(usage, "total_tokens", 0) if usage else (p_tokens + c_tokens)

                logger.info(
                    "Groq completion successful: model=%s, tokens=%d, latency=%.1fms (attempt %d/%d)",
                    target_model,
                    t_tokens,
                    latency_ms,
                    attempt,
                    attempts
                )

                return GroqCompletionResult(
                    content=content,
                    model=response.model or target_model,
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=t_tokens,
                    latency_ms=latency_ms,
                    finish_reason=finish_reason
                )

            except SdkAuthError as e:
                # Fatal: Never retry authentication errors
                logger.warning("Groq authentication failure (HTTP 401). Request rejected.")
                raise GroqAuthenticationError("Groq authentication failed: invalid or revoked API key.") from None

            except SdkBadRequestError as e:
                # Fatal: Client sent malformed payload
                logger.warning("Groq bad request error: %s", e.__class__.__name__)
                raise GroqClientError(f"Groq rejected request payload: {getattr(e, 'message', 'Invalid parameter')}") from None

            except SdkTimeoutError as e:
                last_error = GroqTimeoutError(f"Groq API request timed out after {eff_timeout}s.")
                logger.warning("Groq timeout on attempt %d/%d (timeout=%.1fs)", attempt, attempts, eff_timeout)

            except SdkRateLimitError as e:
                last_error = GroqRateLimitError("Groq rate limit exceeded (HTTP 429).")
                logger.warning("Groq rate limit on attempt %d/%d", attempt, attempts)

            except (SdkConnectionError, SdkInternalError) as e:
                last_error = GroqServiceUnavailableError(
                    f"Groq service unavailable or network connection failed ({e.__class__.__name__})."
                )
                logger.warning("Groq transient failure on attempt %d/%d: %s", attempt, attempts, e.__class__.__name__)

            except SdkAPIError as e:
                status_code = getattr(e, "status_code", 500)
                if status_code in (500, 502, 503, 504):
                    last_error = GroqServiceUnavailableError(f"Groq upstream service error (HTTP {status_code}).")
                    logger.warning("Groq upstream HTTP %d on attempt %d/%d", status_code, attempt, attempts)
                else:
                    raise GroqClientError(f"Groq API error (HTTP {status_code}).") from None

            except asyncio.TimeoutError:
                last_error = GroqTimeoutError(f"Request timed out after {eff_timeout}s.")
                logger.warning("Asyncio timeout on attempt %d/%d", attempt, attempts)

            except Exception as e:
                last_error = GroqClientError(f"Unexpected error communicating with Groq: {e.__class__.__name__}")
                logger.warning("Unexpected Groq exception on attempt %d/%d: %s", attempt, attempts, e.__class__.__name__)

            # If not the last attempt, backoff exponentially before retrying
            if attempt < attempts:
                backoff_delay = 0.5 * (2 ** (attempt - 1))
                logger.info("Retrying Groq request in %.2fs (attempt %d of %d)...", backoff_delay, attempt + 1, attempts)
                await asyncio.sleep(backoff_delay)

        # All retries exhausted
        if last_error:
            raise last_error
        raise GroqServiceUnavailableError("Groq service failed after retry limit.")

    def chat_completion_sync(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout_seconds: Optional[float] = None
    ) -> GroqCompletionResult:
        """Synchronous wrapper for execution within non-async workers or scripts."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # In a running event loop (e.g., inside FastAPI worker), run in dedicated thread/runner
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(
                    asyncio.run,
                    self.chat_completion(
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout_seconds=timeout_seconds
                    )
                )
                return fut.result()
        else:
            return loop.run_until_complete(
                self.chat_completion(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout_seconds=timeout_seconds
                )
            )

    def __repr__(self) -> str:
        return f"<GroqClient model='{self.default_model}' available={self.is_available()} key='{self.masked_key}'>"

    def __str__(self) -> str:
        return self.__repr__()


# Singleton Instance & Accessors
_groq_client_instance: Optional[GroqClient] = None


def get_groq_client() -> GroqClient:
    """Returns shared singleton instance of GroqClient."""
    global _groq_client_instance
    if _groq_client_instance is None:
        _groq_client_instance = GroqClient()
    return _groq_client_instance


def reset_groq_client() -> None:
    """Resets the singleton instance (primarily used for unit testing)."""
    global _groq_client_instance
    _groq_client_instance = None
