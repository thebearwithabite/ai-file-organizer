"""
UnifiedLibrarian — V2 shim for backward compatibility with api/services.py.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from backend.file_operations import get_file_operations
from backend.query import QueryService
from backend.context import ContextStore
from core.paths import get_ai_organizer_root, get_metadata_root

logger = logging.getLogger(__name__)


class CloudFacade:
    """Shim for librarian.cloud.hybrid_librarian.search()."""
    def __init__(self):
        self.hybrid_librarian = self

    def search(self, query: str, search_mode: str = "auto", limit: int = 50) -> list:
        qs = QueryService()
        result = qs.search_files(query_text=query, limit=limit)
        return result.rows


class UnifiedLibrarian:
    """V2 shim — wraps V2 components behind the pre-V2 interface."""
    _instance: Optional["UnifiedLibrarian"] = None

    def __init__(self):
        self.cloud = CloudFacade()
        self.file_ops = get_file_operations()
        self.metadata_root = get_metadata_root()
        self.organizer_root = get_ai_organizer_root()
        self.context_store = ContextStore()
        self._classifier = None

    @classmethod
    def get_instance(cls) -> "UnifiedLibrarian":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def classifier(self):
        if self._classifier is None:
            from unified_classifier import UnifiedClassificationService
            self._classifier = UnifiedClassificationService()
        return self._classifier

    def get_organized_files(self, category: Optional[str] = None) -> list:
        return self.file_ops.list_organized_files(category)

    def get_staging_files(self) -> list:
        return self.file_ops.list_staging_files()

    def move_to_organized(self, source: Path, category: str) -> Path:
        return self.file_ops.move_to_organized(source, category)

    def record_correction(self, file_path: str, predicted: str, corrected: str, confidence: float = 0.0, source: str = "api"):
        from backend.context import CorrectionEvent
        event = CorrectionEvent(
            file_path=file_path,
            predicted_category=predicted,
            corrected_category=corrected,
            confidence=confidence,
            source=source,
        )
        return self.context_store.record_correction(event)
