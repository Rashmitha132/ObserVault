# backend/app/run.py
import sys
from pathlib import Path
import uvicorn

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.seed import seed_database

if __name__ == "__main__":
    # Ensure database is seeded with demo organizations
    seed_database()
    print("Starting ObserVault SaaS Backend on http://127.0.0.1:8000 ...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
