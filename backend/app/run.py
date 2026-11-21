# backend/app/run.py
import os
import sys
from pathlib import Path
import uvicorn

# Ensure backend root and repo root are on sys.path
backend_dir = Path(__file__).resolve().parent.parent
repo_root = backend_dir.parent
for p in [str(backend_dir), str(repo_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.seed import seed_database

if __name__ == "__main__":
    # Ensure database is seeded with demo organizations
    try:
        seed_database()
    except Exception as e:
        print(f"[Startup Seed Notice]: {e}")

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting ObserVault SaaS Backend on http://{host}:{port} ...")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
