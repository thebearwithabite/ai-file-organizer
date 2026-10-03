"""AssetService — script → veo_assets rows + shot bindings (PROMPT-MACHINE-DIRECTIVE v1.2, Phase 2).

Extracts characters / locations / props / styles from a script via the shared
LLM provider chain (``llm_resolver``), persists them to the ``veo_assets``
table, and fuzzy-matches them to shots — writing ``selected_asset_ids`` into
the shot's persisted spec. The shots table is the source of truth: a manual
toggle survives regen because regeneration merges against the stored row.

Asset cards accept ``lora_path`` / ``trigger_token`` / ``ref_image``. Ref
images land through ``StorageProvider`` (``LocalProvider`` by default) — no
side doors. Re-extracting assets UPDATES the row's name/type/description but
never clobbers card fields (lora_path, trigger_token, ref_image).

Weights follow the directive's hierarchy: character 0.8-1.0, scene 0.5-0.7,
effect 0.3-0.6 → character 0.9, location 0.6, prop 0.5, style 0.4.
"""
from __future__ import annotations

import logging
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from core.paths import get_metadata_root

from backend.storage.provider import LocalProvider, StorageProvider
from backend.services.llm_resolver import (
    DegradeReason,
    enqueue_llm_degrade,
    provider_kwargs,
    resolve_provider,
)

from .shot_spec import (
    EXCLUSIONS_TABLE_DDL,
    SHOTS_TABLE_DDL,
    AssetBinding,
    AssetExtractionOutput,
    AssetSpec,
    AssetType,
    ShotSpec,
)

logger = logging.getLogger(__name__)

ASSET_EXTRACT_MAX_TOKENS = 1500

# Directive weight hierarchy: character 0.8-1.0, scene 0.5-0.7, effect 0.3-0.6
DEFAULT_WEIGHTS = {
    AssetType.character: 0.9,
    AssetType.location: 0.6,
    AssetType.prop: 0.5,
    AssetType.style: 0.4,
}

# ShotSpec field paths searched when fuzzy-matching a non-character asset to a
# shot. Paths are resolved by _shot_text(), which expands the "entities"
# pseudo-path to every entity name/kind/description in the shot.
_SCRIPT_TEXT_FIELDS = {
    "location": ("setting", "action", "lighting", "style_grade"),
    "prop": ("setting", "action", "entities", "audio.sfx"),
    "style": ("style_grade", "lighting", "narrative_intent"),
}


# ---------------------------------------------------------------------------
# Matching helpers (module-level for direct unit testing)
# ---------------------------------------------------------------------------


def _shot_text(shot: ShotSpec, path: str) -> str:
    """Resolve a ShotSpec field path to searchable text.

    ``entities`` is a pseudo-path that expands to every entity's name, kind and
    description, so prop/location matching sees the same recurring descriptive
    phrasing the compiler will use.
    """
    if path == "entities":
        return " ".join(
            f"{e.name} {e.kind.value} {e.description}"
            for e in getattr(shot, "entities", []) or []
        )
    value: object = shot
    for part in path.split("."):
        value = getattr(value, part, None)
        if value is None:
            return ""
    if isinstance(value, (list, tuple)):
        return " ".join(str(v) for v in value)
    return str(value)


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def name_matches(asset_name: str, character_name: str) -> bool:
    """Normalized equality or containment (either direction), min length 4."""
    a, b = _normalize(asset_name), _normalize(character_name)
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) >= 4 and a in b:
        return True
    if len(b) >= 4 and b in a:
        return True
    return False


def text_matches(asset_name: str, haystacks: List[str]) -> bool:
    """Any meaningful token (>= 4 chars) of the asset name appears in the text."""
    tokens = {t for t in re.findall(r"[a-z0-9]+", asset_name.lower()) if len(t) >= 4}
    if not tokens:
        return False
    text = " ".join(haystacks).lower()
    return any(t in text for t in tokens)


@dataclass
class AssetExtractionResult:
    assets: List[AssetSpec] = field(default_factory=list)
    provider: str = "none"
    degraded: bool = False
    reason: str = ""


