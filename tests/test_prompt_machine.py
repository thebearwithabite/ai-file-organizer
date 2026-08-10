"""Prompt Machine tests (PROMPT-MACHINE-DIRECTIVE v1.2, Phase 1).

Three layers:
  1. schema unit tests — ShotSpec validation incl. the expression_cues
     no-emotion-labels lock (no LLM needed, runs anywhere)
  2. knowledge seed test — the three seeds land in the knowledge table
  3. golden integration test — 2-page golden script → validated ShotSpec[]
     with no cloud keys present (Checkpoint 1 gate). Requires a local
     provider: vLLM (localhost:8000) or Ollama (gemma4:12b).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from backend.services.knowledge_seeds import (
    SEEDS,
    seed_prompt_machine_knowledge,
)
from backend.services.shot_spec import (
    EMOTION_LABELS,
    AssetBinding,
    AudioSpec,
    CameraSpec,
    CharacterSpec,
    GenerationSpec,
    SceneSpec,
    ShotSpec,
)

GOLDEN = Path(__file__).parent / "golden" / "golden_script.md"

SEED_IDS = {"FILMMAKING_PRINCIPLES", "LTX23_PROMPT_GUIDE", "ENGINE_ROUTING"}


# ---------------------------------------------------------------------------
# 1. Schema unit tests
# ---------------------------------------------------------------------------


def _valid_shot(
    shot_id: str = "sc01_sh01",
    character: CharacterSpec | None = None,
    assets: list[AssetBinding] | None = None,
    **overrides,
) -> ShotSpec:
    """Build a valid ShotSpec through the constructor (validators run)."""
    payload = dict(
        shot_id=shot_id,
        sequence_index=0,
        scene=SceneSpec(
            context="Maya enters the kitchen and finds the letter.",
            visual_style="naturalistic",
            lighting="soft morning window light from the left",
            mood="quiet, suspended",
            duration_s=6.0,
            aspect_ratio="16:9",
        ),
        character=character
        or CharacterSpec(
            name="Maya",
            gender_age="woman, mid-30s",
            physical_description="dark hair, grey knit sweater",
            behavior="walks slowly, stops at the counter",
            expression_cues="eyebrows draw together, fingers still on the envelope",
        ),
        camera=CameraSpec(shot_call="Eye-Level Medium Close-Up", movement="slow push-in"),
        audio=AudioSpec(dialogue='"When did this get here?"'),
        assets=assets or [AssetBinding(asset_id="char_maya", type="character", weight=0.9)],
        generation=GenerationSpec(),
    )
    payload.update(overrides)
    return ShotSpec(**payload)


def test_valid_shot_passes():
    shot = _valid_shot()
    assert shot.shot_id == "sc01_sh01"
    assert shot.status.value == "draft"
    assert shot.sequence_index == 0


@pytest.mark.parametrize("bad_id", ["shot1", "SC01_SH01", "sc01_sh01a", "sc_01_sh_01", "sc01_sh01_extra", "sc01sh01"])
def test_shot_id_pattern_enforced(bad_id):
    with pytest.raises(Exception):
        _valid_shot(shot_id=bad_id)


@pytest.mark.parametrize("emotion", sorted(EMOTION_LABELS))
def test_expression_cues_rejects_emotion_labels(emotion):
    """The directive's design lock: physical cues only, no emotion labels."""
    with pytest.raises(ValueError, match="no emotion labels"):
        _valid_shot(
            character=CharacterSpec(
                name="Maya",
                expression_cues=f"eyes widen, looks {emotion}",
            )
        )


def test_expression_cues_allows_physical_cues():
    shot = _valid_shot(
        character=CharacterSpec(
            name="Maya",
            expression_cues="jaw tightens, breath held, gaze drops to the paper",
        )
    )
    assert "jaw tightens" in shot.character.expression_cues


def test_asset_weight_bounds():
    with pytest.raises(Exception):
        _valid_shot(assets=[AssetBinding(asset_id="x", type="character", weight=1.5)])


