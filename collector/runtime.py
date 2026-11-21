# collector/runtime.py
"""
ObserVault Windows Collector Runtime & Lifecycle Manager.
Provides persistent background daemon execution, process tracking, status diagnostics,
and graceful start/stop controls for edge collector hosts.
"""

import os
import sys
import time
import json
import signal
import subprocess
from pathlib import Path

# Base directories
collector_dir = Path(__file__).resolve().parent
project_dir = collector_dir.parent

sys.path.insert(0, str(project_dir))

from collector.config.settings import settings
from collector.buffer.sqlite_buffer import SQLiteBuffer

def get_runtime_dir() -> Path:
    """Returns directory for PID, logs, and state storage."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        p = Path(local_app_data) / "ObserVault" / "Collector"
    else:
        p = collector_dir / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p

PID_FILE = get_runtime_dir() / "collector.pid"
LOG_FILE = get_runtime_dir() / "collector.log"

def is_pid_running(pid: int) -> bool:
    """Check if process with given PID is currently active."""
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        try:
            # Query tasklist for PID
            output = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                text=True,
                stderr=subprocess.DEVNULL
            )
            return str(pid) in output and "python" in output.lower()
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

def get_running_pid() -> int | None:
    """Read PID file and return PID if actively running."""
    if PID_FILE.exists():
        try:
            content = PID_FILE.read_text(encoding="utf-8").strip()
            if content.isdigit():
                pid = int(content)
                if is_pid_running(pid):
                    return pid
                else:
                    # Stale PID file
                    PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
    return None

def start_daemon(foreground: bool = False):
    """Start collector process in foreground or detached background."""
    active_pid = get_running_pid()
    if active_pid:
        print(f"[!] ObserVault Collector is ALREADY RUNNING (PID: {active_pid}).")
        return active_pid

    # Check if collector is configured
    settings.load() if hasattr(settings, "load") else None
    config_file = get_runtime_dir() / "collector_config.json"
    local_config = collector_dir / "config" / "collector_config.json"

    if not config_file.exists() and not local_config.exists():
        print("[!] WARNING: No collector_config.json found. Collector will run with default/environment settings.")

    print(f"[*] Target Backend : {settings.BACKEND_URL}")
    print(f"[*] Collector ID   : {settings.COLLECTOR_ID}")
    print(f"[*] Device Name    : {settings.COLLECTOR_NAME}")
    print(f"[*] Hostname       : {settings.HOSTNAME}")
    print(f"[*] Collection Int : {settings.COLLECTION_INTERVAL_SECONDS}s")
    print(f"[*] Heartbeat Int  : {settings.HEARTBEAT_INTERVAL_SECONDS}s")

    if foreground:
        print("\n[*] Starting collector in FOREGROUND mode (Press Ctrl+C to stop)...")
        from collector.main import main as run_main
        sys.argv = [sys.argv[0], "--mode", "live"]
        run_main()
        return None

    # Background spawn
    print(f"[*] Spawning background collector process...")
    python_exe = sys.executable

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n--- Collector started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")

    creationflags = 0
    if sys.platform.startswith("win"):
        # CREATE_NO_WINDOW (0x08000000) + CREATE_NEW_PROCESS_GROUP (0x00000200)
        # provides clean detached execution without window popups or handle invalidation
        creationflags = 0x08000000 | subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(
        [python_exe, "-u", "-m", "collector.main", "--mode", "live", "--log-file", str(LOG_FILE)],
        cwd=str(project_dir),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags
    )

    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    time.sleep(1.5)

    if is_pid_running(proc.pid):
        print(f"[+] ObserVault Collector successfully started as background daemon (PID: {proc.pid}).")
        print(f"    Log output directed to: {LOG_FILE}")
        return proc.pid
    else:
        print("[!] ERROR: Collector process exited unexpectedly. Checking log output:")
        if LOG_FILE.exists():
            print(LOG_FILE.read_text(encoding="utf-8")[-500:])
        return None

def stop_daemon():
    """Stop the running collector process gracefully."""
    pid = get_running_pid()
    if not pid:
        print("[-] ObserVault Collector is NOT running.")
        PID_FILE.unlink(missing_ok=True)
        return True

    print(f"[*] Stopping collector process (PID: {pid})...")
    if sys.platform.startswith("win"):
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        except Exception as e:
            print(f"[!] Warning on taskkill: {e}")
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

    time.sleep(1.0)
    if is_pid_running(pid):
        print(f"[!] Force terminating PID {pid}...")
        try:
            if sys.platform.startswith("win"):
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
            else:
                os.kill(pid, signal.SIGKILL)
        except Exception:
            pass

    PID_FILE.unlink(missing_ok=True)
    print("[+] ObserVault Collector has been stopped.")
    return True

def status_daemon():
    """Display comprehensive health and runtime status of the collector."""
    pid = get_running_pid()
    settings.load() if hasattr(settings, "load") else None

    print("==========================================================")
    print("           ObserVault Collector Runtime Status            ")
    print("==========================================================")
    if pid:
        print(f"  Daemon State    : [RUNNING] (PID: {pid})")
    else:
        print("  Daemon State    : [STOPPED]")

    print(f"  Collector ID    : {settings.COLLECTOR_ID}")
    print(f"  Device Name     : {settings.COLLECTOR_NAME}")
    print(f"  Server ID       : {settings.SERVER_ID}")
    print(f"  Host Machine    : {settings.HOSTNAME}")
    print(f"  SaaS Backend    : {settings.BACKEND_URL}")
    print(f"  Heartbeat Freq  : Every {settings.HEARTBEAT_INTERVAL_SECONDS} seconds")
    print(f"  Telemetry Freq  : Every {settings.COLLECTION_INTERVAL_SECONDS} seconds")
    print(f"  Log File Path   : {LOG_FILE}")

    # SQLite Buffer Diagnostics
    try:
        buf = SQLiteBuffer(settings.BUFFER_DB_PATH)
        stats = buf.get_stats()
        print("----------------------------------------------------------")
        print(f"  SQLite Buffer   : {settings.BUFFER_DB_PATH}")
        print(f"    Pending Egress: {stats['pending']} record(s)")
        print(f"    Delivered     : {stats['delivered']} record(s)")
        print(f"    Failed Retries: {stats['failed']} record(s)")
    except Exception as e:
        print(f"  SQLite Buffer   : Error reading buffer: {e}")

    # Check SaaS connectivity
    print("----------------------------------------------------------")
    import urllib.request
    try:
        health_url = f"{settings.BACKEND_URL.rstrip('/')}/health"
        with urllib.request.urlopen(health_url, timeout=3) as resp:
            if resp.status == 200:
                print("  SaaS Connectivity: [CONNECTED] Backend is reachable.")
            else:
                print(f"  SaaS Connectivity: [DEGRADED] HTTP {resp.status}")
    except Exception as e:
        print(f"  SaaS Connectivity: [OFFLINE / UNREACHABLE] {e}")

    print("==========================================================")

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m collector.runtime {start|stop|restart|status|foreground}")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "start":
        start_daemon(foreground=False)
    elif cmd == "foreground":
        start_daemon(foreground=True)
    elif cmd == "stop":
        stop_daemon()
    elif cmd == "restart":
        stop_daemon()
        time.sleep(1)
        start_daemon(foreground=False)
    elif cmd == "status":
        status_daemon()
    else:
        print(f"Unknown command: {cmd}")
        print("Valid commands: start, stop, restart, status, foreground")
        sys.exit(1)

if __name__ == "__main__":
    main()
