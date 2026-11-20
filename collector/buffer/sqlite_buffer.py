# collector/buffer/sqlite_buffer.py
import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

class SQLiteBuffer:
    """
    Tier 1 Offline Buffer:
    Persists approved outbound records locally in an SQLite database.
    Guarantees zero data loss during network outages and enables resilient retries
    with deduplication keys.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS buffered_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT DEFAULT 'pending', -- pending, delivered, failed
                    attempts INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON buffered_events(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_event_id ON buffered_events(event_id);")
            conn.commit()

    def enqueue(self, event_id: str, record_dict: Dict[str, Any]) -> bool:
        """
        Stores an approved outbound record in local buffer.
        """
        payload_str = json.dumps(record_dict)
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO buffered_events (event_id, payload_json, status, created_at)
                    VALUES (?, ?, 'pending', ?);
                """, (event_id, payload_str, datetime.now(timezone.utc).isoformat()))
                conn.commit()
            return True
        except Exception as e:
            print(f"[Buffer Error] Failed to enqueue event {event_id}: {e}")
            return False

    def get_pending(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves pending records awaiting transmission.
        """
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT id, event_id, payload_json, attempts
                FROM buffered_events
                WHERE status = 'pending'
                ORDER BY id ASC
                LIMIT ?;
            """, (limit,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                try:
                    payload = json.loads(r["payload_json"])
                    results.append({
                        "db_id": r["id"],
                        "event_id": r["event_id"],
                        "payload": payload,
                        "attempts": r["attempts"]
                    })
                except Exception:
                    continue
            return results

    def mark_delivered(self, event_ids: List[str]):
        """
        Marks records successfully acknowledged by SaaS backend.
        """
        if not event_ids:
            return
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            placeholders = ",".join("?" for _ in event_ids)
            conn.execute(f"""
                UPDATE buffered_events
                SET status = 'delivered', sent_at = ?
                WHERE event_id IN ({placeholders});
            """, [now_iso] + event_ids)
            conn.commit()

    def mark_failed(self, event_ids: List[str], error_msg: str):
        """
        Increments attempts and marks temporary failure.
        """
        if not event_ids:
            return
        with self._get_conn() as conn:
            placeholders = ",".join("?" for _ in event_ids)
            conn.execute(f"""
                UPDATE buffered_events
                SET attempts = attempts + 1, error_message = ?
                WHERE event_id IN ({placeholders});
            """, [error_msg] + event_ids)
            conn.commit()

    def get_stats(self) -> Dict[str, int]:
        """
        Returns buffer health metrics.
        """
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as delivered,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM buffered_events;
            """)
            row = cursor.fetchone()
            return {
                "total": row["total"] or 0,
                "pending": row["pending"] or 0,
                "delivered": row["delivered"] or 0,
                "failed": row["failed"] or 0
            }
