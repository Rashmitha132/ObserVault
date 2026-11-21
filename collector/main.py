# collector/main.py
import argparse
import time
import sys
import os
import json
from datetime import datetime, timezone

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collector.config.settings import settings
from collector.collectors.system_metrics import SystemMetricsCollector
from collector.collectors.network_metrics import NetworkMetricsCollector
from collector.platform_adapter import get_platform_adapter
from collector.privacy.sanitiser import LocalPrivacySanitiser
from collector.buffer.sqlite_buffer import SQLiteBuffer
from collector.transport.secure_sender import SecureSender
from collector.simulator.scenario_generator import ScenarioGenerator

def run_privacy_test():
    """
    Explicit Privacy & Egress Verification Test:
    Creates a simulated dirty raw event with fake passwords, tokens, API keys.
    Demonstrates that the local privacy sanitiser strips them completely before buffering.
    """
    print("\n" + "="*70)
    print("  OBSERVAULT TIER-1 LOCAL PRIVACY & EGRESS TEST")
    print("="*70)
    
    raw_dirty_event = {
        "event_id": "test-evt-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "failed_login",
        "failed_attempt_count": 6,
        "username": "superadmin_dev",
        "password": "SuperSecretPassword123!DoNotLeak",
        "auth_token": "bearer_jwt_token_header_secret_xyz",
        "api_key": "sk_live_internal_api_secret_999",
        "ip_address": "192.168.1.100",
        "server_id": "srv-acme-prod-01",
        "hostname": "acme-prod-01",
        "cpu_percent": 45.2,
        "memory_percent": 68.1,
        "disk_percent": 54.0,
        "network_latency_ms": 24.5,
        "packet_loss_percent": 0.0,
        "raw_payload": "SELECT * FROM users WHERE auth_hash='secret'"
    }

    print("\n[STEP 1: RAW OPERATIONAL TELEMETRY RECEIVED LOCALLY]")
    print(json.dumps(raw_dirty_event, indent=2))

    print("\n[STEP 2: RUNNING LOCAL PRIVACY PROCESSING & METADATA ALLOW-LIST]")
    outbound, privacy_summary = LocalPrivacySanitiser.sanitise_and_transform(raw_dirty_event)

    print("\n[STEP 3: SANITIZATION AUDIT SUMMARY]")
    print(f" - Local Fields Processed: {privacy_summary['local_processed_count']}")
    print(f" - Approved Fields:        {privacy_summary['fields_approved']}")
    print(f" - Rejected Fields Count:  {privacy_summary['fields_rejected']}")
    print(f" - Stripped Field Names:   {privacy_summary['rejected_field_names']}")
    print(f" - Sensitive Data Dropped: {privacy_summary['sensitive_data_stripped']}")

    print("\n[STEP 4: APPROVED OUTBOUND METADATA TO TRANSMIT]")
    print(json.dumps(outbound, indent=2))

    # Assertions
    assert "password" not in outbound, "FAIL: password leaked into outbound metadata!"
    assert "auth_token" not in outbound, "FAIL: auth_token leaked!"
    assert "api_key" not in outbound, "FAIL: api_key leaked!"
    assert "raw_payload" not in outbound, "FAIL: raw_payload leaked!"
    assert "username" not in outbound, "FAIL: username leaked!"
    assert outbound["failed_login_count"] == 6, "FAIL: failed_login_count not retained!"

    print("\n[VERIFICATION PASSED]: Zero credentials or sensitive payloads exist in outbound metadata.")
    print("="*70 + "\n")

