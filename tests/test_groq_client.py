# tests/test_groq_client.py
"""
ObserVault Groq AI Client Automated Test Suite (Phase 3 - Step 1).
Validates:
1. Client initialization and secure credential masking.
2. Missing or placeholder API key detection (fail-fast availability).
3. Successful completion against mocked AsyncGroq backend.
4. Immediate failure on invalid API key (HTTP 401 AuthenticationError) without retry loops.
5. Timeout handling and mapping to GroqTimeoutError.
6. Rate-limit (HTTP 429) backoff handling and mapping to GroqRateLimitError.
7. Transient error retry recovery (fails once, recovers on retry).
8. Bounded retry enforcement (stops at max_retries).
9. Singleton lifecycle (get_groq_client, reset_groq_client).
10. Synchronous wrapper execution.
"""

import sys
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from app.core.config import settings
from app.ai.groq_client import (
    GroqClient,
    GroqClientError,
    GroqAuthenticationError,
    GroqRateLimitError,
    GroqTimeoutError,
    GroqServiceUnavailableError,
    GroqCompletionResult,
    get_groq_client,
    reset_groq_client
)
import groq


def test_client_initialization_and_masking():
    """Verify client initialization, default parameters, and credential masking."""
    client = GroqClient(api_key="gsk_test_secret_key_12345", default_model="openai/gpt-oss-120b")
    assert client.default_model == "openai/gpt-oss-120b"
    assert client.is_available() is True
    assert client.masked_key == "gsk_...2345"
    assert "gsk_test_secret_key_12345" not in repr(client)
    assert "gsk_test_secret_key_12345" not in str(client)

    status = client.get_status()
    assert status["status"] == "available"
    assert status["configured"] is True
    assert status["masked_key"] == "gsk_...2345"


def test_missing_and_placeholder_api_key():
    """Verify missing or placeholder keys return unavailable and reject completions immediately."""
    placeholders = [
        "",
        "   ",
        "gsk_your_groq_api_key_placeholder",
        "gsk_your_groq_api_key_here",
        None
    ]
    with patch.object(settings, "GROQ_API_KEY", ""):
        for key in placeholders:
            client = GroqClient(api_key=key)
            assert client.is_available() is False
            assert client.masked_key is None
            assert client.get_status()["status"] == "unavailable"

            with pytest.raises(GroqAuthenticationError) as exc_info:
                asyncio.run(client.chat_completion([{"role": "user", "content": "ping"}]))
            assert "not configured or is a placeholder" in str(exc_info.value)


def test_successful_mocked_completion():
    """Verify successful response parsing and usage metrics mapping."""
    client = GroqClient(api_key="gsk_mock_valid_key_0001", max_retries=1)

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "All services operational within latency SLO."
    mock_choice.finish_reason = "stop"
    mock_response.choices = [mock_choice]
    mock_response.model = "openai/gpt-oss-120b"
    mock_response.usage.prompt_tokens = 45
    mock_response.usage.completion_tokens = 12
    mock_response.usage.total_tokens = 57

    mock_async_groq = MagicMock()
    mock_async_groq.chat.completions.create = AsyncMock(return_value=mock_response)
    client._async_client = mock_async_groq

    res = asyncio.run(client.chat_completion(
        messages=[{"role": "user", "content": "Status check"}],
        model="openai/gpt-oss-120b",
        temperature=0.1
    ))

    assert isinstance(res, GroqCompletionResult)
    assert res.content == "All services operational within latency SLO."
    assert res.model == "openai/gpt-oss-120b"
    assert res.prompt_tokens == 45
    assert res.completion_tokens == 12
    assert res.total_tokens == 57
    assert res.latency_ms >= 0.0
    assert mock_async_groq.chat.completions.create.call_count == 1


def test_invalid_api_key_fatal_no_retry():
    """Verify 401 AuthenticationError fails fast without retrying."""
    client = GroqClient(api_key="gsk_invalid_key_9999", max_retries=3)

    mock_request = MagicMock()
    auth_err = groq.AuthenticationError(
        message="Invalid API Key provided",
        response=MagicMock(status_code=401),
        body={"error": {"message": "Invalid API Key"}}
    )

    mock_async_groq = MagicMock()
    mock_async_groq.chat.completions.create = AsyncMock(side_effect=auth_err)
    client._async_client = mock_async_groq

    with pytest.raises(GroqAuthenticationError) as exc_info:
        asyncio.run(client.chat_completion([{"role": "user", "content": "analyze"}]))

    assert "invalid or revoked API key" in str(exc_info.value)
    # Must fail immediately on attempt 1 without retries
    assert mock_async_groq.chat.completions.create.call_count == 1


