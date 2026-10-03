"""Prompt compiler: engine-neutral ShotSpec -> per-engine render payloads.

PROMPT-MACHINE-DIRECTIVE v1.2, Phase 3. ``ShotSpec`` says what a shot *is*;
this module says what a particular renderer needs to be told. The split
exists because LTX 2.3 and the WanGP headless MCP path want genuinely
different things, and neither of those shapes belongs in the schema.

Three guarantees hold everywhere in this module:

**Pure.** No network, no filesystem writes, no clock, no randomness, no LLM
call. It reads the template registry and settings files, and returns dicts.
The settings discipline at the transport boundary
(``backend.integrations.wangp_settings``) is reused rather than
reimplemented, so there is exactly one definition of "the six overrides".

**Deterministic.** Same ShotSpec + template + overrides -> byte-identical
output. Every derived value (seed, frame count, prose assembly) is a pure
function of its inputs; nothing is sampled and nothing is ordered by dict
iteration luck. That is what makes the snapshot tests meaningful and the
payload cacheable.

**Six overrides, or it raises.** ``width, height, frames, fps, steps,
loras`` are the only settings a caller may touch. Everything else comes
from the template file. An unknown override key is a hard error naming the
key and the six legal ones -- never a silent drop, because a silently
dropped override is a render that looks fine and is not the one that was
asked for.

Emitters:

``emit_ltx_prompt``
    One flowing prose paragraph for LTX 2.3: shot establish, scene and
    lighting, action, subject (physical cues only), camera movement with
    the subject described *after* the move, then audio with dialogue in
    quotation marks. Recurring entities repeat their ``description``
    verbatim -- that repetition is the consistency mechanism; there is no
    description lock and no description-lock text to drift.

``emit_wangp_payload``
    The WanGP-compatible request for the headless MCP path: resolved
    settings plus the per-shot job inputs (prompt, seed, negative prompt,
    media anchors). Prompt enhancer stays off -- an enhancer rewrites the
    prose we just carefully composed, which would undo the ShotSpec.

Usage::

    from backend.services.prompt_compiler import compile_shot

    payload = compile_shot(spec, target="ltx23")
    payload = compile_shot(spec, target="wangp",
                           overrides={"frames": 193, "fps": 24})

CLI::

    python -m backend.services.prompt_compiler --validate examples/shotspec/*.json
    python -m backend.services.prompt_compiler --compile examples/shotspec/talking_head_single.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from backend.integrations.wangp_settings import (  # discipline: single source of truth
    ALLOWED_OVERRIDE_KEYS,
    SettingsDisciplineError,
    UnknownOverrideError,
    apply_overrides,
    load_template,
    merge_job_inputs,
)
from backend.services.shot_spec import (
    AssetType,
    EntityRef,
    ShotSpec,
    ShotSpecValidationError,
    validate_shot_spec,
)

__all__ = [
    "ALLOWED_OVERRIDE_KEYS",
    "TARGETS",
    "CompilerError",
    "OverrideRejected",
    "PromptTooLong",
    "TemplateNotFound",
    "CompiledShot",
    "TemplateSpec",
    "load_registry",
    "select_template",
    "estimate_tokens",
    "emit_ltx_prompt",
    "emit_wangp_payload",
    "compile_shot",
    "compile_shots",
    "main",
]

#: Render targets the compiler knows how to emit for.
TARGETS: Tuple[str, ...] = ("ltx23", "wangp")

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / "templates" / "wangp"
REGISTRY_PATH = TEMPLATE_DIR / "index.json"

#: Frames must sit on the 8n+1 lattice LTX-2 / WanGP require.
FRAME_LATTICE = 8

#: Frames below this do not give the model a coherent temporal window.
MIN_FRAMES = 9

#: Conservative ceiling; the renderer's own hard limit is the backstop.
MAX_FRAMES = 481

#: Clamp for the aspect hint used in template selection. The ShotSpec schema
#: deliberately does not carry a ratio -- that is a delivery decision, not a
#: creative one -- so the caller supplies it when it matters.
ASPECTS = ("16:9", "9:16", "1:1", "4:3", "21:9", "4:5")

_DEFAULT_NEGATIVE = (
    "text, captions, subtitles, watermark, logo, deformed hands, "
    "extra fingers, extra limbs, flicker, warped faces"
)


class CompilerError(ValueError):
    """Base class for compile failures. Every message names the fix."""


class OverrideRejected(CompilerError, UnknownOverrideError):
    """An override outside the six legal keys was requested."""


class PromptTooLong(CompilerError):
    """The composed prose exceeds the per-engine token budget.

    Raised, never truncated. The directive forbids silent truncation: a
    clipped prompt renders a shot that is missing its ending, and nobody
    notices until the cut. The caller runs a compression pass and recompiles.
    """


class TemplateNotFound(CompilerError):
    """No template matches the requested id/aspect/duration."""


# ---------------------------------------------------------------------------
# Template registry + selection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TemplateSpec:
    """One selectable template: a settings file plus selection metadata."""

    template_id: str
    path: Path
    settings: Mapping[str, Any]
    targets: Tuple[str, ...]
    aspect: str
    min_duration_s: float
    max_duration_s: float
    priority: int
    max_prompt_tokens: int
    description: str = ""

    def covers(self, duration_s: float) -> bool:
        return self.min_duration_s <= duration_s <= self.max_duration_s

    def as_manifest(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "file": self.path.name,
            "targets": list(self.targets),
            "aspect": self.aspect,
            "duration_range_s": [self.min_duration_s, self.max_duration_s],
            "priority": self.priority,
            "max_prompt_tokens": self.max_prompt_tokens,
            "model": self.settings.get("model", {}).get("name"),
            "model_type": self.settings.get("model_type"),
        }


def _registry_entries(raw: Mapping[str, Any]) -> List[Dict[str, Any]]:
    entries = raw.get("templates")
    if not isinstance(entries, Sequence) or not entries:
        raise CompilerError(f"{REGISTRY_PATH}: 'templates' must be a non-empty list")
    return [dict(e) for e in entries]


def load_registry(registry_path: Any = None) -> List[TemplateSpec]:
    """Read the template registry and every settings file it names.

    Read-only. Raises ``CompilerError`` if an entry names a missing or
    malformed settings file -- a broken registry must fail at load, not at
    the first render of the night.
    """
    path = Path(registry_path) if registry_path else REGISTRY_PATH
    raw = json.loads(path.read_text(encoding="utf-8"))
    specs: List[TemplateSpec] = []
    for entry in _registry_entries(raw):
        tpath = path.parent / str(entry["file"])
        if not tpath.is_file():
            raise CompilerError(f"{path}: template {entry['template_id']!r} names missing file {tpath.name}")
        settings = load_template(tpath)  # wangp_settings.load_template (utf-8-sig, dict check)
        specs.append(
            TemplateSpec(
                template_id=str(entry["template_id"]),
                path=tpath,
                settings=settings,
                targets=tuple(str(t) for t in entry["targets"]),
                aspect=str(entry["aspect"]),
                min_duration_s=float(entry["min_duration_s"]),
                max_duration_s=float(entry["max_duration_s"]),
                priority=int(entry.get("priority", 0)),
                max_prompt_tokens=int(entry.get("max_prompt_tokens", 512)),
                description=str(entry.get("description", "")),
            )
        )
    # Deterministic order: registry order is the file's order, but sort by id
    # so a future index edit cannot silently reorder selection ties.
    return sorted(specs, key=lambda s: s.template_id)


def select_template(
    duration_s: float,
    *,
    template_id: Optional[str] = None,
    target: str = "ltx23",
    aspect: str = "16:9",
    registry: Optional[Sequence[TemplateSpec]] = None,
) -> TemplateSpec:
    """Pick the template for one shot. Pure, explicit, no LLM.

    Rules, in order:

    1. An explicit ``template_id`` wins, provided it supports ``target``.
    2. Otherwise narrow to templates registered for ``target`` with a
       matching ``aspect`` and a duration range covering ``duration_s``.
    3. Among those, take the highest ``priority``; ties break on the
       narrowest duration range, then on ``template_id``.

    The draft template sits at a lower priority than production, so a
    review-loop caller that wants a draft must ask for one by id rather
    than getting it by accident.
    """
    specs = list(registry) if registry is not None else load_registry()

    if template_id:
        for spec in specs:
            if spec.template_id == template_id:
                if target not in spec.targets:
                    raise TemplateNotFound(
                        f"template {template_id!r} does not serve target {target!r} "
                        f"(serves: {', '.join(spec.targets)})"
                    )
                return spec
        known = ", ".join(s.template_id for s in specs)
        raise TemplateNotFound(f"unknown template {template_id!r}; registry has: {known}")

    if target not in TARGETS:
        raise CompilerError(f"unknown target {target!r}; expected one of: {', '.join(TARGETS)}")

    candidates = [
        s for s in specs
        if target in s.targets and s.aspect == aspect and s.covers(duration_s)
    ]
    if not candidates:
        # Widen on aspect before giving up: a vertical delivery still has to
        # render if the only matching template is landscape.
        candidates = [s for s in specs if target in s.targets and s.covers(duration_s)]
        if not candidates:
            available = sorted({s.template_id for s in specs if target in s.targets})
            raise TemplateNotFound(
                f"no template covers duration {duration_s:g}s for target {target!r}; "
                f"available: {', '.join(available)}"
            )
    candidates.sort(
        key=lambda s: (
            -s.priority,
            s.max_duration_s - s.min_duration_s,
            s.template_id,
        )
    )
    return candidates[0]


# ---------------------------------------------------------------------------
# Deterministic derivations
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Token estimate for the prose guard.

    Deliberately crude: ~4 characters per token plus a per-punctuation
    surcharge. An over-estimate costs a needless compression pass; an
    under-estimate ships an over-budget prompt to the renderer. Crude but
    pessimistic is the right direction for a guard.
    """
    words = len(text.split())
    punct = sum(text.count(c) for c in ",.;:!?—")
    return int(words * 1.32 + punct * 0.5) + 1


