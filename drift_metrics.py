#!/usr/bin/env python3
"""
Drift Metrics Monitor
Tracks the health of the Librarian's decisions.
Focuses on: "Are we failing to classify?"
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from gdrive_integration import get_metadata_root

logger = logging.getLogger(__name__)

class DriftMonitor:
    def __init__(self):
        self.metrics_file = get_metadata_root() / "librarian_metrics.json"
        
    def log_decision(self, decision): # Type hinted as PolicyDecision, but using duck typing to avoid circular import if needed
        """
        Log a decision to track drift.
        Drift = High % of "Uncertain" or "Fallback" decisions.
        """
        try:
            metrics = self._load_metrics()
            
            today = datetime.now().strftime("%Y-%m-%d")
            if today not in metrics:
                metrics[today] = {"total": 0, "unsorted": 0, "fallback_stub": 0}
            
            metrics[today]["total"] += 1
            
            # Check for drift indicators
            if "Uncertain" in str(decision.target_path) or decision.action == "review":
                metrics[today]["unsorted"] += 1
            
            # Check for generic fallback stub (simple heuristic)
            if "Document" in decision.suggested_filename and decision.category_id == "unknown":
                 metrics[today]["fallback_stub"] += 1
                 
            self._save_metrics(metrics)
            
        except Exception as e:
            logger.warning(f"Failed to log drift metrics: {e}")

    def _load_metrics(self) -> Dict:
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_metrics(self, metrics: Dict):
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
        except:
            pass
