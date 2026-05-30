"""
cache_manager.py
SQLite를 사용해 처리된 영상 요약을 로컬에 저장합니다.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "cache" / "summaries.db"


class CacheManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS summaries (
                    video_id     TEXT PRIMARY KEY,
                    title        TEXT,
                    published_at TEXT,
                    url          TEXT,
                    cast_info    TEXT,
                    summary      TEXT,
                    description  TEXT,
                    cached_at    DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def exists(self, video_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM summaries WHERE video_id = ?", (video_id,)
            ).fetchone()
        return row is not None

    def get(self, video_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT video_id, title, published_at, url, cast_info, summary, description "
                "FROM summaries WHERE video_id = ?",
                (video_id,),
            ).fetchone()
        if not row:
            return None
        keys = ["video_id", "title", "published_at", "url", "cast", "summary", "description"]
        return dict(zip(keys, row))

    def save(self, data: dict):
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO summaries
                    (video_id, title, published_at, url, cast_info, summary, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("video_id"),
                data.get("title"),
                data.get("published_at"),
                data.get("url"),
                data.get("cast"),
                data.get("summary"),
                data.get("description", ""),
            ))
            conn.commit()

    def get_all(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT video_id, title, published_at, url, cast_info, summary, description "
                "FROM summaries ORDER BY published_at DESC"
            ).fetchall()
        keys = ["video_id", "title", "published_at", "url", "cast", "summary", "description"]
        return [dict(zip(keys, row)) for row in rows]

    def get_all_ids(self) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute("SELECT video_id FROM summaries").fetchall()
        return [r[0] for r in rows]

    def clear(self):
        with self._conn() as conn:
            conn.execute("DELETE FROM summaries")
            conn.commit()
