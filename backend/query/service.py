"""
Read-only NL query service over the metadata DB (Phase 2.3).

Enforces read-only at the connection level — not the prompt level.
Powers UI queries like "PDFs about LoRA training from March" and
"what did you move yesterday and why."
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.paths import get_metadata_root, ensure_safe_local_path

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result row from a query."""
    columns: list[str]
    rows: list[dict]
    row_count: int
    query_time_ms: float
    sql: str
    explanation: str = ""


class QueryService:
    """
    Read-only query interface over the metadata DB.

    Key security property: the connection is opened with mode=ro (read-only).
    Even if an injected SQL statement reaches the connection layer, it is
    rejected at the SQLite level — not the prompt level.
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            meta = ensure_safe_local_path(get_metadata_root())
            db_path = meta / "organizer.db"
        self.db_path = db_path
        self._schema_cache: Optional[dict] = None

    # ------------------------------------------------------------------
    # Schema discovery
    # ------------------------------------------------------------------

    @property
    def schema(self) -> dict:
        """Lazy-load the DB schema for LLM context."""
        if self._schema_cache is None:
            self._schema_cache = self._discover_schema()
        return self._schema_cache

    def _discover_schema(self) -> dict:
        """Discover table schemas from the DB."""
        tables = {}
        try:
            # Open read-write temporarily just for schema discovery
            with sqlite3.connect(str(self.db_path)) as conn:
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
                for (name,) in rows:
                    cols = conn.execute(f"PRAGMA table_info({name})").fetchall()
                    tables[name] = [
                        {"name": c[1], "type": c[2], "nullable": not c[3]}
                        for c in cols
                    ]
        except Exception as e:
            logger.warning(f"Schema discovery failed: {e}")

        return tables

    # ------------------------------------------------------------------
    # Query execution (READ-ONLY)
    # ------------------------------------------------------------------

    def query(self, sql: str, params: tuple = ()) -> QueryResult:
        """
        Execute a read-only SQL query.

        The connection is opened with uri=True and mode=ro query parameter,
        enforcing read-only at the SQLite level.
        """
        start = time.time()

        db_uri = f"file:{self.db_path}?mode=ro"

        try:
            conn = sqlite3.connect(db_uri, uri=True)
            conn.row_factory = sqlite3.Row

            try:
                cursor = conn.execute(sql, params)
            except sqlite3.OperationalError:
                conn.close()
                return QueryResult(columns=[], rows=[], row_count=0, query_time_ms=0, sql=sql)

            rows = [dict(r) for r in cursor.fetchall()]
            columns = [d[0] for d in cursor.description] if cursor.description else []
            conn.close()
        except sqlite3.OperationalError as e:
            if "readonly" in str(e).lower():
                raise PermissionError(f"Write operation rejected: {e}")
            raise

        elapsed = (time.time() - start) * 1000

        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            query_time_ms=round(elapsed, 2),
            sql=sql,
        )
    def search_files(
        self,
        query_text: str = "",
        category: str = "",
        file_type: str = "",
        date_from: str = "",
        date_to: str = "",
        tier: str = "",
        limit: int = 50,
    ) -> QueryResult:
        """Parameterized file search — no string interpolation of user input."""
        conditions = []
        params = []

        if query_text:
            conditions.append("(f.name LIKE ? OR f.ai_category LIKE ?)")
            params.extend([f"%{query_text}%", f"%{query_text}%"])

        if category:
            conditions.append("f.ai_category = ?")
            params.append(category)

        if file_type:
            conditions.append("f.file_type = ?")
            params.append(file_type)

        if date_from:
            conditions.append("f.created_at >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("f.created_at <= ?")
            params.append(date_to)

        where = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
            SELECT f.name, f.ai_category, f.confidence_score, f.file_type,
                   f.file_size, f.created_at, f.gcs_key
            FROM file_metadata f
            WHERE {where}
            ORDER BY f.created_at DESC
            LIMIT ?
        """
        params.append(limit)

        result = self.query(sql, tuple(params))
        result.explanation = (
            f"Searching files" +
            (f" matching '{query_text}'" if query_text else "") +
            (f" in category '{category}'" if category else "") +
            (f" of type '{file_type}'" if file_type else "")
        )
        return result

    def get_recent_activity(self, limit: int = 20) -> QueryResult:
        """Get recent classification activity with decisions."""
        return self.query(
            """SELECT c.file_path, c.predicted_category, c.corrected_category,
                      c.confidence_before, c.source, datetime(c.created_at, 'unixepoch') as when_
               FROM corrections c
               ORDER BY c.created_at DESC
               LIMIT ?""",
            (limit,),
        )

    def get_category_stats(self) -> QueryResult:
        """Get file counts by category."""
        return self.query(
            """SELECT ai_category, COUNT(*) as file_count,
                      AVG(confidence_score) as avg_confidence
               FROM file_metadata
               WHERE ai_category IS NOT NULL
               GROUP BY ai_category
               ORDER BY file_count DESC"""
        )

    def get_learnings_summary(self) -> QueryResult:
        """Get the most common correction patterns."""
        return self.query(
            """SELECT predicted_category, corrected_category, COUNT(*) as count
               FROM learnings
               GROUP BY predicted_category, corrected_category
               ORDER BY count DESC
               LIMIT 20"""
        )