# ---------------------------------------------------------------------------
# 2. Knowledge seeds
# ---------------------------------------------------------------------------


def test_knowledge_seeds_upsert(tmp_path):
    db = tmp_path / "organizer.db"
    status = seed_prompt_machine_knowledge(db_path=db)
    assert set(status.keys()) == SEED_IDS
    assert all(v in ("inserted", "updated") for v in status.values())

    # Re-run → updates, no dupes
    status2 = seed_prompt_machine_knowledge(db_path=db)
    assert set(status2.keys()) == SEED_IDS

    import sqlite3

    with sqlite3.connect(str(db)) as conn:
        rows = conn.execute("SELECT category_id, description FROM knowledge WHERE parent_category='prompt_machine'").fetchall()
    assert len(rows) == 3
    for cid, desc in rows:
        assert desc and len(desc) > 200, f"{cid} seed content missing"
        assert cid in SEEDS


# ---------------------------------------------------------------------------
# 3. Golden integration test (Checkpoint 1 gate)
# ---------------------------------------------------------------------------


def test_golden_script_keyless_shots():
    """2-page golden script → validated ShotSpec[] with no cloud keys present."""
    # Checkpoint 1 gate: the pipeline must not require cloud keys.
    for key in ("OPENAI_API_KEY", "NVIDIA_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY"):
        assert key not in os.environ, f"{key} must be absent for the keyless gate"

    script = GOLDEN.read_text()
    assert 500 < len(script) < 4000, "golden script should be ~2 pages"

    # Test hygiene: clear this project's rows so re-runs are deterministic
    # (INSERT OR REPLACE only touches the shot_ids the LLM produced this run).
    import sqlite3

    from core.paths import get_metadata_root

    with sqlite3.connect(str(get_metadata_root() / "organizer.db")) as conn:
        conn.execute("DELETE FROM shots WHERE project_id='golden_test'")

    from backend.services.director_service import DirectorService

    svc = DirectorService()
    result = svc.generate_shot_list(script=script, project_id="golden_test")

    # The gate requires a local provider; if none is up the test must say so loudly.
    assert result.provider in ("vllm", "ollama"), (
        f"no local provider available (provider={result.provider}); "
        f"start vLLM (localhost:8000) or Ollama (gemma4:12b) and re-run"
    )
    assert not result.degraded, f"director degraded: {result.reason}"

    shots = result.shots
    assert 4 <= len(shots) <= 14, f"expected 4-14 shots for a 2-page script, got {len(shots)}"

    # Structural assertions (Pydantic already validated the schema)
    import re

    for i, shot in enumerate(shots):
        assert re.fullmatch(r"sc\d\d_sh\d\d", shot.shot_id), f"bad shot_id: {shot.shot_id}"
        assert shot.sequence_index == i, "sequence_index must be contiguous"
        assert shot.scene.context and shot.scene.lighting and shot.scene.mood
        assert shot.camera.shot_call
        assert shot.character.name
        # Pydantic enforced this, but assert it again for the record:
        words = set(__import__("re").findall(r"[a-z']+", shot.character.expression_cues.lower()))
        assert not (words & EMOTION_LABELS), f"emotion label leaked into {shot.shot_id}"

    # The cast should be discoverable in the shots
    names = {s.character.name.lower() for s in shots}
    assert any("maya" in n for n in names), "golden script cast (Maya) not found in shots"

    # Persistence check (shots table)
    import sqlite3

    from core.paths import get_metadata_root

    with sqlite3.connect(str(get_metadata_root() / "organizer.db")) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM shots WHERE project_id='golden_test'"
        ).fetchone()[0]
    assert count == len(shots), "shots not persisted to the shots table"

    # Keep a machine-readable record for the checkpoint
    record = Path(__file__).parent / "golden" / "shotlist_record.json"
    record.write_text(
        json.dumps(
            {"provider": result.provider, "shot_count": len(shots), "shot_ids": [s.shot_id for s in shots]},
            indent=2,
        )
    )