def derive_seed(spec: ShotSpec) -> int:
    """Stable seed for a spec whose ``seed`` is unset (-1).

    Not random and not the clock: a hash of ``project_id:shot_id``. A shot
    re-rendered for review reasons keeps its seed, so a diff between two
    runs is the prompt's fault rather than luck's.
    """
    if spec.seed != -1:
        return int(spec.seed)
    digest = hashlib.sha256(f"{spec.project_id}:{spec.shot_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 2_147_483_647


def snap_frames(frames: int) -> int:
    """Snap a frame count onto the 8n+1 lattice, clamped to the legal band."""
    value = max(MIN_FRAMES, min(MAX_FRAMES, int(frames)))
    # Round up to the next 8n+1 so we never lose requested duration.
    return 1 + ((value - 1 + FRAME_LATTICE - 1) // FRAME_LATTICE) * FRAME_LATTICE


def frames_for_duration(duration_s: float, fps: int) -> int:
    """Frame count for a shot length, on the lattice."""
    return snap_frames(max(1, int(round(float(duration_s) * int(fps)))))


# ---------------------------------------------------------------------------
# Prose helpers — one responsibility each, all pure
# ---------------------------------------------------------------------------


_WS = re.compile(r"\s+")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _clean(text: str) -> str:
    """Collapse whitespace, strip, drop trailing terminal punctuation."""
    out = _WS.sub(" ", str(text or "")).strip()
    return out.rstrip(" .;:,")


def _decapitalize(text: str) -> str:
    """Lowercase only a genuine sentence-initial word.

    Keeps acronyms (``NGU``, ``USA``), mixed-case tokens (``iPhone``,
    ``McKay``) and one-letter all-caps tokens intact so proper nouns and
    model names survive mid-sentence assembly.
    """
    if not text:
        return text
    first = text.split(" ", 1)[0]
    stripped = first.strip("\"'“‘(")
    if not stripped:
        return text
    if stripped.isupper() and len(stripped) > 1:
        return text  # acronym
    if stripped[1:].lower() != stripped[1:]:
        return text  # mixed case, e.g. McKay
    return text[: text.index(stripped)] + stripped[:1].lower() + stripped[1:] + text[text.index(stripped) + len(stripped):]


def _ensure_period(text: str) -> str:
    text = text.strip()
    return text if text.endswith((".", "!", "?")) else text + "."


def _sentence_case(text: str) -> str:
    """Capitalize a sentence's first letter when the source text did not.

    Shot lists routinely store lowercase fragments ("soft overcast window
    light", "the same kitchen, later"), because they are sentence fragments
    by design. Assembled into a paragraph they each become a sentence, so
    they have to start like one. Acronyms and mixed-case tokens are left
    alone -- the same guard ``_decapitalize`` applies in reverse.
    """
    if not text:
        return text
    lead = len(text) - len(text.lstrip())
    body = text[lead:]
    if not body:
        return text
    first = body.split(" ", 1)[0].strip("\"'“‘(")
    if not first or not first[0].isalpha():
        return text
    if first.isupper() or (len(first) > 1 and first[1:].lower() != first[1:]):
        return text  # acronym or McKay-style token
    return text[:lead] + first[:1].upper() + first[1:] + body[len(first):]


def _join(parts: Sequence[str], sep: str = " ") -> str:
    return sep.join(p for p in (str(x).strip() for x in parts) if p)


def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(_clean(text)) if s.strip()]


def _setting_fragments(setting: str) -> List[str]:
    """Split the setting into reusable location/time fragments.

    Terminal punctuation is dropped from every fragment: the emitter joins
    them with commas into one sentence, so a fragment that kept its full stop
    would emit "at dawn., unwashed window".
    """
    return [_clean(s) for s in _split_sentences(setting)]


def _is_dialogue_quoted(dialogue: str) -> bool:
    text = _clean(dialogue)
    if len(text) >= 2 and text[0] in "\"“" and text[-1] in "\"”":
        return True
    return text.startswith(("say", "says"))


def _quote_dialogue(dialogue: str) -> str:
    """Dialogue goes in quotation marks -- LTX needs the boundary to know
    where speech starts and stops."""
    text = _clean(dialogue)
    if not text:
        return ""
    if text[0] in "\"“" and text[-1] in "\"”":
        return text
    if len(text) >= 2 and text[0] == '"':
        return text
    return f'"{text.strip(chr(34))}"'


def _primary_subject(spec: ShotSpec) -> Optional[EntityRef]:
    """The entity the camera is on: first character, else first entity."""
    for entity in spec.entities:
        if entity.kind == AssetType.character:
            return entity
    return spec.entities[0] if spec.entities else None


def subject_phrase(entity: EntityRef) -> str:
    """The recurring descriptive phrase for an entity.

    Drawn from ``name`` + ``description`` only -- the parts the schema
    requires to repeat verbatim across shots. Two shots sharing an
    ``entity_id`` therefore produce byte-identical subject phrasing, which
    is exactly the consistency guarantee the engine-neutral schema buys.
    """
    name = _clean(entity.name)
    desc = _clean(entity.description)
    if not desc:
        return name
    return f"{name}, {desc}"


def _entity_clause(entity: EntityRef) -> str:
    """``Name, description`` plus this shot's physical cues, if any."""
    base = subject_phrase(entity)
    cues = _clean(entity.expression_cues or "")
    if not cues:
        return base
    lead = f"{_clean(entity.name)} {_decapitalize(cues)}"
    return f"{base}; {lead}"


# Camera movements are stored in the shorthand a shot list actually uses
# ("slow push-in", "locked off, a barely perceptible handheld breath"). The
# prose emitter needs a verb to hang them on, so the leading phrase is mapped
# to one. Longest match first: "dolly in" must beat "dolly".
_CAMERA_MOVES: Tuple[Tuple[str, str], ...] = (
    ("dolly in", "dollies in"),
    ("dolly out", "dollies out"),
    ("dolly", "dollies"),
    ("push in", "pushes in"),
    ("push-in", "pushes in"),
    ("pushes in", "pushes in"),
    ("push", "pushes"),
    ("pan left", "pans left"),
    ("pan right", "pans right"),
    ("pan", "pans"),
    ("tilt down", "tilts down"),
    ("tilt up", "tilts up"),
    ("tilt", "tilts"),
    ("crane up", "cranes up"),
    ("crane", "cranes"),
    ("zoom in", "zooms in"),
    ("zoom out", "zooms out"),
    ("zoom", "zooms"),
    ("track", "tracks"),
    ("handheld", "is handheld"),
    ("orbit", "orbits"),
    ("locked off", "is locked off"),
    ("locked-off", "is locked off"),
    ("static", "is static"),
    ("still", "is still"),
    ("fixed", "is fixed"),
)


def _camera_verb(movement: str) -> str:
    """Turn a stored movement phrase into a clause for ``The camera ...``.

    A leading pace adverb ("slow", "fast") is preserved verbatim ahead of the
    verb: dropping it would silently change the shot's intent. The adverb is
    only read from the *front* of the phrase, so "static, slight handheld
    drift" keeps its drift qualifier instead of turning into
    "slight is static".
    """
    text = _clean(movement)
    pace = _pace_words(text)
    body = text[len(pace):].lstrip(" ,-") if pace else text
    lower = body.lower()
    for needle, verb in _CAMERA_MOVES:
        if lower.startswith(needle):
            clause = verb + _rest_clause(body[len(needle):])
            return f"{pace} {clause}" if pace else clause
    # Unknown phrasing: use it as written rather than inventing a verb.
    return f"{pace} {_decapitalize(body)}" if pace else _decapitalize(body)


_PACES = (
    "very slow", "barely perceptible", "slowly", "quickly",
    "slow", "fast", "quick", "gentle", "slight", "slightly",
)


def _pace_words(text: str) -> str:
    """Leading pace adverb, if the phrase opens with one."""
    lower = text.lower()
    for pace in _PACES:
        if lower.startswith(pace) and (len(text) == len(pace) or not text[len(pace)].isalpha()):
            return text[: len(pace)]
    return ""


def _rest_clause(text: str) -> str:
    """Whatever followed the verb, normalized for mid-sentence use.

    A leading comma is stripped before the clause re-adds one, otherwise
    "locked off, a handheld breath" becomes "is locked off, , a handheld
    breath".
    """
    rest = _clean(text).lstrip(" ,;-").rstrip(".")
    return f", {rest}" if rest else ""


# ---------------------------------------------------------------------------
# Emitter: LTX 2.3 prose
# ---------------------------------------------------------------------------


def emit_ltx_prompt(spec: ShotSpec) -> str:
    """Compose the LTX 2.3 prompt: one flowing prose paragraph.

    Order follows the LTX 2.3 prompting spec -- shot establish, scene and
    lighting, action, subject with physical cues, camera movement with the
    subject described after the move, then audio with dialogue in quotes.
    Present tense, 4-8 sentences.

    Deliberately absent: emotion labels (the schema already rejects them in
    ``expression_cues`` and the validator is the enforcement point), readable
    text or logos, JSON, keyword lists, and any second lighting scheme.
    """
    if not isinstance(spec, ShotSpec):
        raise TypeError("emit_ltx_prompt requires a validated ShotSpec")

    sentences: List[str] = []

    # 1. Establish the shot: framing first, then where and when.
    framing = _clean(spec.camera.framing)
    setting_parts = _setting_fragments(spec.setting)
    establish = f"{framing} of " if framing else ""
    # Every fragment is decapitalized once a framing clause precedes it --
    # "Medium Close-Up of A rented kitchen" is wrong, "...of a rented
    # kitchen" is right.
    establish += _join([_decapitalize(p) for p in setting_parts], sep=", ")
    if establish:
        sentences.append(establish)

    # 2. Lighting and grade as one coherent block -- never two light sources.
    look = _join([_clean(spec.lighting), _clean(spec.style_grade)], sep=", ")
    if look:
        sentences.append(_decapitalize(look))

    # 3. The action beat, in the present tense the schema already enforces.
    action = _clean(spec.action)
    if action:
        sentences.append(action)

    # 4. Subjects: recurring phrase verbatim, this shot's physical cues.
    character_clauses = [
        _entity_clause(e) for e in spec.entities if e.kind == AssetType.character
    ]
    if character_clauses:
        sentences.append("; ".join(character_clauses))
    elif spec.entities:
        sentences.append(subject_phrase(spec.entities[0]))

    # 5. Non-character entities (location, prop) as descriptive material.
    other = [subject_phrase(e) for e in spec.entities if e.kind != AssetType.character]
    if other and character_clauses:
        # Only the first keeps its capital; "and The letter" is wrong.
        others = [other[0]] + [_decapitalize(p) for p in other[1:]]
        sentences.append(_join(others, sep=", and "))

    # 6. Camera movement, then the subject as it reads *after* the move.
    movement = _clean(spec.camera.movement)
    lens = _clean(spec.camera.lens_feel)
    if movement:
        sentence = f"The camera {_camera_verb(movement)}"
        subject = _primary_subject(spec)
        if subject is not None:
            # LTX 2.3 rule: describe the subject AFTER the move, not before.
            # If the movement already names its own ending ("ending at
            # Medium"), use a different tail so the clause does not stutter.
            if subject.kind == AssetType.character:
                landing = subject_phrase(subject)
            else:
                landing = _clean(subject.name)
            tail = "arriving on" if "ending" in movement.lower() else "ending on"
            # The landing keeps its capital: "ending on Maya, woman,
            # mid-30s" is a proper noun, not a sentence start.
            sentence += f", {tail} {landing}"
        if lens:
            sentence += f", shot on {lens}"
        sentences.append(sentence)
    elif lens:
        sentences.append(f"The camera is static, shot on {lens}")

    # 7. Audio: room tone and effects, then dialogue in quotation marks.
    room = _join(
        [_decapitalize(_clean(spec.audio.ambience)), _decapitalize(_clean(spec.audio.sfx))],
        sep=", ",
    )
    if room:
        sentences.append(f"The sound is {room}")

    dialogue = _clean(spec.audio.dialogue)
    if dialogue:
        subject = _primary_subject(spec)
        speaker = _clean(subject.name) if subject is not None else ""
        delivery = _decapitalize(_clean(spec.audio.delivery))
        line = _quote_dialogue(dialogue)
        said = f"{speaker} says {line}" if speaker else f"Someone says {line}"
        # Delivery rides as an adverbial tail on the speech verb. On its own
        # sentence it read as a fragment ("level, unhurried, ... Maya says").
        if delivery:
            said = f"{said}, {delivery}"
        sentences.append(said)

    # Every fragment terminates before joining: the paragraph is prose, not a
    # run-on and not a keyword list. Sentence case is applied last, at the
    # single point where fragments become sentences.
    return _join(
        [_ensure_period(_sentence_case(s)) for s in sentences if s],
        sep=" ",
    )


# ---------------------------------------------------------------------------
# Settings + payload
# ---------------------------------------------------------------------------


def _validate_overrides(overrides: Mapping[str, Any]) -> Dict[str, Any]:
    """Reject any key outside the six, naming it and naming the six."""
    overrides = dict(overrides or {})
    unknown = sorted(set(overrides) - set(ALLOWED_OVERRIDE_KEYS))
    if unknown:
        raise OverrideRejected(
            "override key(s) not allowed: "
            + ", ".join(repr(k) for k in unknown)
            + ". Allowed overrides: "
            + ", ".join(ALLOWED_OVERRIDE_KEYS)
            + ". Generation settings come from the template file; the LLM "
              "never composes them."
        )
    return overrides


@dataclass(frozen=True)
class CompiledShot:
    """The result of one compile: payload plus the audit trail.

    ``payload`` is what the renderer gets. ``manifest`` is what a run log
    stores: which template, which overrides, which derived seed, and a
    digest of the prompt so two runs can be compared without re-reading the
    prose.
    """

    target: str
    shot_id: str
    payload: Dict[str, Any]
    settings: Dict[str, Any]
    overrides: Dict[str, Any]
    template: TemplateSpec
    prompt: str
    seed: int
    prompt_tokens: int
    manifest: Dict[str, Any] = field(default_factory=dict)

    @property
    def prompt_digest(self) -> str:
        return hashlib.sha256(self.prompt.encode("utf-8")).hexdigest()[:16]

    def as_manifest(self) -> Dict[str, Any]:
        out = dict(self.manifest)
        out.update(
            {
                "target": self.target,
                "shot_id": self.shot_id,
                "template": self.template.as_manifest(),
                "overrides": dict(self.overrides),
                "seed": self.seed,
                "prompt_sha256_16": self.prompt_digest,
                "prompt_tokens_estimated": self.prompt_tokens,
                "settings": dict(self.settings),
            }
        )
        return out

    def as_dict(self) -> Dict[str, Any]:
        """JSON-serializable form (payload + audit trail in one object)."""
        return {"payload": dict(self.payload), "manifest": self.as_manifest()}


def _resolved_settings(
    spec: ShotSpec,
    template: TemplateSpec,
    overrides: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Template ⊕ the six overrides, with frames derived when unset.

    Deriving frames from ``duration_seconds`` is arithmetic, not inference:
    the caller asked for a 6.5 second shot and the template fixes fps, so
    there is exactly one correct frame count. An explicit ``frames``
    override always wins, and still has to land on the lattice.
    """
    clean = _validate_overrides(overrides)
    effective = dict(clean)

    if "frames" not in effective:
        fps = int(template.settings.get("force_fps") or 24)
        effective["frames"] = frames_for_duration(spec.duration_seconds, fps)
    else:
        effective["frames"] = snap_frames(int(effective["frames"]))

    if "width" in effective or "height" in effective:
        # Both dimensions must be knowable; apply_overrides enforces it
        # against the template's resolution and raises a clear error.
        pass

    settings = apply_overrides(template.settings, effective)
    return settings, effective


def _negative_prompt(spec: ShotSpec, template: TemplateSpec) -> str:
    """Negative prompt: the template's, plus explicit camera negatives.

    The ShotSpec has no negatives field of its own; ``camera.negatives`` is
    accepted as free-form on some upstream shapes, so read it if present
    rather than dropping it on the floor.
    """
    base = _clean(template.settings.get("negative_prompt") or _DEFAULT_NEGATIVE)
    extra = _clean(getattr(spec.camera, "negatives", "") or "")
    if extra:
        return f"{base}, {_decapitalize(extra)}"
    return base


def emit_wangp_payload(
    spec: ShotSpec,
    template: TemplateSpec,
    overrides: Mapping[str, Any],
) -> Dict[str, Any]:
    """The WanGP-compatible request for the headless MCP path.

    Settings come from the template plus the six overrides; per-shot job
    inputs (prompt, seed, negative prompt) travel beside them. Prompt
    enhancer is forced off -- it rewrites prose, which would silently
    discard the ShotSpec.
    """
    settings, effective = _resolved_settings(spec, template, overrides)
    prompt = emit_ltx_prompt(spec)
    seed = derive_seed(spec)

    job_inputs: Dict[str, Any] = {
        "prompt": prompt,
        "seed": seed,
        "negative_prompt": _negative_prompt(spec, template),
        "output_filename": f"{spec.project_id or 'project'}_{spec.shot_id}_v{spec.version}",
    }

    # An approved keyframe (Phase 3b) rides as image_start when the caller
    # supplies one; absent it, the render is text-to-video.
    payload = merge_job_inputs(settings, job_inputs)
    payload["prompt_enhancer"] = False
    return payload


def _compile_ltx23(spec: ShotSpec, template: TemplateSpec, overrides: Mapping[str, Any]) -> Dict[str, Any]:
    """LTX 2.3 target: the prose paragraph plus the settings that produce it.

    The prose is the deliverable; the settings block travels with it because
    a prompt without its render context is not reproducible.
    """
    settings, _ = _resolved_settings(spec, template, overrides)
    prompt = emit_ltx_prompt(spec)
    return {
        "target": "ltx23",
        "prompt": prompt,
        "negative_prompt": _negative_prompt(spec, template),
        "settings": dict(settings),
        "seed": derive_seed(spec),
    }


def compile_shot(
    shot_spec: Any,
    *,
    target: str = "ltx23",
    template: Optional[str] = None,
    overrides: Optional[Mapping[str, Any]] = None,
    aspect: str = "16:9",
    registry: Optional[Sequence[TemplateSpec]] = None,
    max_prompt_tokens: Optional[int] = None,
) -> CompiledShot:
    """Compile one validated ShotSpec into a renderer payload.

    ``shot_spec`` may be a ``ShotSpec`` or any raw mapping/JSON string --
    it is validated here, so a caller cannot skip the schema by accident.

    Raises ``OverrideRejected`` for any override outside the six,
    ``PromptTooLong`` when the prose busts the token budget (never
    truncates), ``TemplateNotFound`` when nothing matches, and
    ``ShotSpecValidationError`` for a bad spec.
    """
    if isinstance(shot_spec, ShotSpec):
        spec = shot_spec
    else:
        spec = validate_shot_spec(shot_spec, source="compile_shot")

    if target not in TARGETS:
        raise CompilerError(f"unknown target {target!r}; expected one of: {', '.join(TARGETS)}")

    chosen = select_template(
        spec.duration_seconds,
        template_id=template,
        target=target,
        aspect=aspect,
        registry=registry,
    )

    if target == "ltx23":
        payload = _compile_ltx23(spec, chosen, overrides or {})
        settings = dict(payload["settings"])
    else:
        payload = emit_wangp_payload(spec, chosen, overrides or {})
        _, effective = _resolved_settings(spec, chosen, overrides or {})
        settings = dict(payload)
        # The WanGP payload is settings ⊕ job inputs; the settings component
        # is what the manifest records.
        for key in list(payload):
            if key in ("prompt", "seed", "negative_prompt", "output_filename", "prompt_enhancer"):
                settings.pop(key, None)

    prompt = payload["prompt"]
    budget = int(max_prompt_tokens if max_prompt_tokens is not None else chosen.max_prompt_tokens)
    tokens = estimate_tokens(prompt)
    if budget > 0 and tokens > budget:
        raise PromptTooLong(
            f"{spec.shot_id}: composed prompt is ~{tokens} tokens, over the "
            f"{budget}-token budget for template {chosen.template_id!r}. "
            "Compress at the ShotSpec level and recompile -- the compiler "
            "does not truncate."
        )

    manifest = {
        "shot_id": spec.shot_id,
        "project_id": spec.project_id,
        "sequence_index": spec.sequence_index,
        "version": spec.version,
        "duration_seconds": spec.duration_seconds,
        "aspect_hint": aspect,
        "template_selection": {
            "requested_id": template,
            "selected_id": chosen.template_id,
            "reason": "explicit" if template else "duration+aspect+target",
        },
        "entities": [
            {
                "entity_id": e.entity_id,
                "name": e.name,
                "kind": e.kind.value,
                "description": e.description,
                "reference_images": list(e.reference_images),
            }
            for e in spec.entities
        ],
        "prompt_digest": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }

    return CompiledShot(
        target=target,
        shot_id=spec.shot_id,
        payload=payload,
        settings=settings,
        overrides=dict(overrides or {}),
        template=chosen,
        prompt=prompt,
        seed=int(payload.get("seed", derive_seed(spec))),
        prompt_tokens=tokens,
        manifest=manifest,
    )


def compile_shots(
    shot_specs: Sequence[Any],
    *,
    target: str = "ltx23",
    template: Optional[str] = None,
    overrides: Optional[Mapping[str, Any]] = None,
    aspect: str = "16:9",
    image_starts: Optional[Mapping[str, str]] = None,
    registry: Optional[Sequence[TemplateSpec]] = None,
) -> List[CompiledShot]:
    """Compile a shot list, attaching approved keyframes when supplied.

    ``image_starts`` maps ``shot_id`` -> approved keyframe path. The compiler
    never invents a keyframe; without an approved one the shot renders
    text-to-video.
    """
    out: List[CompiledShot] = []
    for raw in shot_specs:
        spec = raw if isinstance(raw, ShotSpec) else validate_shot_spec(raw, source="compile_shots")
        keyframe = (image_starts or {}).get(spec.shot_id)
        extra = dict(overrides or {})
        if keyframe and target == "wangp":
            # image_start is a job input, not a setting: it rides in the
            # payload, never in the six.
            compiled = compile_shot(
                spec,
                target=target,
                template=template,
                overrides=extra,
                aspect=aspect,
                registry=registry,
            )
            payload = merge_job_inputs(compiled.settings, {
                "prompt": compiled.prompt,
                "seed": compiled.seed,
                "negative_prompt": compiled.payload.get("negative_prompt", _DEFAULT_NEGATIVE),
                "output_filename": compiled.payload.get("output_filename"),
                "image_start": keyframe,
            })
            payload["prompt_enhancer"] = False
            compiled = CompiledShot(
                target=compiled.target,
                shot_id=compiled.shot_id,
                payload=payload,
                settings=compiled.settings,
                overrides=compiled.overrides,
                template=compiled.template,
                prompt=compiled.prompt,
                seed=compiled.seed,
                prompt_tokens=compiled.prompt_tokens,
                manifest={**compiled.manifest, "image_start": keyframe},
            )
        else:
            compiled = compile_shot(
                spec,
                target=target,
                template=template,
                overrides=extra,
                aspect=aspect,
                registry=registry,
            )
        out.append(compiled)
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="ShotSpec prompt compiler")
    parser.add_argument("--compile", nargs="+", metavar="SPEC", help="compile ShotSpec file(s)")
    parser.add_argument("--validate", nargs="+", metavar="SPEC", help="validate only")
    parser.add_argument("--target", default="ltx23", choices=list(TARGETS))
    parser.add_argument("--template", default=None, help="force a template_id")
    parser.add_argument("--aspect", default="16:9")
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="repeatable override; only the six legal keys are accepted",
    )
    parser.add_argument("--list-templates", action="store_true")
    parser.add_argument("--json", action="store_true", help="emit payload JSON instead of prose")
    args = parser.parse_args(argv)

    if args.list_templates:
        for spec in load_registry():
            print(
                f"{spec.template_id:32s} {spec.aspect:6s} "
                f"{spec.min_duration_s:g}-{spec.max_duration_s:g}s "
                f"prio={spec.priority} {spec.settings.get('resolution')}"
            )
        return 0

    if not args.compile and not args.validate:
        parser.print_help()
        return 2

    overrides: Dict[str, Any] = {}
    for item in args.override:
        key, _, raw = item.partition("=")
        if not _:
            print(f"bad --override {item!r}; expected KEY=VALUE")
            return 2
        value: Any = raw
        if key == "loras":
            value = [v for v in (s.strip() for s in raw.split(",")) if v]
        else:
            try:
                value = int(raw)
            except ValueError:
                pass
        overrides[key.strip()] = value

    rc = 0
    files = args.compile or args.validate
    for path in files:
        try:
            spec = load_spec_file(path)
            if args.validate:
                print(f"ok   {path}  ({spec.shot_id})")
                continue
            compiled = compile_shot(
                spec,
                target=args.target,
                template=args.template,
                overrides=overrides,
                aspect=args.aspect,
            )
            if args.json:
                print(json.dumps(compiled.as_dict(), indent=2, sort_keys=True))
            else:
                print(f"# {compiled.shot_id} [{compiled.target}] "
                      f"template={compiled.template.template_id} "
                      f"tokens~{compiled.prompt_tokens} seed={compiled.seed}")
                print(compiled.prompt)
        except (ShotSpecValidationError, CompilerError, SettingsDisciplineError) as exc:
            rc = 1
            print(f"FAIL {path}")
            print(str(exc))
    return rc


def load_spec_file(path: Any) -> ShotSpec:
    """Load + validate a ShotSpec file (thin wrapper, keeps CLI short)."""
    return validate_shot_spec(
        json.loads(Path(path).read_text(encoding="utf-8")), source=str(path)
    )


if __name__ == "__main__":
    raise SystemExit(_main())