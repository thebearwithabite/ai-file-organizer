"""Template-settings discipline for the WanGP renderer boundary.

Deepy's proven pattern, reused verbatim (directive v1.2): the LLM never
composes generation settings. A call selects a TEMPLATE (a WanGP settings
JSON) and may override EXACTLY six keys:

    width, height, frames, fps, steps, loras

...which map onto WanGP's native fields:

    width+height -> resolution ("WxH")
    frames       -> video_length
    fps          -> force_fps
    steps        -> num_inference_steps
    loras        -> activated_loras (+ optional loras_multipliers)

Everything else in the template is frozen. Per-shot job inputs that are not
generation settings (prompt, seed, media anchors such as image_start,
image_refs, audio_guide, ...) travel beside the settings and are validated
against a small allow-list. Anything else is rejected BEFORE it reaches the
renderer.

This module performs no network I/O and no filesystem writes. ``load_template``
only reads.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

__all__ = [
    "ALLOWED_OVERRIDE_KEYS",
    "JOB_INPUT_KEYS",
    "NATIVE_SETTING_KEYS",
    "SettingsDisciplineError",
    "UnknownOverrideError",
    "TemplateDeviationError",
    "ResolvedSettings",
    "load_template",
    "apply_overrides",
    "merge_job_inputs",
    "build_generation_settings",
    "enforce_bounded_settings",
]

#: The only override keys any caller may request (canonical names).
ALLOWED_OVERRIDE_KEYS: tuple[str, ...] = (
    "width",
    "height",
    "frames",
    "fps",
    "steps",
    "loras",
)

#: WanGP-native field each canonical override may touch at the boundary.
NATIVE_SETTING_KEYS: frozenset[str] = frozenset(
    {
        "resolution",
        "video_length",
        "force_fps",
        "num_inference_steps",
        "activated_loras",
        "loras_multipliers",
    }
)

#: Per-shot job inputs that are NOT generation settings. These may be added or
#: replaced beside the template without violating the six-override rule.
JOB_INPUT_KEYS: frozenset[str] = frozenset(
    {
        "prompt",
        "seed",
        "output_filename",
        "image_start",
        "image_end",
        "image_refs",
        "image_refs_relative_size",
        "video_source",
        "video_guide",
        "audio_guide",
        "audio_refs",
        "negative_prompt",
    }
)


class SettingsDisciplineError(ValueError):
    """A settings request violated the template + six-override discipline."""


class UnknownOverrideError(SettingsDisciplineError):
    """An override key outside the allowed six was requested."""


class TemplateDeviationError(SettingsDisciplineError):
    """A payload deviates from its template outside the allowed six fields."""


def load_template(path: str | Path) -> dict[str, Any]:
    """Read a WanGP settings template (UTF-8; BOM tolerated). Read-only."""
    text = Path(path).read_text(encoding="utf-8-sig")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise SettingsDisciplineError(f"template {path!s} is not a settings object")
    return data


def _coerce_positive_int(value: Any, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise UnknownOverrideError(f"override {key!r} must be a positive integer, got {value!r}")
    if isinstance(value, str):
        value = value.strip()
        if not value.isdigit():
            raise UnknownOverrideError(f"override {key!r} must be a positive integer, got {value!r}")
    number = int(value)
    if number <= 0:
        raise UnknownOverrideError(f"override {key!r} must be positive, got {value!r}")
    return number


def _split_resolution(template: Mapping[str, Any]) -> tuple[int | None, int | None]:
    resolution = str(template.get("resolution") or "").strip().lower()
    if not resolution or "x" not in resolution:
        return None, None
    width, _, height = resolution.partition("x")
    try:
        return int(width), int(height)
    except ValueError:
        return None, None


def _clean_loras(value: Any) -> tuple[list[str], str | None]:
    """Accept a list of LoRA names, or {'names': [...], 'multipliers': '...'}."""
    multipliers: str | None = None
    if isinstance(value, str):
        names = [value]
    elif isinstance(value, (list, tuple)):
        names = [str(item) for item in value]
    elif isinstance(value, Mapping):
        unknown = set(value) - {"names", "activated_loras", "multipliers", "loras_multipliers"}
        if unknown:
            raise UnknownOverrideError(
                f"override 'loras' object has unsupported keys: {sorted(unknown)}; "
                "use names/activated_loras and optionally multipliers/loras_multipliers"
            )
        raw_names = value.get("names", value.get("activated_loras", []))
        names = [str(item) for item in (raw_names if isinstance(raw_names, (list, tuple)) else [raw_names])]
        multipliers = value.get("multipliers", value.get("loras_multipliers"))
        if multipliers is not None:
            multipliers = str(multipliers)
    else:
        raise UnknownOverrideError(f"override 'loras' must be a list or object, got {type(value).__name__}")
    names = [name for name in names if str(name).strip()]
    return names, multipliers


def apply_overrides(template: Mapping[str, Any], overrides: Mapping[str, Any]) -> dict[str, Any]:
    """Return template ⊕ overrides. Rejects any override outside the six."""
    overrides = dict(overrides or {})
    unknown = sorted(set(overrides) - set(ALLOWED_OVERRIDE_KEYS))
    if unknown:
        raise UnknownOverrideError(
            "override key(s) not allowed: "
            + ", ".join(repr(key) for key in unknown)
            + f". Allowed overrides: {', '.join(ALLOWED_OVERRIDE_KEYS)}."
        )
    result = dict(template)

    width = overrides.get("width")
    height = overrides.get("height")
    if width is not None or height is not None:
        base_w, base_h = _split_resolution(template)
        new_w = _coerce_positive_int(width, "width") if width is not None else base_w
        new_h = _coerce_positive_int(height, "height") if height is not None else base_h
        if new_w is None or new_h is None:
            raise SettingsDisciplineError(
                "cannot override width/height: template has no parsable 'resolution' "
                "and both dimensions must be provided together"
            )
        result["resolution"] = f"{new_w}x{new_h}"

    if "frames" in overrides:
        result["video_length"] = _coerce_positive_int(overrides["frames"], "frames")
    if "fps" in overrides:
        result["force_fps"] = _coerce_positive_int(overrides["fps"], "fps")
    if "steps" in overrides:
        result["num_inference_steps"] = _coerce_positive_int(overrides["steps"], "steps")
    if "loras" in overrides:
        names, multipliers = _clean_loras(overrides["loras"])
        result["activated_loras"] = names
        if multipliers is not None:
            result["loras_multipliers"] = multipliers
    return result


def merge_job_inputs(settings: Mapping[str, Any], job_inputs: Mapping[str, Any] | None) -> dict[str, Any]:
    """Attach per-shot job inputs (prompt, seed, media anchors, ...) to settings."""
    result = dict(settings)
    for key, value in dict(job_inputs or {}).items():
        if key in NATIVE_SETTING_KEYS:
            raise UnknownOverrideError(
                f"{key!r} is a generation setting; use the canonical override "
                f"({', '.join(ALLOWED_OVERRIDE_KEYS)}) instead"
            )
        if key not in JOB_INPUT_KEYS:
            raise SettingsDisciplineError(
                f"{key!r} is not a recognized job input; settings changes are limited "
                "to the six overrides"
            )
        result[key] = value
    return result


def build_generation_settings(
    template: Mapping[str, Any],
    overrides: Mapping[str, Any] | None = None,
    job_inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The sanctioned way to produce a render payload: template ⊕ six ⊕ job inputs."""
    return merge_job_inputs(apply_overrides(template, overrides or {}), job_inputs)


