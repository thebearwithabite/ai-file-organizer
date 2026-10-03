"""Prompt Machine asset tests (PROMPT-MACHINE-DIRECTIVE v1.2, Phase 2).

Layers:
  1. matching helper units — name/text fuzzy match (no LLM)
  2. schema units — AssetSpec validation
  3. persistence — veo_assets upsert, card fields survive re-extract, clear
  4. auto_bind — fuzzy-match shots → selected_asset_ids, weights by type
  5. toggle — manual binding persists across service instances (regen survival)
  6. ref image — StorageProvider round trip (no side doors)
  7. golden integration — golden script → assets → bindings, keyless via vLLM
     (Checkpoint 2 gate). Isolated under project_id='golden_test'.
  8. API wiring — TestClient 422/404/200 on the Phase 2 endpoints
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.services.asset_service import (
    DEFAULT_WEIGHTS,
    AssetService,
    name_matches,
    text_matches,
)
from backend.services.shot_spec import (
    AssetSpec,
    AssetType,
    CameraSpec,
    EntityRef,
    ShotSpec,
)

GOLDEN = Path(__file__).parent / "golden" / "golden_script.md"
GOLDEN_PROJECT = "golden_test"

CLOUD_KEYS = ("OPENAI_API_KEY", "NVIDIA_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY")


def _make_shot(
    shot_id: str = "sc01_sh01",
    name: str = "Maya",
    context: str = "In the kitchen, Maya finds the letter on the counter.",
    seq: int = 0,
    project_id: str = "",
) -> ShotSpec:
    return ShotSpec(
        shot_id=shot_id,
        sequence_index=seq,
        project_id=project_id,
        narrative_intent="Maya finds the letter and the room's cheer drops away.",
        setting=context,
        action="Maya walks in, stops at the counter, and picks up the envelope.",
        lighting="soft window light",
        style_grade="naturalistic, desaturated",
        duration_seconds=6.0,
        camera=CameraSpec(framing="Medium Close-Up", movement="slow push-in"),
        entities=[
            EntityRef(
                entity_id="char_maya",
                name=name,
                description="woman, mid-30s, shoulder-length dark hair",
                expression_cues="eyebrows draw together",
            )
        ],
    )



# ---------------------------------------------------------------------------
# 1. Matching helpers
# ---------------------------------------------------------------------------


def test_name_matches_exact_and_case():
    assert name_matches("Maya", "maya")
    assert name_matches("maya", "MAYA")


def test_name_matches_containment_both_directions():
    assert name_matches("Dr. Chen", "Chen")  # asset longer than character
    assert name_matches("Chen", "Dr. Chen")  # character longer than asset
    assert name_matches("Maya Chen", "MAYA")  # token prefix


def test_name_matches_guards():
    assert name_matches("a", "a")  # exact equality always matches
    assert not name_matches("", "Maya")
    assert not name_matches("Maya", "Tom")
    assert not name_matches("ab", "xaby")  # containment below min length 4


def test_text_matches_token_hit():
    assert text_matches("Kitchen", ["In the kitchen, she pours coffee"])
    assert text_matches("The Letter", ["the unopened letter on the counter"])


def test_text_matches_guards():
    assert not text_matches("Kitchen", ["In the bedroom"])
    assert not text_matches("a", ["a"] * 5)  # token too short
    assert not text_matches("", ["anything"])


# ---------------------------------------------------------------------------
# 2. Schema units
# ---------------------------------------------------------------------------


def test_asset_spec_valid():
    a = AssetSpec(asset_id="char_maya", name="Maya", type="character", description="dark hair")
    assert a.type == AssetType.character


def test_asset_spec_bad_id_rejected():
    with pytest.raises(ValueError):
        AssetSpec(asset_id="Char-Maya!", name="Maya", type="character")


def test_asset_spec_bad_type_rejected():
    with pytest.raises(ValueError):
        AssetSpec(asset_id="char_maya", name="Maya", type="vehicle")


# ---------------------------------------------------------------------------
# 3. Persistence
# ---------------------------------------------------------------------------


def test_dedup_persist_and_card_fields_survive_re_extract(tmp_path):
    svc = AssetService(db_path=tmp_path / "t.db")
    assets = [
        AssetSpec(asset_id="char_maya", name="Maya", type="character", description="dark hair"),
        AssetSpec(asset_id="loc_kitchen", name="Kitchen", type="location", description="morning light"),
    ]
    svc._dedup_and_persist(assets, "")
    assert len(svc.list_assets()) == 2

    # set card fields, then re-extract — they must survive
    svc.update_asset("char_maya", lora_path=r"D:\loras\maya.safetensors", trigger_token="maya1")
    svc._dedup_and_persist(assets, "")
    row = svc.get_asset("char_maya")
    assert row["lora_path"] == r"D:\loras\maya.safetensors"
    assert row["trigger_token"] == "maya1"
    assert len(svc.list_assets()) == 2  # no dupes


def test_update_asset_and_clear(tmp_path):
    svc = AssetService(db_path=tmp_path / "t.db")
    svc._dedup_and_persist([AssetSpec(asset_id="char_maya", name="Maya", type="character")], "")
    svc.update_asset("char_maya", lora_path="lora.bin", trigger_token="tok")
    row = svc.get_asset("char_maya")
    assert row["lora_path"] == "lora.bin"
    assert row["trigger_token"] == "tok"

    # empty string clears
    svc.update_asset("char_maya", lora_path="")
    row = svc.get_asset("char_maya")
    assert row["lora_path"] is None
    assert row["trigger_token"] == "tok"

    assert svc.update_asset("missing", lora_path="x") is None


# ---------------------------------------------------------------------------
# 4. auto_bind
# ---------------------------------------------------------------------------


def test_auto_bind_fuzzy_matches(tmp_path):
    svc = AssetService(db_path=tmp_path / "t.db")
    svc._dedup_and_persist(
        [
            AssetSpec(asset_id="char_maya", name="Maya", type="character"),
            AssetSpec(asset_id="char_tom", name="Tom", type="character"),
            AssetSpec(asset_id="loc_kitchen", name="Kitchen", type="location"),
            AssetSpec(asset_id="prop_letter", name="letter", type="prop"),
        ],
        "",
    )
    svc._persist_shot(_make_shot("sc01_sh01", name="Maya", context="In the kitchen, Maya finds the letter."))
    svc._persist_shot(_make_shot("sc01_sh02", name="Tom", context="Tom opens the front door.", seq=1))

    result = svc.auto_bind()
    assert result["shots"] == 2
    bound = result["bindings"]

    s1 = {a.asset_id for a in svc._load_shot("sc01_sh01").assets}
    assert s1 == {"char_maya", "loc_kitchen", "prop_letter"}
    weights = {a.asset_id: a.weight for a in svc._load_shot("sc01_sh01").assets}
    assert weights["char_maya"] == DEFAULT_WEIGHTS[AssetType.character] == 0.9
    assert weights["loc_kitchen"] == DEFAULT_WEIGHTS[AssetType.location] == 0.6
    assert weights["prop_letter"] == DEFAULT_WEIGHTS[AssetType.prop] == 0.5

    s2 = {a.asset_id for a in svc._load_shot("sc01_sh02").assets}
    assert s2 == {"char_tom"}  # kitchen/letter not in Tom's shot


def test_auto_bind_is_additive_only(tmp_path):
    svc = AssetService(db_path=tmp_path / "t.db")
    svc._dedup_and_persist([AssetSpec(asset_id="char_maya", name="Maya", type="character")], "")
    svc._persist_shot(_make_shot("sc01_sh01", name="Maya"))
    svc.auto_bind()
    first = svc._load_shot("sc01_sh01").assets
    svc.auto_bind()  # second pass must not duplicate
    second = svc._load_shot("sc01_sh01").assets
    assert len(first) == len(second) == 1


def test_auto_bind_respects_exclusions(tmp_path):
    """A manual deselection (toggle off) must survive the reconciliation pass;
    a re-selection must stick."""
    svc = AssetService(db_path=tmp_path / "t.db")
    svc._dedup_and_persist(
        [
            AssetSpec(asset_id="char_maya", name="Maya", type="character"),
            AssetSpec(asset_id="char_tom", name="Tom", type="character"),
        ],
        "",
    )
    svc._persist_shot(_make_shot("sc01_sh01", name="Maya"))
    svc._persist_shot(_make_shot("sc01_sh02", name="Tom", seq=1))

    # deselect Maya on shot 1, then run the reconciliation pass
    svc.toggle_shot_asset("sc01_sh01", "char_maya", False)
    svc.auto_bind()

    s1 = {a.asset_id for a in svc._load_shot("sc01_sh01").assets}
    assert "char_maya" not in s1, "deselected asset re-added by auto_bind"
    s2 = {a.asset_id for a in svc._load_shot("sc01_sh02").assets}
    assert s2 == {"char_tom"}, "unrelated matches still bind"

    # re-select → auto_bind keeps it
    svc.toggle_shot_asset("sc01_sh01", "char_maya", True)
    svc.auto_bind()
    s1 = {a.asset_id for a in svc._load_shot("sc01_sh01").assets}
    assert "char_maya" in s1


def test_exclusion_survives_regeneration(tmp_path):
    """Exclusions are sidecar state: a shot-list rebuild (delete-then-insert)
    must preserve them for surviving shots and drop them for removed ones."""
    import sqlite3

    from backend.services.director_service import DirectorService

    db = tmp_path / "t.db"
    svc = AssetService(db_path=db)
    svc._dedup_and_persist([AssetSpec(asset_id="char_maya", name="Maya", type="character")], "")
    shots2 = [
        _make_shot("sc01_sh01", "Maya", "In the kitchen.", 0, "p1"),
        _make_shot("sc01_sh02", "Tom", "Tom opens the door.", 1, "p1"),
    ]
    DirectorService(db_path=db)._persist_shots(shots2, project_id="p1")

    svc.toggle_shot_asset("sc01_sh01", "char_maya", False)  # deselect on sh01
    svc.toggle_shot_asset("sc01_sh02", "char_maya", True)   # select on sh02

    # rebuild the same shot list — exclusion must survive
    DirectorService(db_path=db)._persist_shots(shots2, project_id="p1")
    with sqlite3.connect(str(db)) as conn:
        ex = conn.execute("SELECT shot_id FROM shot_asset_exclusions").fetchall()
    assert [r[0] for r in ex] == ["sc01_sh01"], f"exclusion lost on rebuild: {ex}"

    # rebuild dropping sh02 — orphan exclusion cleanup must keep only sh01's
    DirectorService(db_path=db)._persist_shots(shots2[:1], project_id="p1")
    with sqlite3.connect(str(db)) as conn:
        ex = conn.execute("SELECT shot_id FROM shot_asset_exclusions").fetchall()
    assert [r[0] for r in ex] == ["sc01_sh01"], f"exclusion orphaned or lost: {ex}"

    # and the deselected binding stays absent from the regenerated shot
    shot = svc._load_shot("sc01_sh01")
    assert "char_maya" not in {a.asset_id for a in shot.assets}


# ---------------------------------------------------------------------------
# 5. Toggle — survives across service instances (regen survival)
# ---------------------------------------------------------------------------


def test_toggle_on_off_and_survives_reload(tmp_path):
    svc = AssetService(db_path=tmp_path / "t.db")
    svc._dedup_and_persist([AssetSpec(asset_id="char_maya", name="Maya", type="character")], "")
    svc._persist_shot(_make_shot("sc01_sh01", name="Maya"))

    r = svc.toggle_shot_asset("sc01_sh01", "char_maya", True)
    assert r["shot_id"] == "sc01_sh01"
    assert any(a["asset_id"] == "char_maya" for a in r["assets"])

    # fresh service instance, same DB — the toggle must have persisted
    svc2 = AssetService(db_path=tmp_path / "t.db")
    shot = svc2._load_shot("sc01_sh01")
    assert {a.asset_id for a in shot.assets} == {"char_maya"}

    r = svc2.toggle_shot_asset("sc01_sh01", "char_maya", False)
    assert r["assets"] == []
    assert {a.asset_id for a in svc2._load_shot("sc01_sh01").assets} == set()

    assert svc2.toggle_shot_asset("missing_shot", "char_maya", True) is None


def test_toggle_unknown_asset_defaults_to_character(tmp_path):
    svc = AssetService(db_path=tmp_path / "t.db")
    svc._persist_shot(_make_shot("sc01_sh01", name="Maya"))
    r = svc.toggle_shot_asset("sc01_sh01", "char_ghost", True)
    assert r["assets"][0]["type"] == "character"


# ---------------------------------------------------------------------------
# 6. Ref image via StorageProvider
# ---------------------------------------------------------------------------


def test_store_ref_image_round_trip(tmp_path):
    from backend.storage.provider import LocalProvider

    svc = AssetService(db_path=tmp_path / "t.db", storage=LocalProvider(root=tmp_path / "store"))
    svc._dedup_and_persist([AssetSpec(asset_id="char_maya", name="Maya", type="character")], "")
    img = tmp_path / "maya_ref.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)

    uri = svc.store_ref_image("char_maya", img)
    assert uri and uri.startswith("file://")
    assert svc.get_asset("char_maya")["ref_image"] == uri
    # object is actually in the storage root
    stored = next((tmp_path / "store").rglob("*.png"), None)
    assert stored is not None and stored.exists()

    assert svc.store_ref_image("missing_asset", img) is None


# ---------------------------------------------------------------------------
# 7. Golden integration (Checkpoint 2 gate — keyless, vLLM)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not GOLDEN.exists(), reason="golden script missing")
def test_golden_script_assets_and_bindings_keyless():
    for var in CLOUD_KEYS:
        assert var not in os.environ, f"cloud key present in env: {var}"

    script = GOLDEN.read_text(encoding="utf-8")
    svc = AssetService()

    # shots first (director pass), then assets, then bind
    from backend.services.director_service import DirectorService

    shots = DirectorService().generate_shot_list(
        script=script, project_id=GOLDEN_PROJECT, allow_cloud_script=False
    )
    assert not shots.degraded and len(shots.shots) >= 4, f"shot list degraded: {shots.reason}"

    result = svc.extract_assets(script=script, project_id=GOLDEN_PROJECT, allow_cloud_script=False)
    assert not result.degraded, f"extraction degraded: {result.reason}"
    assert result.provider != "none"
    assert len(result.assets) >= 3

    chars = [a for a in result.assets if a.type == AssetType.character]
    assert len(chars) >= 2
    names = " ".join(a.name.lower() for a in chars)
    assert "maya" in names, f"expected Maya among characters: {names}"
    assert "tom" in names, f"expected Tom among characters: {names}"

    bound = svc.auto_bind(project_id=GOLDEN_PROJECT)
    assert bound["shots"] >= 4
    # The director pass already embeds character bindings in the shot JSON
    # (the shot-list prompt asks for one character asset per shot), so
    # auto_bind is a reconciliation pass: it fills gaps and never undoes a
    # manual deselection.
    shot0 = svc._load_shot(shots.shots[0].shot_id)
    assert any(a.asset_id == "char_maya" for a in shot0.assets), (
        "director pass should embed the character binding"
    )

    # Manual deselection must survive auto_bind (exclusion row honored)
    svc.toggle_shot_asset(shot0.shot_id, "char_maya", False)
    svc.auto_bind(project_id=GOLDEN_PROJECT)
    after = {a.asset_id for a in svc._load_shot(shot0.shot_id).assets}
    assert "char_maya" not in after, f"auto_bind re-added a deselected asset: {after}"

    # Re-selecting restores it and survives another auto_bind
    svc.toggle_shot_asset(shot0.shot_id, "char_maya", True)
    svc.auto_bind(project_id=GOLDEN_PROJECT)
    after = {a.asset_id for a in svc._load_shot(shot0.shot_id).assets}
    assert "char_maya" in after, f"re-selected asset missing after auto_bind: {after}"


# ---------------------------------------------------------------------------
# 8. API wiring
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    from main import app

    return TestClient(app)


def test_api_extract_assets_422_short_script(client):
    r = client.post("/api/prompt-machine/extract-assets", json={"script": "hi"})
    assert r.status_code == 422


def test_api_assets_list_ok(client):
    r = client.get("/api/prompt-machine/assets")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_api_assets_404s(client):
    assert client.patch("/api/prompt-machine/assets/nope", json={"lora_path": "x"}).status_code == 404
    assert client.post("/api/prompt-machine/shots/nope/assets", json={"asset_id": "char_x"}).status_code == 404
    assert (
        client.post(
            "/api/prompt-machine/assets/nope/ref-image",
            files={"file": ("r.png", b"\x89PNG\r\n\x1a\n" + b"0" * 32, "image/png")},
        ).status_code
        == 404
    )


def test_api_auto_bind_unknown_project_no_mutation(client):
    # project that has no shots/assets: 200, zero bindings, zero mutation
    r = client.post("/api/prompt-machine/auto-bind-assets", json={"project_id": "__api_test_nope__"})
    assert r.status_code == 200
    assert r.json()["shot_count"] == 0
    assert r.json()["bindings"] == {}
