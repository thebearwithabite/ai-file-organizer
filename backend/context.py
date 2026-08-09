"""
Grounded context layers (Dash pattern, SQLite-native).

Phase 2.2: Every classification decision is grounded in:
  1. Knowledge   — taxonomy definitions, category descriptions, naming rules
  2. Learnings   — error patterns: misclassification + correction + extracted rule
  3. Corrections — raw event log of every human correction

Populated on user corrections, queried during classification for context assembly.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.paths import get_metadata_root, ensure_safe_local_path

logger = logging.getLogger(__name__)


@dataclass
class CorrectionEvent:
    """Raw correction event (maps to corrections table)."""
    file_path: str
    predicted_category: str
    corrected_category: str
    confidence: float
    source: str = "unknown"  # "ui", "cli", "batch"
    timestamp: float = field(default_factory=time.time)
    notes: str = ""


class ContextStore:
    """
    Manages the grounded context tables in the metadata DB.

    Usage:
        store = ContextStore()
        store.record_correction(CorrectionEvent(...))
        context = store.assemble_context(file_content, top_k=5)
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            meta = ensure_safe_local_path(get_metadata_root())
            db_path = meta / "organizer.db"
        self.db_path = db_path
        self._init_tables()
        self._seed_knowledge()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_tables(self) -> None:
        """Create tables if they don't exist."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id TEXT NOT NULL,
                    display_name TEXT,
                    description TEXT,
                    examples TEXT,          -- JSON array of example filenames
                    naming_rules TEXT,      -- human-readable naming conventions
                    keywords TEXT,          -- JSON array of trigger words
                    parent_category TEXT,
                    created_at REAL DEFAULT (strftime('%s', 'now')),
                    updated_at REAL DEFAULT (strftime('%s', 'now'))
                );

                CREATE TABLE IF NOT EXISTS learnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT,
                    predicted_category TEXT NOT NULL,
                    corrected_category TEXT NOT NULL,
                    extracted_rule TEXT,     -- e.g. "invoices from Acme Corp are business"
                    confidence_before REAL,
                    file_type TEXT,
                    embedding_id TEXT,       -- chromadb embedding ID for similarity search
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                );

                CREATE TABLE IF NOT EXISTS corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    predicted_category TEXT NOT NULL,
                    corrected_category TEXT NOT NULL,
                    confidence_before REAL,
                    source TEXT DEFAULT 'unknown',
                    notes TEXT,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                );

                CREATE INDEX IF NOT EXISTS idx_learnings_predicted 
                    ON learnings(predicted_category);
                CREATE INDEX IF NOT EXISTS idx_learnings_corrected 
                    ON learnings(corrected_category);
                CREATE INDEX IF NOT EXISTS idx_knowledge_category 
                    ON knowledge(category_id);
                CREATE INDEX IF NOT EXISTS idx_corrections_file 
                    ON corrections(file_path);
            """)
            conn.commit()

        logger.info(f"Context tables initialized in {self.db_path}")

    # ------------------------------------------------------------------
    # Knowledge seeding
    # ------------------------------------------------------------------

    def _seed_knowledge(self) -> None:
        """Seed knowledge table from classification_rules.json if empty."""
        with sqlite3.connect(str(self.db_path)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
            if count > 0:
                return  # already seeded

        # Load from classification_rules.json
        rules_path = Path(__file__).parent.parent / "classification_rules.json"
        if not rules_path.exists():
            logger.warning(f"classification_rules.json not found at {rules_path}")
            return

        try:
            rules = json.loads(rules_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load classification_rules.json: {e}")
            return

        with sqlite3.connect(str(self.db_path)) as conn:
            for category_id, rule_data in rules.items():
                if isinstance(rule_data, dict):
                    conn.execute(
                        """INSERT INTO knowledge 
                           (category_id, display_name, description, keywords, examples)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            category_id,
                            rule_data.get("display_name", category_id),
                            rule_data.get("description", ""),
                            json.dumps(rule_data.get("keywords", [])),
                            json.dumps(rule_data.get("examples", [])),
                        ),
                    )
            conn.commit()

        logger.info(f"Seeded knowledge table with {len(rules)} categories")

    # ------------------------------------------------------------------
    # Write path: corrections -> learnings
    # ------------------------------------------------------------------

    def record_correction(self, event: CorrectionEvent) -> int:
        """
        Record a user correction. This writes to BOTH corrections (raw log)
        and learnings (generalized rule). Returns the correction row ID.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            # 1. Raw correction log
            cursor = conn.execute(
                """INSERT INTO corrections 
                   (file_path, predicted_category, corrected_category, 
                    confidence_before, source, notes, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.file_path,
                    event.predicted_category,
                    event.corrected_category,
                    event.confidence,
                    event.source,
                    event.notes,
                    event.timestamp,
                ),
            )
            correction_id = cursor.lastrowid

            # 2. Generalize into a learning rule
            rule = self._extract_rule(event)

            # Check if a similar learning already exists
            existing = conn.execute(
                """SELECT id FROM learnings 
                   WHERE predicted_category = ? AND corrected_category = ? 
                   AND extracted_rule = ?
                   LIMIT 1""",
                (event.predicted_category, event.corrected_category, rule),
            ).fetchone()

            if not existing:
                conn.execute(
                    """INSERT INTO learnings 
                       (file_path, predicted_category, corrected_category,
                        extracted_rule, confidence_before, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        event.file_path,
                        event.predicted_category,
                        event.corrected_category,
                        rule,
                        event.confidence,
                        event.timestamp,
                    ),
                )
                logger.info(
                    f"New learning: {event.predicted_category} -> "
                    f"{event.corrected_category} ({rule})"
                )
            else:
                logger.debug(f"Learning already exists for this pattern")

            conn.commit()

        return correction_id

    @staticmethod
    def _extract_rule(event: CorrectionEvent) -> str:
        """Generalize a correction into a reusable rule string."""
        fname = Path(event.file_path).stem.lower() if event.file_path else "unknown"
        return (
            f"files similar to '{fname}' are "
            f"'{event.corrected_category}', not '{event.predicted_category}'"
        )

    # ------------------------------------------------------------------
    # Read path: context assembly for classification
    # ------------------------------------------------------------------

    def assemble_context(
        self,
        filename: str,
        content_snippet: str = "",
        top_k: int = 5,
    ) -> dict:
        """
        Assemble grounded context for a classification decision.

        Returns a dict with:
          - knowledge: relevant taxonomy entries
          - learnings: top-k similar correction patterns
          - corrections_count: total corrections for this file
        """
        context = {
            "knowledge": [],
            "learnings": [],
            "corrections_count": 0,
        }

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # 1. All knowledge (taxonomy is small enough to load fully)
            knowledge_rows = conn.execute(
                "SELECT category_id, display_name, description, keywords FROM knowledge"
            ).fetchall()
            context["knowledge"] = [dict(r) for r in knowledge_rows]

            # 2. Learnings — most recent corrections first (simple approach; 
            #    embedding-based retrieval added when chromadb is wired)
            fname_lower = filename.lower() if filename else ""

            # Try exact file match first
            learnings_rows = conn.execute(
                """SELECT predicted_category, corrected_category, extracted_rule, 
                          confidence_before, created_at
                   FROM learnings
                   WHERE file_path LIKE ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (f"%{fname_lower}%", top_k),
            ).fetchall()

            # If no exact match, get recent learnings for common corrections
            if not learnings_rows:
                learnings_rows = conn.execute(
                    """SELECT predicted_category, corrected_category, extracted_rule,
                              confidence_before, created_at
                       FROM learnings
                       ORDER BY created_at DESC
                       LIMIT ?""",
                    (top_k,),
                ).fetchall()

            context["learnings"] = [dict(r) for r in learnings_rows]

            # 3. Correction count for this file
            context["corrections_count"] = conn.execute(
                "SELECT COUNT(*) FROM corrections WHERE file_path = ?",
                (fname_lower,),
            ).fetchone()[0]

        return context

    def get_learnings_for_category(self, category: str, limit: int = 10) -> list[dict]:
        """Get learnings where files were corrected TO this category."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT predicted_category, extracted_rule, created_at
                   FROM learnings
                   WHERE corrected_category = ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (category, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_recent_corrections(self, limit: int = 20) -> list[dict]:
        """Get the most recent corrections for review."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT file_path, predicted_category, corrected_category,
                          confidence_before, source, created_at
                   FROM corrections
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
