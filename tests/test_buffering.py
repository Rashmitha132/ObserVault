# tests/test_buffering.py
import pytest
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collector.buffer.sqlite_buffer import SQLiteBuffer

def test_sqlite_buffer_lifecycle():
    # Use dedicated test db in test directory
    db_path = str(Path(__file__).parent / f"test_buffer_{uuid.uuid4().hex[:8]}.db")

    try:
        buffer = SQLiteBuffer(db_path)
        stats = buffer.get_stats()
        assert stats["total"] == 0

        # 1. Enqueue 3 records
        buffer.enqueue("evt-001", {"event_id": "evt-001", "cpu": 50})
        buffer.enqueue("evt-002", {"event_id": "evt-002", "cpu": 75})
        buffer.enqueue("evt-003", {"event_id": "evt-003", "cpu": 95})

        stats = buffer.get_stats()
        assert stats["total"] == 3
        assert stats["pending"] == 3
        assert stats["delivered"] == 0

        # 2. Test duplicate prevention
        buffer.enqueue("evt-001", {"event_id": "evt-001", "cpu": 50})
        stats = buffer.get_stats()
        assert stats["total"] == 3, "Duplicate record was not prevented!"

        # 3. Retrieve pending
        pending = buffer.get_pending(limit=2)
        assert len(pending) == 2
        assert pending[0]["event_id"] == "evt-001"
        assert pending[1]["event_id"] == "evt-002"

        # 4. Mark delivered
        buffer.mark_delivered(["evt-001", "evt-002"])
        stats = buffer.get_stats()
        assert stats["delivered"] == 2
        assert stats["pending"] == 1

        # 5. Remaining pending
        remaining = buffer.get_pending(limit=10)
        assert len(remaining) == 1
        assert remaining[0]["event_id"] == "evt-003"

    finally:
        import gc
        gc.collect()
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass
