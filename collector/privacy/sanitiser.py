# collector/privacy/sanitiser.py
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List
from collector.privacy.allowlist import APPROVED_OUTBOUND_KEYS, SENSITIVE_KEY_PATTERNS

class LocalPrivacySanitiser:
    """
    Tier 1 Privacy Engine:
    Processes operational telemetry locally before any external transmission.
    Guarantees that raw logs, passwords, auth tokens, and sensitive payloads
    are stripped and never leave the customer's on-premises perimeter.
    """

    @staticmethod
    def sanitise_and_transform(raw_record: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Takes raw local operational record or log event.
        Returns:
            (outbound_metadata, privacy_summary)
        """
        raw_keys = set(raw_record.keys())
        rejected_keys: List[str] = []
        sensitive_flag_detected = False

        # 1. Audit incoming keys for sensitive attributes
        for k in raw_keys:
            if k not in APPROVED_OUTBOUND_KEYS:
                rejected_keys.append(k)
                lower_k = k.lower()
                if any(p in lower_k for p in SENSITIVE_KEY_PATTERNS):
                    sensitive_flag_detected = True

        # 2. Build a BRAND NEW metadata record from explicit allow-list only
        outbound: Dict[str, Any] = {}

        # Default fallback values for required fields
        now_iso = datetime.now(timezone.utc).isoformat()
        outbound["event_id"] = str(raw_record.get("event_id") or uuid.uuid4())
        outbound["timestamp"] = raw_record.get("timestamp") or now_iso
        outbound["server_id"] = str(raw_record.get("server_id") or "srv-local-node")
        outbound["hostname"] = str(raw_record.get("hostname") or "localhost")
        outbound["collector_id"] = str(raw_record.get("collector_id") or "col-edge-01")
        outbound["collector_version"] = str(raw_record.get("collector_version") or "1.0.0")

        # Numeric metrics (sanitized, bounded)
        outbound["cpu_percent"] = max(0.0, min(100.0, float(raw_record.get("cpu_percent", 0.0))))
        outbound["memory_percent"] = max(0.0, min(100.0, float(raw_record.get("memory_percent", 0.0))))
        outbound["disk_percent"] = max(0.0, min(100.0, float(raw_record.get("disk_percent", 0.0))))
        outbound["network_latency_ms"] = max(0.0, float(raw_record.get("network_latency_ms", 0.0)))
        outbound["packet_loss_percent"] = max(0.0, min(100.0, float(raw_record.get("packet_loss_percent", 0.0))))
        outbound["network_status"] = str(raw_record.get("network_status", "connected"))

        # Handling special security event transformation:
        # If the raw event was a failed login event containing sensitive fields (username, password, client ip),
        # we transform it purely into statistical metadata (failed_login_count) and NEVER send the credentials!
        if raw_record.get("event_type") == "failed_login" or "failed_attempt_count" in raw_record:
            outbound["failed_login_count"] = int(raw_record.get("failed_attempt_count", raw_record.get("failed_login_count", 1)))
        else:
            outbound["failed_login_count"] = int(raw_record.get("failed_login_count", 0))

        outbound["service_status"] = str(raw_record.get("service_status", "up"))
        outbound["is_simulated"] = bool(raw_record.get("is_simulated", False))

        # 3. Compile local privacy audit summary
        approved_count = len(outbound)
        rejected_count = len(rejected_keys)

        privacy_summary = {
            "local_processed_count": 1,
            "fields_approved": approved_count,
            "fields_rejected": rejected_count,
            "rejected_field_names": rejected_keys,
            "sensitive_data_stripped": True,
            "sanitization_timestamp": now_iso
        }

        # Embed privacy summary into outbound record
        outbound["privacy_summary"] = privacy_summary

        return outbound, privacy_summary
