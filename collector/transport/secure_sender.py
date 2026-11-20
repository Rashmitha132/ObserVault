# collector/transport/secure_sender.py
import uuid
import requests
from typing import List, Dict, Any, Tuple
from collector.config.settings import settings
from collector.buffer.sqlite_buffer import SQLiteBuffer

class SecureSender:
    """
    Tier 1 Secure Transport Layer:
    Handles authenticated communication with the ObserVault SaaS Backend.
    Enforces header authentication (X-Collector-Key), batch transmission,
    offline resiliency, and heartbeat signaling.
    """
    def __init__(self, buffer: SQLiteBuffer):
        self.buffer = buffer
        self.base_url = settings.BACKEND_URL.rstrip("/")
        self.collector_key = settings.COLLECTOR_KEY
        self.session = requests.Session()
        self.session.headers.update({
            "X-Collector-Key": self.collector_key,
            "Content-Type": "application/json",
            "User-Agent": f"ObserVault-Collector/{settings.COLLECTOR_VERSION}"
        })

    def send_heartbeat(self) -> bool:
        """
        Sends collector health & buffer status heartbeat.
        """
        self.session.headers["X-Collector-Key"] = settings.COLLECTOR_KEY
        url = f"{settings.BACKEND_URL.rstrip('/')}/api/v1/heartbeat"
        stats = self.buffer.get_stats()
        payload = {
            "collector_id": settings.COLLECTOR_ID,
            "hostname": settings.HOSTNAME,
            "status": "online",
            "version": settings.COLLECTOR_VERSION,
            "collection_interval": settings.COLLECTION_INTERVAL_SECONDS,
            "buffered_records_count": stats["pending"],
            "failed_transmissions_count": stats["failed"]
        }
        try:
            resp = self.session.post(url, json=payload, timeout=3.0)
            return resp.status_code == 200
        except Exception as e:
            # Network interruption / backend offline
            return False

    def flush_pending_records(self, batch_size: int = 50) -> Tuple[int, int]:
        """
        Retrieves pending records from local SQLite buffer and securely transmits to SaaS.
        Returns:
            (records_delivered_count, records_failed_count)
        """
        pending_items = self.buffer.get_pending(limit=batch_size)
        if not pending_items:
            return 0, 0

        event_ids = [item["event_id"] for item in pending_items]
        records_payload = [item["payload"] for item in pending_items]

        batch_id = f"batch-{uuid.uuid4().hex[:12]}"
        payload = {
            "batch_id": batch_id,
            "collector_id": settings.COLLECTOR_ID,
            "records": records_payload
        }

        self.session.headers["X-Collector-Key"] = settings.COLLECTOR_KEY
        url = f"{settings.BACKEND_URL.rstrip('/')}/api/v1/telemetry"
        try:
            resp = self.session.post(url, json=payload, timeout=5.0)
            if resp.status_code == 200:
                # Successfully delivered! Mark delivered in local buffer
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
