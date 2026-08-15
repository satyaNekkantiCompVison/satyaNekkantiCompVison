from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any


class EventStore:
    def __init__(self, sqlite_path: str, maxlen: int = 2000) -> None:
        self.path = Path(sqlite_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.recent: deque[dict[str, Any]] = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    camera_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_cam ON events(camera_id)")

    def add(self, event: dict[str, Any]) -> dict[str, Any]:
        event = dict(event)
        event.setdefault("ts", time.time())
        with self._lock:
            self.recent.appendleft(event)
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO events (ts, camera_id, type, payload) VALUES (?, ?, ?, ?)",
                    (
                        event["ts"],
                        event.get("camera_id", ""),
                        event.get("type", "unknown"),
                        json.dumps(event),
                    ),
                )
        return event

    def list_events(
        self,
        camera_id: str | None = None,
        type_: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        query = "SELECT payload FROM events WHERE 1=1"
        params: list[Any] = []
        if camera_id:
            query += " AND camera_id = ?"
            params.append(camera_id)
        if type_:
            query += " AND type = ?"
            params.append(type_)
        query += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [json.loads(r["payload"]) for r in rows]
