# collector/transport/signed_transport.py
"""
ObserVault Signed Transport Layer.
Extends the collector's secure sender to attach HMAC-SHA256 batch signatures,
timestamp drift windows, and anti-replay nonces to all egress traffic.
"""

import uuid
import secrets
import hmac
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from collector.transport.secure_sender import SecureSender
from collector.config.settings import settings

class SignedTransport(SecureSender):
    """
    Cryptographically signs all outbound telemetry batches before egress.
    Defends against batch tampering, unauthorized injection, and replay attacks.
    """
    def __init__(self, buffer):
        super().__init__(buffer)
        # Shared symmetric secret or collector private key for HMAC signing
        self.signing_key = getattr(settings, "SIGNING_KEY", settings.SECRET_KEY if hasattr(settings, "SECRET_KEY") else "observault-insecure-dev-secret-key-change-in-prod-2026")

    def _generate_signature(self, batch_payload: Dict[str, Any], timestamp_str: str, nonce: str) -> str:
        serialized = json.dumps(batch_payload, sort_keys=True, separators=(',', ':'))
        canonical = f"{settings.COLLECTOR_ID}|{timestamp_str}|{nonce}|{serialized}"
        return hmac.new(
            self.signing_key.encode('utf-8'),
            canonical.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def flush_pending_records_signed(self, batch_size: int = 50) -> Tuple[int, int]:
        """
        Retrieves records from local SQLite buffer, constructs batch, signs it with HMAC-SHA256,
        and transmits with anti-replay headers.
        """
        pending_items = self.buffer.get_pending(limit=batch_size)
        if not pending_items:
            return 0, 0

        event_ids = [item["event_id"] for item in pending_items]
        records_payload = [item["payload"] for item in pending_items]

        batch_id = f"batch-signed-{uuid.uuid4().hex[:12]}"
        payload = {
            "batch_id": batch_id,
            "collector_id": settings.COLLECTOR_ID,
            "records": records_payload
        }

        now_str = datetime.now(timezone.utc).isoformat()
        nonce = f"nonce-{secrets.token_hex(16)}"
        signature = self._generate_signature(payload, now_str, nonce)

        headers = {
            "X-Signature": signature,
            "X-Timestamp": now_str,
            "X-Nonce": nonce
        }

        url = f"{self.base_url}/api/v1/telemetry"
        try:
            resp = self.session.post(url, json=payload, headers=headers, timeout=5.0)
            if resp.status_code == 200:
                self.buffer.mark_delivered(event_ids)
                return len(event_ids), 0
            else:
                err_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                self.buffer.mark_failed(event_ids, err_msg)
                return 0, len(event_ids)
        except Exception as e:
            err_msg = f"Transport network error: {str(e)}"
            self.buffer.mark_failed(event_ids, err_msg)
            return 0, len(event_ids)
