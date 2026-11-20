# backend/app/core/crypto.py
"""
ObserVault Cryptographic Integrity & Replay Protection Engine.
Enforces HMAC-SHA256 signatures, timestamp drift validation, and nonce replay prevention.
"""

import hmac
import hashlib
import json
import time
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta

# In-memory LRU nonce replay cache with timestamp eviction
# For high-availability multi-instance setups, this can also back onto Redis.
class NonceCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._cache: Dict[str, float] = {}

    def is_replayed(self, nonce: str) -> bool:
        self._purge_expired()
        now = time.time()
        if nonce in self._cache:
            return True
        self._cache[nonce] = now
        return False

    def _purge_expired(self):
        now = time.time()
        expired = [n for n, ts in self._cache.items() if now - ts > self.ttl]
        for n in expired:
            del self._cache[n]

    def clear(self):
        self._cache.clear()

nonce_cache = NonceCache(ttl_seconds=300)

class TelemetrySigner:
    """
    Cryptographic batch signing and verification using HMAC-SHA256.
    Ensures message integrity and authenticity between Collector and SaaS Cloud.
    """
    MAX_CLOCK_SKEW_SECONDS = 300  # 5 minutes window

    @staticmethod
    def generate_canonical_string(collector_id: str, timestamp_str: str, nonce: str, payload_data: Any) -> bytes:
        """
        Creates a deterministic canonical byte representation of the telemetry payload.
        Sorts keys to guarantee identical hashing across platforms.
        """
        serialized = json.dumps(payload_data, sort_keys=True, separators=(',', ':'))
        canonical = f"{collector_id}|{timestamp_str}|{nonce}|{serialized}"
        return canonical.encode('utf-8')

    @classmethod
    def sign_batch(cls, secret_key: str, collector_id: str, timestamp_str: str, nonce: str, payload_data: Any) -> str:
        """
        Generates HMAC-SHA256 hex signature for a batch payload.
        """
        canonical_bytes = cls.generate_canonical_string(collector_id, timestamp_str, nonce, payload_data)
        signature = hmac.new(
            secret_key.encode('utf-8'),
            canonical_bytes,
            hashlib.sha256
        ).hexdigest()
        return signature

    @classmethod
    def verify_batch(
        cls,
        secret_key: str,
        collector_id: str,
        timestamp_str: str,
        nonce: str,
        signature: str,
        payload_data: Any
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates:
        1. Nonce uniqueness (Replay Attack Defense)
        2. Timestamp freshness (Clock Skew Window)
        3. HMAC-SHA256 cryptographic signature match (Tamper Resistance)
        """
        # 1. Nonce check
        if nonce_cache.is_replayed(nonce):
            return False, "Replay attack detected: Nonce has already been processed"

        # 2. Timestamp freshness check
        try:
            # Handle ISO formats
            if timestamp_str.endswith('Z'):
                ts = datetime.fromisoformat(timestamp_str[:-1] + '+00:00')
            else:
                ts = datetime.fromisoformat(timestamp_str)
            
            now = datetime.now(timezone.utc)
            skew = abs((now - ts).total_seconds())
            if skew > cls.MAX_CLOCK_SKEW_SECONDS:
                return False, f"Timestamp drift exceeds maximum allowable window ({skew:.1f}s > {cls.MAX_CLOCK_SKEW_SECONDS}s)"
        except Exception as e:
            return False, f"Malformed timestamp in request signature: {str(e)}"

        # 3. Signature verification
        expected_sig = cls.sign_batch(secret_key, collector_id, timestamp_str, nonce, payload_data)
        if not hmac.compare_digest(expected_sig, signature):
            return False, "Cryptographic signature mismatch: Payload integrity compromised"

        return True, None
