"""
Phase 3b · Test Suite · Batch Reverse Prompt Processor
"""

import json, tempfile
from pathlib import Path
from batch_reverse_prompt import discover_videos, run_batch

def test_discover_videos(tmp_path: Path):
    # Create fake videos
    for ext in [".mp4", ".mov", ".txt"]:
        (tmp_path / f"clip{ext}").write_text("dummy")
    vids = discover_videos(str(tmp_path))
    assert all(v.suffix in [".mp4", ".mov"] for v in vids)
    assert len(vids) == 2

def test_run_batch_minimal(monkeypatch, tmp_path: Path):
    """Smoke test using a stubbed VEOPromptGenerator"""
    dummy_json = {"shot_id": "auto_shot_test", "scene": {"duration_s": 8}, "confidence_score": 0.9}

    # Create a mock VEOPromptGenerator
    class MockGenerator:
        def generate_reverse_veo_json(self, path):
            return dummy_json

    monkeypatch.setattr("batch_reverse_prompt.discover_videos",
                        lambda path: [tmp_path / "dummy.mp4"])
    monkeypatch.setattr("batch_reverse_prompt.get_veo_generator",
                        lambda: MockGenerator())
    monkeypatch.setattr("batch_reverse_prompt.analyze_continuity",
                        lambda results: [])
    monkeypatch.setattr("batch_reverse_prompt.build_manifest",
                        lambda results, cont: {"project": "unit_test", "clips": results})

    manifest = run_batch(str(tmp_path), workers=1)
    assert "project" in manifest
    assert manifest["project"] == "unit_test"
