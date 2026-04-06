"""
SQLite-backed storage for tracking:
  - Articles already notified (deduplication)
  - Notification history / audit log
"""

import sqlite3
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "dameko.db"


def _get_conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    """Create tables if they don't exist."""
    with _get_conn(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS seen_articles (
                url_hash    TEXT PRIMARY KEY,
                url         TEXT NOT NULL,
                title       TEXT,
                category    TEXT,
                notified_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                url_hash        TEXT NOT NULL,
                article_title   TEXT,
                markets_found   INTEGER DEFAULT 0,
                sent_at         TEXT NOT NULL,
                success         INTEGER DEFAULT 1
            );

            CREATE INDEX IF NOT EXISTS idx_seen_notified
                ON seen_articles(notified_at);
        """)
    logger.info(f"Database initialised at {db_path}")


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


class ArticleStore:
    """Manages deduplication of processed articles."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        init_db(db_path)

    def is_seen(self, url: str) -> bool:
        """Return True if this URL has already been processed."""
        url_hash = _hash_url(url)
        with _get_conn(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM seen_articles WHERE url_hash = ?", (url_hash,)
            ).fetchone()
        return row is not None

    def mark_seen(
        self,
        url: str,
        title: str = "",
        category: str = "",
    ) -> None:
        """Record this article as processed."""
        url_hash = _hash_url(url)
        now = datetime.now(timezone.utc).isoformat()
        with _get_conn(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO seen_articles (url_hash, url, title, category, notified_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (url_hash, url, title, category, now),
            )

    def log_notification(
        self,
        url: str,
        article_title: str,
        markets_found: int,
        success: bool,
    ) -> None:
        """Log a notification attempt."""
        url_hash = _hash_url(url)
        now = datetime.now(timezone.utc).isoformat()
        with _get_conn(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO notifications (url_hash, article_title, markets_found, sent_at, success)
                VALUES (?, ?, ?, ?, ?)
                """,
                (url_hash, article_title, markets_found, now, int(success)),
            )

    def cleanup_old_records(self, days: int = 7) -> int:
        """Remove records older than `days` days. Returns count deleted."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with _get_conn(self.db_path) as conn:
            cur = conn.execute(
                "DELETE FROM seen_articles WHERE notified_at < ?", (cutoff,)
            )
            deleted = cur.rowcount
        if deleted:
            logger.info(f"Cleaned up {deleted} old article records")
        return deleted

    def stats(self) -> dict:
        """Return basic stats about the store."""
        with _get_conn(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM seen_articles").fetchone()[0]
            notifications = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
            success = conn.execute(
                "SELECT COUNT(*) FROM notifications WHERE success = 1"
            ).fetchone()[0]
        return {
            "articles_seen": total,
            "notifications_sent": notifications,
            "notifications_success": success,
        }
