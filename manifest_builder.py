"""
Phase 3b · Manifest Builder
---------------------------
Aggregates VEO JSONs + continuity results into a unified
project-level manifest (iJSON index).
"""

from __future__ import annotations
from typing import List, Dict, Any
import logging, statistics, json
from pathlib import Path

logger = logging.getLogger(__name__)


def build_manifest(results: List[Dict[str, Any]],
                   continuity: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Construct a batch-level manifest structure."""
    valid = [r for r in results if "veo_json" in r]
    avg_conf = statistics.mean([r["confidence"] for r in valid]) if valid else 0.0
    avg_cont = statistics.mean([c["continuity_score"] for c in continuity]) if continuity else 0.0

    manifest = {
        "project": Path(results[0]["path"]).parent.name if results else "untitled_project",
        "clips": [
            {
                "shot_id": r["veo_json"]["shot_id"],
                "duration_s": r["veo_json"]["scene"]["duration_s"],
                "confidence": r.get("confidence", 0.0)
            }
            for r in valid
        ],
        "continuity": continuity,
        "summary": {
            "avg_confidence": round(avg_conf, 3),
            "avg_continuity": round(avg_cont, 3),
            "total_clips": len(valid),
        },
    }
    logger.info(f"Manifest built for {len(valid)} clips (avg conf {avg_conf:.2f})")
    return manifest


def save_manifest(manifest: Dict[str, Any], output_dir: str) -> str:
    """Save manifest JSON to disk."""
    path = Path(output_dir) / f"{manifest['project']}_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Manifest saved to {path}")
    return str(path)
