"""SQLite storage for deduplication history."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class Storage:
    """Persists seen job posting hashes in SQLite so we only notify new ones."""

    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS seen_postings (
        hash TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        title TEXT,
        source_site TEXT,
        first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(self.CREATE_TABLE_SQL)
        self._conn.commit()

    def has_seen(self, hash_value: str) -> bool:
        """Return True if this posting hash was already seen."""
        row = self._conn.execute(
            "SELECT 1 FROM seen_postings WHERE hash = ?", (hash_value,)
        ).fetchone()
        return row is not None

    def mark_seen(
        self,
        hash_value: str,
        url: str,
        title: Optional[str] = None,
        source_site: Optional[str] = None,
    ) -> None:
        """Record that we've seen a posting."""
        try:
            self._conn.execute(
                "INSERT OR IGNORE INTO seen_postings (hash, url, title, source_site) "
                "VALUES (?, ?, ?, ?)",
                (hash_value, url, title, source_site),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            logger.error("Failed to mark posting as seen: %s", exc)

    def mark_seen_bulk(self, entries: List[dict]) -> None:
        """Bulk-insert seen posting entries."""
        try:
            self._conn.executemany(
                "INSERT OR IGNORE INTO seen_postings (hash, url, title, source_site) "
                "VALUES (:hash, :url, :title, :source_site)",
                entries,
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            logger.error("Bulk mark seen failed: %s", exc)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
