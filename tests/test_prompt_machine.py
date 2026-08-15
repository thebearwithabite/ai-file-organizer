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
    assert result.provider == "ollama", (
        f"no local provider available (provider={result.provider}); "
        f"start Ollama (qwen3.5:4b) and re-run"
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


# ---------------------------------------------------------------------------
# Phase 1 amendments (2026-08-10): orphan cleanup, degrade_reason, determinism
# ---------------------------------------------------------------------------


def _director_shot(shot_id: str, seq: int, project_id: str = "") -> ShotSpec:
    return ShotSpec(
        shot_id=shot_id,
        sequence_index=seq,
        project_id=project_id,
        scene=SceneSpec(context="x", visual_style="naturalistic", lighting="soft", mood="quiet"),
        character=CharacterSpec(name="Maya", expression_cues="eyebrows draw together"),
        camera=CameraSpec(shot_call="Medium Close-Up"),
    )


def test_regenerate_removes_orphans_and_keeps_bindings(tmp_path):
    """delete-then-insert: a rerun with fewer shots must drop the stale rows,
    and manual asset toggles must survive the regeneration."""
    import sqlite3

    from backend.services.asset_service import AssetService
    from backend.services.director_service import DirectorService
    from backend.services.shot_spec import AssetSpec

    db = tmp_path / "t.db"
    svc = DirectorService(db_path=db)
    shots5 = [_director_shot(f"sc01_sh{i:02d}", seq=i, project_id="p1") for i in range(1, 6)]
    svc._persist_shots(shots5, project_id="p1")

    # manual toggle on one shot
    assets = AssetService(db_path=db)
    assets._dedup_and_persist([AssetSpec(asset_id="char_maya", name="Maya", type="character")], "")
    assets.toggle_shot_asset("sc01_sh01", "char_maya", True)

    # regenerate with FEWER shots (the orphan scenario: 5 → 2)
    svc._persist_shots(shots5[:2], project_id="p1")

    with sqlite3.connect(str(db)) as conn:
        remaining = [
            r[0]
            for r in conn.execute(
                "SELECT shot_id FROM shots WHERE project_id='p1' ORDER BY sequence_index"
            ).fetchall()
        ]
    assert remaining == ["sc01_sh01", "sc01_sh02"], f"orphans not removed: {remaining}"

    shot = assets._load_shot("sc01_sh01")
    assert {a.asset_id for a in shot.assets} == {"char_maya"}, "toggle lost on regeneration"


def test_degrade_reason_stored_on_review_rows(tmp_path):
    import sqlite3

    from backend.audio.review_queue import ReviewQueue

    q = ReviewQueue(db_path=tmp_path / "t.db")
    q.enqueue("f1", "r1", batch_group="g", degrade_reason="provider_unreachable")
    q.enqueue("f2", "r2", batch_group="g", degrade_reason="schema_invalid")

    with sqlite3.connect(str(tmp_path / "t.db")) as conn:
        rows = conn.execute(
            "SELECT file_path, degrade_reason FROM review_queue ORDER BY id"
        ).fetchall()
    assert rows == [("f1", "provider_unreachable"), ("f2", "schema_invalid")]


def test_review_table_migration_adds_degrade_reason(tmp_path):
    import sqlite3

    from backend.audio.review_queue import ensure_review_table

    db = tmp_path / "m.db"
    with sqlite3.connect(str(db)) as conn:  # old schema, no degrade_reason
        conn.execute(
            """CREATE TABLE review_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL, reason TEXT NOT NULL, category_hint TEXT,
                surfaced_on TEXT, batch_group TEXT, status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')), UNIQUE(file_path, reason)
            )"""
        )
        conn.commit()
    ensure_review_table(db)
    with sqlite3.connect(str(db)) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(review_queue)")}
    assert "degrade_reason" in cols


def test_provider_kwargs_pins_seed_and_temperature():
    from backend.services.llm_resolver import DIRECTOR_SEED, provider_kwargs

    for name in ("deepseek", "ollama"):
        kw = provider_kwargs(name)
        assert kw["seed"] == DIRECTOR_SEED, f"{name} seed not pinned"
        assert kw["temperature"] == 0.1, f"{name} temperature not pinned"


def test_dead_provider_breaks_early_without_burning_retries():
    from backend.llm.base import LLMProvider
    from backend.services.shot_spec import ShotListOutput

    class DeadProvider(LLMProvider):
        def __init__(self):
            super().__init__(model="dead", max_retries=3)
            self.calls = 0

        def health_check(self):
            return False

        def _generate_raw(self, prompt, **kwargs):
            self.calls += 1
            raise ConnectionError("connection refused")

    p = DeadProvider()
    out, ok = p.generate_structured("x", ShotListOutput, degrade_value=None)
    assert not ok
    assert p.calls == 1, f"retry budget burned on a dead provider: {p.calls} calls"
    assert p.last_failure == "provider_unreachable"
