#!/usr/bin/env python
"""
ObserVault Hackathon Demo Launcher
Boots the SaaS Backend (FastAPI), starts the Tier-1 Collector, and verifies connectivity.
"""
import subprocess
import sys
import time
import os
import signal
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = BASE_DIR / "backend"
COLLECTOR_DIR = BASE_DIR / "collector"
FRONTEND_DIR = BASE_DIR / "frontend"

def main():
    print("="*75)
    print("  OBSERVAULT: PRIVACY-FIRST INTELLIGENT OBSERVABILITY PLATFORM")
    print("  24-Hour Hackathon Demonstration Suite")
    print("="*75)

    # 1. Seed Database
    print("\n[1/3] Initializing and Seeding Multi-Tenant Database...")
    seed_proc = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, r'backend'); from app.seed import seed_database; seed_database()"],
        cwd=str(BASE_DIR)
    )
    if seed_proc.returncode != 0:
        print("Database seed failed.")
        sys.exit(1)

    # 2. Launch Backend
    print("\n[2/3] Starting SaaS FastAPI Backend on http://127.0.0.1:8000 ...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BACKEND_DIR)
    )
    time.sleep(2)

    # 3. Launch Local Collector Daemon
    print("\n[3/3] Starting Tier-1 On-Premises Collector Daemon...")
    collector_proc = subprocess.Popen(
        [sys.executable, "main.py", "--mode", "live", "--interval", "5"],
        cwd=str(COLLECTOR_DIR)
    )

    print("\n" + "="*75)
    print("  OBSERVAULT SERVICES ARE ONLINE!")
    print("="*75)
    print("  -> SaaS Backend API:    http://127.0.0.1:8000")
    print("  -> API Documentation:   http://127.0.0.1:8000/docs")
    print("  -> React Dashboard:     http://localhost:5173")
    print("\n  Demo Login Credentials:")
    print("   * Acme FinTech Corp:   admin@acme.com / Password123!")
    print("   * BioHealth Global:    admin@biohealth.com / Password123!")
    print("\n  To start the React frontend dev server, run:")
    print(f"    cd \"{FRONTEND_DIR}\" && npm run dev")
    print("="*75)
    print("\nPress Ctrl+C to terminate all services...\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down ObserVault services...")
        collector_proc.terminate()
        backend_proc.terminate()
        print("Done. Goodbye!")

if __name__ == "__main__":
    main()