def test_timeout_handling():
    """Verify APITimeoutError maps to GroqTimeoutError."""
    client = GroqClient(api_key="gsk_valid_key_timeout", max_retries=1)

    timeout_err = groq.APITimeoutError(request=MagicMock())
    mock_async_groq = MagicMock()
    mock_async_groq.chat.completions.create = AsyncMock(side_effect=timeout_err)
    client._async_client = mock_async_groq

    with pytest.raises(GroqTimeoutError) as exc_info:
        asyncio.run(client.chat_completion([{"role": "user", "content": "slow"}]))

    assert "timed out" in str(exc_info.value)
    # Retried max_retries + 1 times (1 + 1 = 2)
    assert mock_async_groq.chat.completions.create.call_count == 2


def test_rate_limit_handling():
    """Verify HTTP 429 maps to GroqRateLimitError when retries are exhausted."""
    client = GroqClient(api_key="gsk_valid_key_ratelimit", max_retries=1)

    rate_err = groq.RateLimitError(
        message="Rate limit exceeded",
        response=MagicMock(status_code=429),
        body={"error": {"message": "Rate limit exceeded"}}
    )
    mock_async_groq = MagicMock()
    mock_async_groq.chat.completions.create = AsyncMock(side_effect=rate_err)
    client._async_client = mock_async_groq

    with pytest.raises(GroqRateLimitError) as exc_info:
        asyncio.run(client.chat_completion([{"role": "user", "content": "burst"}]))

    assert "rate limit exceeded" in str(exc_info.value).lower()
    assert mock_async_groq.chat.completions.create.call_count == 2


def test_transient_error_retry_and_recovery():
    """Verify transient connection failure retries and recovers on subsequent attempt."""
    client = GroqClient(api_key="gsk_valid_key_recover", max_retries=2)

    conn_err = groq.APIConnectionError(request=MagicMock(), message="Temporary connection drop")

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Recovered response after transient glitch"
    mock_response.choices = [mock_choice]
    mock_response.model = "openai/gpt-oss-120b"
    mock_response.usage = None

    mock_async_groq = MagicMock()
    # First attempt fails with connection error, second attempt succeeds
    mock_async_groq.chat.completions.create = AsyncMock(side_effect=[conn_err, mock_response])
    client._async_client = mock_async_groq

    res = asyncio.run(client.chat_completion([{"role": "user", "content": "retry test"}]))

    assert res.content == "Recovered response after transient glitch"
    assert mock_async_groq.chat.completions.create.call_count == 2


def test_retry_limits_exhausted():
    """Verify bounded retry limit: ceases attempts and raises GroqServiceUnavailableError."""
    client = GroqClient(api_key="gsk_valid_key_exhaust", max_retries=2)

    conn_err = groq.APIConnectionError(request=MagicMock(), message="Persistent network outage")
    mock_async_groq = MagicMock()
    mock_async_groq.chat.completions.create = AsyncMock(side_effect=conn_err)
    client._async_client = mock_async_groq

    with pytest.raises(GroqServiceUnavailableError) as exc_info:
        asyncio.run(client.chat_completion([{"role": "user", "content": "persistent drop"}]))

    assert "service unavailable" in str(exc_info.value).lower()
    # Initial attempt + 2 retries = 3 attempts total
    assert mock_async_groq.chat.completions.create.call_count == 3


def test_singleton_lifecycle():
    """Verify get_groq_client returns singleton and reset_groq_client refreshes."""
    reset_groq_client()
    c1 = get_groq_client()
    c2 = get_groq_client()
    assert c1 is c2

    reset_groq_client()
    c3 = get_groq_client()
    assert c3 is not c1


def test_sync_wrapper_execution():
    """Verify synchronous chat_completion_sync executes and returns GroqCompletionResult."""
    client = GroqClient(api_key="gsk_valid_sync_test", max_retries=0)

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Sync completion response"
    mock_response.choices = [mock_choice]
    mock_response.model = "openai/gpt-oss-120b"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5
    mock_response.usage.total_tokens = 15

    mock_async_groq = MagicMock()
    mock_async_groq.chat.completions.create = AsyncMock(return_value=mock_response)
    client._async_client = mock_async_groq

    res = client.chat_completion_sync([{"role": "user", "content": "sync check"}])
    assert res.content == "Sync completion response"
    assert res.total_tokens == 15