def enforce_bounded_settings(
    payload: Mapping[str, Any],
    template: Mapping[str, Any],
    overrides: Mapping[str, Any] | None = None,
) -> None:
    """Transport-boundary check: reject payloads that leave the template discipline.

    Raises TemplateDeviationError / UnknownOverrideError before any network call.
    """
    merged = apply_overrides(template, overrides or {})

    for key, value in merged.items():
        if key in JOB_INPUT_KEYS:
            continue  # job inputs may legitimately differ from the template
        if key not in payload:
            raise TemplateDeviationError(
                f"payload is missing template field {key!r}; settings must be the "
                "template plus the six overrides"
            )
        if payload[key] != value:
            raise TemplateDeviationError(
                f"payload changes template field {key!r} outside the six allowed "
                f"overrides ({', '.join(ALLOWED_OVERRIDE_KEYS)}): "
                f"template={value!r} payload={payload[key]!r}"
            )

    for key in payload:
        if key in merged or key in JOB_INPUT_KEYS:
            continue
        if key in NATIVE_SETTING_KEYS:
            raise TemplateDeviationError(
                f"payload adds native setting {key!r}; use the canonical overrides "
                f"({', '.join(ALLOWED_OVERRIDE_KEYS)})"
            )
        raise SettingsDisciplineError(
            f"payload field {key!r} is not part of the template nor a recognized "
            "job input; nothing was submitted"
        )


@dataclass(frozen=True)
class ResolvedSettings:
    """A template plus its (validated) overrides — everything a render needs.

    Build with :meth:`from_file` (template on disk) or :meth:`from_template`
    (template already in memory, e.g. fetched from the renderer's defaults).
    """

    template: Mapping[str, Any]
    overrides: Mapping[str, Any] = field(default_factory=dict)
    template_path: str | None = None

    def __post_init__(self) -> None:
        apply_overrides(self.template, self.overrides)  # validate now, not at submit time

    @classmethod
    def from_file(cls, path: str | Path, overrides: Mapping[str, Any] | None = None) -> "ResolvedSettings":
        return cls(template=load_template(path), overrides=dict(overrides or {}), template_path=str(path))

    @classmethod
    def from_template(
        cls,
        template: Mapping[str, Any],
        overrides: Mapping[str, Any] | None = None,
        template_path: str | None = None,
    ) -> "ResolvedSettings":
        return cls(template=dict(template), overrides=dict(overrides or {}), template_path=template_path)

    def resolved_settings(self) -> dict[str, Any]:
        """Template ⊕ overrides (the settings component of the payload)."""
        return apply_overrides(self.template, self.overrides)

    def build_payload(self, job_inputs: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Full payload: template ⊕ six overrides ⊕ job inputs."""
        return merge_job_inputs(self.resolved_settings(), job_inputs)

    def as_manifest(self) -> dict[str, Any]:
        """Auditable record for run manifests (no secrets involved)."""
        return {
            "template_path": self.template_path,
            "template_model_type": self.template.get("model_type"),
            "overrides": dict(self.overrides),
        }
