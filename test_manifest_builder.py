"""
Phase 3b · Test Suite · Manifest Builder
"""

from manifest_builder import build_manifest, save_manifest
from pathlib import Path
import json, tempfile

def test_build_manifest_composition(tmp_path: Path):
    results = [
        {"path": str(tmp_path / "a.mp4"),
         "veo_json": {"shot_id": "shotA", "scene": {"duration_s": 8}},
         "confidence": 0.9},
        {"path": str(tmp_path / "b.mp4"),
         "veo_json": {"shot_id": "shotB", "scene": {"duration_s": 8}},
         "confidence": 0.8},
    ]
    continuity = [{"pair": ["shotA", "shotB"], "continuity_score": 0.75}]
    manifest = build_manifest(results, continuity)
    assert "summary" in manifest
    assert manifest["summary"]["total_clips"] == 2

def test_save_manifest(tmp_path: Path):
    manifest = {"project": "unit_test", "clips": [], "continuity": [], "summary": {}}
    out = save_manifest(manifest, str(tmp_path))
    assert Path(out).exists()
    data = json.loads(Path(out).read_text())
    assert data["project"] == "unit_test"