def main():
    parser = argparse.ArgumentParser(description="ObserVault Local Telemetry Collector")
    parser.add_argument("--mode", choices=["live", "simulate"], default="live", help="Collection mode: 'live' uses psutil, 'simulate' uses scenario generator")
    parser.add_argument("--scenario", default="normal", choices=["normal", "high_cpu", "network_failure", "security_event", "application_failure"], help="Scenario to generate in simulate mode")
    parser.add_argument("--offline", action="store_true", help="Simulate network offline mode (enqueues to SQLite buffer without transmitting)")
    parser.add_argument("--test-privacy", action="store_true", help="Run explicit local privacy sanitisation demonstration")
    parser.add_argument("--once", action="store_true", help="Run one collection cycle and exit")
    parser.add_argument("--interval", type=int, default=settings.COLLECTION_INTERVAL_SECONDS, help="Collection interval in seconds")
    parser.add_argument("--log-file", type=str, default=None, help="Redirect stdout/stderr to specified log file")

    args = parser.parse_args()

    if args.log_file:
        try:
            log_f = open(args.log_file, "a", encoding="utf-8", buffering=1)
            sys.stdout = log_f
            sys.stderr = log_f
        except Exception:
            pass

    if args.test_privacy:
        run_privacy_test()
        return

    print("="*65)
    print(f"  OBSERVAULT TIER-1 LOCAL COLLECTOR (v{settings.COLLECTOR_VERSION})")
    print(f"  Target SaaS Backend: {settings.BACKEND_URL}")
    print(f"  Collector ID:        {settings.COLLECTOR_ID}")
    print(f"  Host:                {settings.HOSTNAME}")
    print(f"  Mode:                {args.mode.upper()} {'(OFFLINE BUFFERING)' if args.offline else ''}")
    print("="*65)

    settings.load() if hasattr(settings, "load") else None

    buffer = SQLiteBuffer(settings.BUFFER_DB_PATH)
    sender = SecureSender(buffer)
    platform_adapter = get_platform_adapter()
    net_collector = NetworkMetricsCollector(settings.BACKEND_URL)
    scenario_gen = ScenarioGenerator(server_id=settings.SERVER_ID, hostname=settings.HOSTNAME)

    last_heartbeat_time = 0.0

    try:
        while True:
            cycle_start = time.time()

            # 1. Collect Telemetry
            if args.mode == "live":
                sys_metrics = platform_adapter.get_system_metrics()
                net_metrics = net_collector.measure_network()
                raw_record = {
                    "server_id": settings.SERVER_ID,
                    "hostname": settings.HOSTNAME,
                    "collector_id": settings.COLLECTOR_ID,
                    "collector_version": settings.COLLECTOR_VERSION,
                    **sys_metrics,
                    **net_metrics,
                    "failed_login_count": 0,
                    "service_status": "up"
                }
            else:
                raw_record = scenario_gen.generate(args.scenario)
                raw_record["collector_id"] = settings.COLLECTOR_ID
                raw_record["collector_version"] = settings.COLLECTOR_VERSION

            # 2. Local Privacy Processing (Tier 1 Allow-List)
            outbound_record, privacy_summary = LocalPrivacySanitiser.sanitise_and_transform(raw_record)

            # 3. Local SQLite Buffering
            event_id = outbound_record["event_id"]
            buffer.enqueue(event_id, outbound_record)

            # 4. Transmit to SaaS Backend (if not in offline simulation mode)
            stats = buffer.get_stats()
            delivered_count = 0
            if not args.offline:
                # Send heartbeat if interval elapsed
                if cycle_start - last_heartbeat_time >= settings.HEARTBEAT_INTERVAL_SECONDS:
                    hb_ok = sender.send_heartbeat()
                    last_heartbeat_time = cycle_start
                    if hb_ok:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Heartbeat acknowledged by SaaS.")

                # Flush pending buffered records
                delivered, failed = sender.flush_pending_records(batch_size=20)
                delivered_count = delivered
                stats = buffer.get_stats()

            # Display Status
            status_tag = "[OFFLINE BUFFERED]" if args.offline else (f"[TRANSMITTED {delivered_count} RECORD(S)]" if delivered_count > 0 else "[PENDING BUFFER]")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {status_tag} CPU: {outbound_record['cpu_percent']}% | Mem: {outbound_record['memory_percent']}% | Latency: {outbound_record['network_latency_ms']}ms | Buffer: {stats['pending']} pending, {stats['delivered']} delivered")

            if args.once:
                break

            # Sleep remaining interval
            elapsed = time.time() - cycle_start
            sleep_time = max(0.5, args.interval - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nCollector gracefully stopped.")

if __name__ == "__main__":
    main()
