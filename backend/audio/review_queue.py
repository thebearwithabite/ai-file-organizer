"""
Review Queue Service — daily surfacing cap + batch grouping.

The system waits; it never floods. Calm is a design constraint.
"""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

from core.paths import get_metadata_root

DEFAULT_DAILY_CAP = 20


def ensure_review_table(db_path: Path | None = None) -> None:
    """Create review_queue table if it doesn't exist."""
    if db_path is None:
        db_path = get_metadata_root() / "organizer.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS review_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                reason TEXT NOT NULL,
                category_hint TEXT,
                surfaced_on TEXT,          -- date string (YYYY-MM-DD) or NULL if not surfaced
                batch_group TEXT,          -- e.g. "sub3s-speech", "anomaly", "disagreement"
                status TEXT DEFAULT 'pending',  -- pending | reviewed | dismissed
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(file_path, reason)
            )
        """)
        conn.commit()


class ReviewQueue:
    """Review queue with daily surfacing cap. Overflow queues silently."""

    def __init__(self, db_path: Path | None = None, daily_cap: int = DEFAULT_DAILY_CAP):
        if db_path is None:
            db_path = get_metadata_root() / "organizer.db"
        self.db_path = db_path
        self.daily_cap = daily_cap
        ensure_review_table(db_path)

    # ------------------------------------------------------------------
    # Enqueue
    # ------------------------------------------------------------------

    def enqueue(
        self,
        file_path: str,
        reason: str,
        category_hint: str = "",
        batch_group: str = "general",
    ) -> bool:
        """
        Add an item to the review queue.
        Returns True if it was surfaced (within cap), False if queued silently.
        """
        today = date.today().isoformat()

        with sqlite3.connect(str(self.db_path)) as conn:
            # Dedupe: same file+reason already queued → don't re-add
            existing = conn.execute(
                "SELECT id FROM review_queue WHERE file_path = ? AND reason = ?",
                (file_path, reason),
            ).fetchone()
            if existing:
                return False

            conn.execute(
                """INSERT INTO review_queue (file_path, reason, category_hint, surfaced_on, batch_group)
                   VALUES (?, ?, ?, NULL, ?)""",
                (file_path, reason, category_hint, batch_group),
            )

            # Count how many already surfaced today
            surfaced_today = conn.execute(
                "SELECT COUNT(*) FROM review_queue WHERE surfaced_on = ?",
                (today,),
            ).fetchone()[0]

            # Surface if under cap, else leave silent (overflow)
            if surfaced_today < self.daily_cap:
                conn.execute(
                    "UPDATE review_queue SET surfaced_on = ? WHERE file_path = ? AND reason = ?",
                    (today, file_path, reason),
                )
                conn.commit()
                return True
            else:
                conn.commit()
                return False

    # ------------------------------------------------------------------
    # Surfacing
    # ------------------------------------------------------------------

    def surface(self, limit: int | None = None) -> list[dict]:
        """
        Get items to show the user today: surfaced items first,
        batch-grouped by type. Overflow stays silent until cap resets.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            query = """
                SELECT * FROM review_queue
                WHERE surfaced_on = ?
                ORDER BY batch_group, created_at
            """
            if limit:
                query += f" LIMIT {limit}"
            rows = conn.execute(query, (date.today().isoformat(),)).fetchall()
            return [dict(r) for r in rows]

    def surface_grouped(self) -> dict[str, list[dict]]:
        """Surface items grouped by batch_group."""
        items = self.surface()
        grouped: dict[str, list[dict]] = {}
        for item in items:
            grouped.setdefault(item["batch_group"], []).append(item)
        return grouped

    # ------------------------------------------------------------------
    # Stats / maintenance
    # ------------------------------------------------------------------

    def pending_count(self) -> int:
        """Total pending items (surfaced + silent overflow)."""
        with sqlite3.connect(str(self.db_path)) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM review_queue WHERE status = 'pending'"
            ).fetchone()[0]

    def overflow_count(self) -> int:
        """Items queued but never surfaced (over the cap)."""
        with sqlite3.connect(str(self.db_path)) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM review_queue WHERE surfaced_on IS NULL AND status = 'pending'"
            ).fetchone()[0]

    def mark_reviewed(self, file_path: str, reason: str = "") -> None:
        """Mark an item as reviewed."""
        with sqlite3.connect(str(self.db_path)) as conn:
            if reason:
                conn.execute(
                    "UPDATE review_queue SET status = 'reviewed' WHERE file_path = ? AND reason = ?",
                    (file_path, reason),
                )
            else:
                conn.execute(
                    "UPDATE review_queue SET status = 'reviewed' WHERE file_path = ?",
                    (file_path,),
                )
            conn.commit()

    def reset_daily(self) -> None:
        """Reset surfaced_on for a new day (simulates day rollover in tests)."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("UPDATE review_queue SET surfaced_on = NULL")
            conn.commit()
