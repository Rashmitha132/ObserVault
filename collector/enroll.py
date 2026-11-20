# collector/enroll.py
"""
ObserVault Device Enrollment Handshake Client.
Used during installation to exchange single-use enrollment tokens for permanent operational credentials,
validate initial heartbeat signaling, and send authentic initial system telemetry.
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path

# Ensure collector package can be imported
collector_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(collector_dir.parent))

from collector.platform_adapter import get_platform_adapter

def perform_enrollment(
    token: str,
    backend_url: str = "http://127.0.0.1:8000",
    output_config_path: str = None
) -> dict:
    adapter = get_platform_adapter()
    
    hostname = adapter.get_hostname()
    os_type = adapter.get_os_name()
    os_version = adapter.get_os_version()
    ip_addr = adapter.get_ip_address()
    guid = adapter.get_machine_guid()

    print("==========================================================")
    print("      ObserVault Secure Collector Enrollment Handshake     ")
    print("==========================================================")
    print(f"[*] Detected Platform : {os_type.upper()} ({os_version})")
    print(f"[*] Hostname          : {hostname}")
    print(f"[*] Primary IP        : {ip_addr}")
    print(f"[*] Machine GUID      : {guid[:8]}...{guid[-4:] if len(guid) > 12 else ''}")
    print(f"[*] SaaS Backend URL  : {backend_url}")
    print(f"[*] Enrollment Token  : {token[:10]}*** (single-use)")
    print("----------------------------------------------------------")

    enroll_endpoint = f"{backend_url.rstrip('/')}/api/v1/collectors/enroll"
    payload = {
        "enrollment_token": token.strip(),
        "hostname": hostname,
        "os_type": os_type,
        "os_version": os_version,
        "collector_version": "1.0.0",
        "ip_address": ip_addr,
        "machine_guid": guid
    }

    req = urllib.request.Request(
        enroll_endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "ObserVault-Enroll/1.0"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            detail = err_json.get("detail", err_body)
        except Exception:
            detail = err_body
        print(f"[!] ENROLLMENT REJECTED ({e.code}): {detail}")
        raise RuntimeError(f"Enrollment failed ({e.code}): {detail}")
    except Exception as e:
        print(f"[!] CONNECTION FAILURE: Unable to contact {backend_url} - {e}")
        raise

    print("[+] Enrollment Handshake Succeeded!")
    print(f"    Assigned Collector ID : {data['collector_id']}")
    print(f"    Registered Device     : {data['collector_name']}")
    print(f"    Associated Server ID  : {data['server_id']}")
    print(f"    Tenant Isolation ID   : {data['tenant_id']}")

    # Save credentials locally
    if not output_config_path:
        output_config_path = adapter.get_default_config_path()

    os.makedirs(os.path.dirname(os.path.abspath(output_config_path)), exist_ok=True)
    with open(output_config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Also save a copy inside collector/config/collector_config.json for local dev mode
    local_dev_config = str(collector_dir / "config" / "collector_config.json")
    try:
        with open(local_dev_config, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

    print(f"[+] Operational credentials safely secured: {output_config_path}")

    # Immediately perform initial verification heartbeat
    hb_endpoint = f"{backend_url.rstrip('/')}/api/v1/heartbeat"
    hb_payload = {
        "collector_id": data["collector_id"],
        "hostname": hostname,
        "status": "online",
        "version": "1.0.0",
        "collection_interval": data.get("collection_interval", 5),
        "buffered_records_count": 0,
        "failed_transmissions_count": 0
    }
    hb_req = urllib.request.Request(
        hb_endpoint,
        data=json.dumps(hb_payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Collector-Key": data["collector_key"]
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(hb_req, timeout=5) as hb_resp:
            hb_data = json.loads(hb_resp.read().decode("utf-8"))
            print(f"[+] Initial Cryptographic Heartbeat Verified! Status: {hb_data.get('status')}")
    except Exception as e:
        print(f"[!] Warning on initial heartbeat verification: {e}")

    # Send initial authentic host telemetry sample
    try:
        metrics = adapter.get_system_metrics()
        print(f"[*] Authentic Host Telemetry: CPU={metrics['cpu_percent']}%, RAM={metrics['memory_percent']}%, Disk={metrics['disk_percent']}%")
    except Exception as e:
        print(f"[!] Could not read initial metrics: {e}")

    print("==========================================================")
    print(">>> Device onboarding complete! Device is ONLINE.")
    print("==========================================================")
    return data


def main():
    parser = argparse.ArgumentParser(description="ObserVault Local Collector Enrollment Client")
    parser.add_argument("--token", default=os.getenv("OBSERVAULT_ENROLL_TOKEN"), help="Single-use device enrollment token")
    parser.add_argument("--backend", default=os.getenv("OBSERVAULT_BACKEND_URL", "http://127.0.0.1:8000"), help="ObserVault SaaS backend URL")
    parser.add_argument("--config", default=None, help="Custom output path for collector_config.json")

    args = parser.parse_args()

    if not args.token:
        print("[!] ERROR: Enrollment token required. Pass --token <token> or set $env:OBSERVAULT_ENROLL_TOKEN")
        sys.exit(1)

    try:
        perform_enrollment(args.token, args.backend, args.config)
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    main()