class AssetService:
    """Characters/locations/props from script → veo_assets rows + shot bindings."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        provider=None,
        storage: Optional[StorageProvider] = None,
    ):
        if db_path is None:
            db_path = get_metadata_root() / "organizer.db"
        self.db_path = db_path
        self._provider = provider  # injected (tests); otherwise resolved per call
        self._storage = storage
        self._init_tables()

    # ------------------------------------------------------------------
    # Tables
    # ------------------------------------------------------------------

    def _init_tables(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS veo_assets (
                    asset_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL DEFAULT '',
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    lora_path TEXT,
                    trigger_token TEXT,
                    ref_image TEXT,
                    weight REAL NOT NULL DEFAULT 0.9,
                    created_at REAL DEFAULT (strftime('%s','now')),
                    updated_at REAL DEFAULT (strftime('%s','now'))
                )"""
            )
            conn.execute(SHOTS_TABLE_DDL)
            conn.execute(EXCLUSIONS_TABLE_DDL)
            conn.commit()

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def extract_assets(
        self,
        script: str,
        project_id: str = "",
        allow_cloud_script: bool = False,
    ) -> AssetExtractionResult:
        """Script → validated AssetSpec[] (bounded retry, degrade-to-queue)."""
        provider, name = resolve_provider(allow_cloud_script, injected=self._provider)
        if provider is None:
            enqueue_llm_degrade(
                script, project_id, "no local LLM provider available",
                degrade_reason=DegradeReason.provider_unreachable.value,
            )
            return AssetExtractionResult(
                degraded=True,
                reason="no local LLM provider available (vLLM and Ollama unreachable)",
            )

        prompt = self._build_extract_prompt(script)
        kwargs = provider_kwargs(name, max_tokens=ASSET_EXTRACT_MAX_TOKENS)
        output, ok = provider.generate_structured(
            prompt, AssetExtractionOutput, degrade_value=None, **kwargs
        )

        if not ok or output is None:
            reason = getattr(provider, "last_failure", "") or DegradeReason.schema_invalid.value
            enqueue_llm_degrade(
                script, project_id, f"asset extraction failed ({name})",
                degrade_reason=reason,
            )
            return AssetExtractionResult(
                provider=name,
                degraded=True,
                reason=f"asset extraction failed after retries ({name})",
            )

        assets = self._dedup_and_persist(output.assets, project_id)
        return AssetExtractionResult(assets=assets, provider=name, degraded=False, reason="")

    def _dedup_and_persist(self, assets: List[AssetSpec], project_id: str) -> List[AssetSpec]:
        """Upsert asset rows; card fields (lora/trigger/ref) survive re-extraction."""
        seen: dict[str, AssetSpec] = {}
        for a in assets:
            seen[a.asset_id] = a
        with sqlite3.connect(str(self.db_path)) as conn:
            for a in seen.values():
                conn.execute(
                    """INSERT INTO veo_assets
                           (asset_id, project_id, name, type, description, weight)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(asset_id) DO UPDATE SET
                           name = excluded.name,
                           type = excluded.type,
                           description = excluded.description,
                           weight = excluded.weight,
                           updated_at = strftime('%s','now')""",
                    (
                        a.asset_id,
                        project_id,
                        a.name,
                        a.type.value,
                        a.description,
                        DEFAULT_WEIGHTS[a.type],
                    ),
                )
            conn.commit()
        return list(seen.values())

    def _build_extract_prompt(self, script: str) -> str:
        return f"""You are a script supervisor extracting the asset list for AI video generation.

TASK: Extract recurring characters, key locations, notable props, and style references from the script as STRICT JSON matching exactly this shape:
{{"assets": [{{"asset_id": "...", "name": "...", "type": "character | location | prop | style", "description": "..."}}]}}

Rules:
- asset_id: LOWERCASE, underscores ONLY — NO hyphens, NO spaces, NO parentheses, NO dots. Strip or replace every non-alphanumeric character. Prefix char_/loc_/prop_/style_ (e.g. char_maya, loc_kitchen, prop_letter, prop_wax_sealed_letter).
- name: the proper name as used in the script (may keep hyphens, spaces, parentheses — only asset_id must be sanitized).
- type: one of character, location, prop, style.
- description: one concise line, max 12 words.
- Include every named character, every distinct location, and only props that drive the action. MAXIMUM 10 assets total.
- Output ONLY the JSON object. No markdown fences, no commentary, no trailing text.

Example:
{{"assets": [
  {{"asset_id": "char_maya", "name": "Maya", "type": "character", "description": "woman, mid-30s, dark hair, grey sweater"}},
  {{"asset_id": "loc_kitchen", "name": "Kitchen", "type": "location", "description": "morning light, counter, front door"}},
  {{"asset_id": "prop_wax_sealed_letter", "name": "Wax-Sealed Letter", "type": "prop", "description": "cream envelope, wax seal"}}
]}}

SCRIPT:
{script}
"""

    # ------------------------------------------------------------------
    # Assets CRUD
    # ------------------------------------------------------------------

    def _row_to_dict(self, row) -> dict:
        return {
            "asset_id": row[0],
            "project_id": row[1],
            "name": row[2],
            "type": row[3],
            "description": row[4],
            "lora_path": row[5],
            "trigger_token": row[6],
            "ref_image": row[7],
            "weight": row[8],
        }

    def list_assets(self, project_id: str = "") -> List[dict]:
        with sqlite3.connect(str(self.db_path)) as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT asset_id, project_id, name, type, description, lora_path, "
                    "trigger_token, ref_image, weight FROM veo_assets WHERE project_id = ? "
                    "ORDER BY type, name",
                    (project_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT asset_id, project_id, name, type, description, lora_path, "
                    "trigger_token, ref_image, weight FROM veo_assets ORDER BY type, name"
                ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_asset(self, asset_id: str) -> Optional[dict]:
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT asset_id, project_id, name, type, description, lora_path, "
                "trigger_token, ref_image, weight FROM veo_assets WHERE asset_id = ?",
                (asset_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def update_asset(
        self,
        asset_id: str,
        lora_path: Optional[str] = None,
        trigger_token: Optional[str] = None,
        ref_image: Optional[str] = None,
    ) -> Optional[dict]:
        """Update card fields. Explicit empty string clears a field (→ NULL)."""
        if self.get_asset(asset_id) is None:
            return None
        sets, params = [], []
        for col, val in (
            ("lora_path", lora_path),
            ("trigger_token", trigger_token),
            ("ref_image", ref_image),
        ):
            if val is not None:
                sets.append(f"{col} = ?")
                params.append(val or None)  # "" clears
        if not sets:
            return self.get_asset(asset_id)
        sets.append("updated_at = strftime('%s','now')")
        params.append(asset_id)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(f"UPDATE veo_assets SET {', '.join(sets)} WHERE asset_id = ?", params)
            conn.commit()
        return self.get_asset(asset_id)

    def store_ref_image(
        self,
        asset_id: str,
        local_path: Path,
        provider: Optional[StorageProvider] = None,
    ) -> Optional[str]:
        """Persist a reference image through StorageProvider (no side doors)."""
        if self.get_asset(asset_id) is None:
            return None
        storage = provider or self._storage or LocalProvider()
        suffix = Path(local_path).suffix or ".png"
        key = f"assets/{asset_id}/ref_{int(time.time())}{suffix}"
        ref = storage.put(Path(local_path), key)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "UPDATE veo_assets SET ref_image = ?, updated_at = strftime('%s','now') "
                "WHERE asset_id = ?",
                (ref.uri, asset_id),
            )
            conn.commit()
        logger.info("Stored ref image for %s -> %s", asset_id, ref.uri)
        return ref.uri

    # ------------------------------------------------------------------
    # Shot bindings
    # ------------------------------------------------------------------

    def _load_shots(self, project_id: str = "") -> List[ShotSpec]:
        with sqlite3.connect(str(self.db_path)) as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT shot_json FROM shots WHERE project_id = ?", (project_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT shot_json FROM shots").fetchall()
        return [ShotSpec.model_validate_json(r[0]) for r in rows]

    def _load_shot(self, shot_id: str) -> Optional[ShotSpec]:
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT shot_json FROM shots WHERE shot_id = ?", (shot_id,)
            ).fetchone()
        return ShotSpec.model_validate_json(row[0]) if row else None

    def _persist_shot(self, shot: ShotSpec) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO shots
                   (shot_id, project_id, sequence_index, status, version, shot_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    shot.shot_id,
                    shot.project_id,
                    shot.sequence_index,
                    shot.status.value,
                    shot.version,
                    shot.model_dump_json(),
                ),
            )
            conn.commit()

    def _load_exclusions(self, shot_ids: List[str]) -> dict:
        """{shot_id: {asset_id, ...}} — explicit deselections that auto_bind
        and regeneration must honor."""
        if not shot_ids:
            return {}
        placeholders = ",".join("?" * len(shot_ids))
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                f"SELECT shot_id, asset_id FROM shot_asset_exclusions "
                f"WHERE shot_id IN ({placeholders})",
                shot_ids,
            ).fetchall()
        out: dict[str, set] = {}
        for sid, aid in rows:
            out.setdefault(sid, set()).add(aid)
        return out

    def _asset_matches_shot(self, shot: ShotSpec, asset: dict) -> bool:
        atype = asset["type"]
        if atype == "character":
            # Characters match on entity names; a shot may carry several, and a
            # recurring character appears in every shot of the scene.
            names = [
                e.name
                for e in getattr(shot, "entities", []) or []
                if e.kind == AssetType.character
            ]
            return any(name_matches(asset["name"], n) for n in names)
        fields = _SCRIPT_TEXT_FIELDS.get(atype, ("setting", "action"))
        haystacks = [h for h in (_shot_text(shot, f) for f in fields) if h]
        return text_matches(asset["name"], haystacks)

    def auto_bind(self, project_id: str = "") -> dict:
        """Fuzzy-match assets to shots; persist selected_asset_ids.

        Add-only, and honors explicit exclusions: an asset the user toggled
        OFF on a shot is never re-added by reconciliation (or by a rebuild —
        exclusions live in their own table and survive regeneration).
        """
        shots = self._load_shots(project_id)
        assets = self.list_assets(project_id) if project_id else self.list_assets()
        excluded = self._load_exclusions([s.shot_id for s in shots])
        bound: dict[str, List[str]] = {}
        for shot in shots:
            existing = {a.asset_id for a in shot.assets}
            skip = excluded.get(shot.shot_id, set())
            for asset in assets:
                if asset["asset_id"] in existing or asset["asset_id"] in skip:
                    continue
                if self._asset_matches_shot(shot, asset):
                    shot.assets.append(
                        AssetBinding(
                            asset_id=asset["asset_id"],
                            type=AssetType(asset["type"]),
                            weight=DEFAULT_WEIGHTS[AssetType(asset["type"])],
                        )
                    )
                    bound.setdefault(shot.shot_id, []).append(asset["asset_id"])
            self._persist_shot(shot)
        logger.info("auto_bind: %d shots scanned, %d bindings", len(shots), sum(len(v) for v in bound.values()))
        return {"shots": len(shots), "bindings": bound}

    def toggle_shot_asset(self, shot_id: str, asset_id: str, selected: bool = True) -> Optional[dict]:
        """Manual toggle of an asset binding on a shot. Persists immediately.

        Toggle-OFF writes an exclusion row (the deselection survives auto_bind
        and regeneration); toggle-ON clears it.
        """
        shot = self._load_shot(shot_id)
        if shot is None:
            return None
        asset = self.get_asset(asset_id)
        atype = AssetType(asset["type"]) if asset else AssetType.character
        shot.assets = [a for a in shot.assets if a.asset_id != asset_id]
        with sqlite3.connect(str(self.db_path)) as conn:
            if selected:
                conn.execute(
                    "DELETE FROM shot_asset_exclusions WHERE shot_id = ? AND asset_id = ?",
                    (shot_id, asset_id),
                )
                shot.assets.append(
                    AssetBinding(asset_id=asset_id, type=atype, weight=DEFAULT_WEIGHTS[atype])
                )
            else:
                conn.execute(
                    "INSERT OR IGNORE INTO shot_asset_exclusions (shot_id, asset_id) VALUES (?, ?)",
                    (shot_id, asset_id),
                )
            conn.commit()
        self._persist_shot(shot)
        return {"shot_id": shot_id, "assets": [a.model_dump() for a in shot.assets]}
