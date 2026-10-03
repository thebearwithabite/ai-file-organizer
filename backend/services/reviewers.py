"""Artifact reviewers — deterministic probes and an LLM critique.

Two reviewers, both returning the same :class:`ReviewVerdict`:

:class:`ArtifactProbeReviewer`
    Frame-level checks against the render itself: does the file exist, is it
    non-trivial, does its duration match the ShotSpec, are its frames
    distinct rather than a frozen still. No LLM, no network, fully
    deterministic — this is the CI-safe default, and the one whose verdicts
    provably terminate the retry loop.

:class:`CritiqueReviewer`
    Routes a critique against the ShotSpec's intent through the LLM router and
    validates the reply against a Pydantic schema. Produces structured
    revision fields so a failure can drive an actual re-compile rather than a
    bare "try again".

Why the probe reviewer exists at all
------------------------------------
An LLM critic judging a 6-second clip from a few sampled frames is a weak
signal, and on a box where the local model may be down it is *no* signal. A
review loop whose only reviewer can vanish is a loop that either stalls or
silently approves. The probe reviewer is boring, always available, and catches
the failure modes that actually cost GPU hours: an empty file, a truncated
write, a frozen frame, a duration that does not match the spec.

ffprobe is optional. When it is absent the probe degrades to the checks it can
make from the filesystem alone and *says so* in the verdict notes rather than
quietly reporting a pass it did not earn.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from backend.services.review_loop import ReviewVerdict

logger = logging.getLogger(__name__)

__all__ = [
    "ProbeResult",
    "probe_artifact",
    "ffprobe_available",
    "ArtifactProbeReviewer",
    "CritiqueReviewer",
    "CritiqueOutput",
    "MIN_ARTIFACT_BYTES",
]

#: Below this, an artifact is a stub, a placeholder, or a failed write.
MIN_ARTIFACT_BYTES = 1024

#: Duration tolerance when comparing probe duration to the ShotSpec's.
DURATION_TOLERANCE_S = 0.75

#: Identical-frame ratio above which a clip counts as frozen.
FROZEN_FRAME_RATIO = 0.98


def ffprobe_available(explicit: Optional[str] = None) -> Optional[str]:
    """Path to a usable ffprobe, or None.

    Resolved through PATH. Callers may pass an explicit binary; there is no
    bundled copy because a media probe is an operator's tool choice, not a
    pipeline dependency.
    """
    candidate = explicit or os.environ.get("FFPROBE") or "ffprobe"
    return shutil.which(candidate)


@dataclass(frozen=True)
class ProbeResult:
    """What we could learn about one artifact from the filesystem/probe."""

    path: str
    exists: bool = False
    size_bytes: int = 0
    duration_s: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    frame_count: Optional[int] = None
    distinct_frame_ratio: Optional[float] = None
    probed: bool = False
    probe_error: str = ""
    checks: Tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.exists and self.size_bytes >= MIN_ARTIFACT_BYTES

    def as_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "duration_s": self.duration_s,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "frame_count": self.frame_count,
            "distinct_frame_ratio": self.distinct_frame_ratio,
            "probed": self.probed,
            "probe_error": self.probe_error,
            "checks": list(self.checks),
        }


def probe_artifact(path: Any, *, ffprobe: Optional[str] = None) -> ProbeResult:
    """Inspect one artifact. Never raises; failures land in the result.

    Two layers: filesystem facts always, ffprobe/ffmpeg-derived facts when the
    binaries exist. An unreadable or absent artifact is a *result*, not an
    exception, because "the render produced nothing" is exactly the condition
    the review loop exists to catch.
    """
    target = Path(path)
    exists = target.is_file()
    size = target.stat().st_size if exists else 0

    if not exists:
        return ProbeResult(path=str(target), exists=False, size_bytes=0, checks=("exists",))
    if size < MIN_ARTIFACT_BYTES:
        return ProbeResult(
            path=str(target),
            exists=True,
            size_bytes=size,
            checks=("exists", "size"),
        )

    binary = ffprobe_available(ffprobe)
    if not binary:
        return ProbeResult(
            path=str(target),
            exists=True,
            size_bytes=size,
            probed=False,
            checks=("exists", "size"),
        )

    try:
        raw = subprocess.run(  # noqa: S603 - fixed argv, resolved via PATH
            [
                binary,
                "-v", "error",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(target),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return ProbeResult(
            path=str(target),
            exists=True,
            size_bytes=size,
            probed=False,
            probe_error=f"{type(exc).__name__}: {exc}",
            checks=("exists", "size"),
        )

    if raw.returncode != 0:
        return ProbeResult(
            path=str(target),
            exists=True,
            size_bytes=size,
            probed=False,
            probe_error=(raw.stderr or "ffprobe failed").strip()[:300],
            checks=("exists", "size"),
        )

    try:
        info = json.loads(raw.stdout or "{}")
    except json.JSONDecodeError as exc:
        return ProbeResult(
            path=str(target),
            exists=True,
            size_bytes=size,
            probed=False,
            probe_error=f"unparsable ffprobe output: {exc}",
            checks=("exists", "size"),
        )

    duration = _as_float((info.get("format") or {}).get("duration"))
    video = next(
        (
            s
            for s in (info.get("streams") or [])
            if isinstance(s, Mapping) and s.get("codec_type") == "video"
        ),
        None,
    )
    width = height = None
    fps = frames = None
    if isinstance(video, Mapping):
        width = _as_int(video.get("width"))
        height = _as_int(video.get("height"))
        fps = _parse_rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
        frames = _as_int(video.get("nb_frames"))

    distinct = _distinct_frame_ratio(target, ffprobe=binary)

    return ProbeResult(
        path=str(target),
        exists=True,
        size_bytes=size,
        duration_s=duration,
        width=width,
        height=height,
        fps=fps,
        frame_count=frames,
        distinct_frame_ratio=distinct,
        probed=True,
        checks=("exists", "size", "probe"),
    )


def _as_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None  # drop NaN


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_rate(value: Any) -> Optional[float]:
    """'24/1' -> 24.0. A zero denominator means unknown, not infinite."""
    text = str(value or "").strip()
    if "/" in text:
        num, _, den = text.partition("/")
        try:
            numerator, denominator = float(num), float(den)
        except ValueError:
            return None
        return numerator / denominator if denominator else None
    return _as_float(text)


def _distinct_frame_ratio(target: Path, *, ffprobe: str, samples: int = 6) -> Optional[float]:
    """Fraction of sampled frames that are pairwise distinct.

    Uses ffmpeg's framehash muxer, so no image library is needed. Returns None
    when ffmpeg is unavailable or the hash pass fails — an unknown freeze ratio
    is reported as unknown, never as "not frozen".
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    try:
        raw = subprocess.run(  # noqa: S603 - fixed argv, resolved via PATH
            [
                ffmpeg,
                "-v", "error",
                "-i", str(target),
                "-vf", f"select='not(mod(n\\,max(1\\,floor(tb))) )'",
                "-vsync", "0",
                "-f", "framehash",
                "-hash", "sha256",
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if raw.returncode != 0:
        return None

    hashes: List[str] = []
    for line in (raw.stdout or "").splitlines():
        parts = line.split(",")
        # framehash rows are: stream, dts, pts, duration, size, hash
        if len(parts) >= 6 and parts[0].strip().isdigit():
            hashes.append(parts[-1].strip())
    if len(hashes) < 2:
        return None
    unique = len(set(hashes))
    return unique / len(hashes)


# ---------------------------------------------------------------------------
# Deterministic reviewer
# ---------------------------------------------------------------------------


class ArtifactProbeReviewer:
    """Judge an artifact from measurable facts about the render itself.

    Deterministic by construction: same artifact, same verdict, every time. No
    clock, no network, no RNG. This is what CI exercises, and what proves the
    retry ceiling terminates.
    """

    name = "artifact-probe"

    def __init__(
        self,
        *,
        ffprobe: Optional[str] = None,
        duration_tolerance_s: float = DURATION_TOLERANCE_S,
        require_distinct_frames: bool = True,
    ) -> None:
        self.ffprobe = ffprobe
        self.duration_tolerance_s = float(duration_tolerance_s)
        self.require_distinct_frames = bool(require_distinct_frames)

    def review(
        self,
        *,
        shot_spec: Any,
        compiled: Any = None,
        artifacts: Sequence[str] = (),
        attempt: int = 1,
    ) -> ReviewVerdict:
        reasons: List[str] = []
        notes: List[str] = []

        if not artifacts:
            return ReviewVerdict(
                passed=False,
                reviewer=self.name,
                reasons=("no_artifact",),
                notes=(
                    "the renderer reported success but produced no artifact path; "
                    "treat the job as failed rather than approving an empty shot",
                ),
            )

        probes = [probe_artifact(p, ffprobe=self.ffprobe) for p in artifacts]
        primary = probes[0]

        if not primary.exists:
            reasons.append("artifact_missing")
            notes.append(f"artifact {primary.path} does not exist")
        elif not primary.ok:
            reasons.append("artifact_too_small")
            notes.append(
                f"artifact {primary.path} is {primary.size_bytes} bytes, below the "
                f"{MIN_ARTIFACT_BYTES}-byte floor — likely a truncated or empty write"
            )

        expected_duration = float(getattr(shot_spec, "duration_seconds", 0.0) or 0.0)
        if primary.probed and primary.duration_s is not None and expected_duration > 0:
            delta = abs(primary.duration_s - expected_duration)
            if delta > self.duration_tolerance_s:
                reasons.append("duration_mismatch")
                notes.append(
                    f"artifact runs {primary.duration_s:.2f}s but the ShotSpec asks for "
                    f"{expected_duration:.2f}s (delta {delta:.2f}s exceeds "
                    f"{self.duration_tolerance_s:.2f}s tolerance)"
                )

        if (
            self.require_distinct_frames
            and primary.distinct_frame_ratio is not None
            and primary.distinct_frame_ratio <= FROZEN_FRAME_RATIO
        ):
            reasons.append("frozen_frames")
            notes.append(
                f"only {primary.distinct_frame_ratio:.0%} of sampled frames are distinct — "
                f"the clip reads as a still image held for the shot length"
            )

        if not primary.probed:
            # Say so. A verdict that silently skipped the checks it could not
            # run is a verdict the operator will over-trust.
            notes.append(
                f"ffprobe unavailable ({primary.probe_error or 'not on PATH'}); "
                f"duration and freeze checks were skipped, so this verdict covers "
                f"file existence and size only"
            )

        if reasons:
            return ReviewVerdict(
                passed=False,
                reviewer=self.name,
                reasons=tuple(reasons),
                notes=tuple(notes),
            )

        # Built with an explicit list, not ``tuple(x for p in probes)``: the
        # generator form makes ``for p in probes`` bind to the *tuple* call, so
        # it yields one list per probe instead of one string per probe, and
        # ``verdict.notes`` silently becomes a tuple-of-lists. Every consumer
        # then substring-tests a list and quietly finds nothing.
        #
        # No filenames in these notes: the renderer's filenames embed the job
        # id, so naming the file would smuggle a per-run value into the notes
        # and break manifest reproducibility. The paths are already recorded
        # in dedicated ``artifacts`` / ``artifacts_native`` fields.
        artifact_notes = [
            f"artifact verified: {p.size_bytes} bytes"
            + (f", {p.duration_s:.2f}s" if p.duration_s is not None else "")
            + (f", {p.width}x{p.height}" if p.width and p.height else "")
            + (
                f", {p.distinct_frame_ratio:.0%} distinct frames"
                if p.distinct_frame_ratio is not None
                else ""
            )
            + (
                " (duration and freeze checks skipped: no ffprobe)"
                if not p.probed
                else ""
            )
            for p in probes
        ]
        return ReviewVerdict(
            passed=True,
            reviewer=self.name,
            reasons=(),
            notes=tuple([*notes, *artifact_notes]),
        )


# ---------------------------------------------------------------------------
# LLM critique reviewer
# ---------------------------------------------------------------------------


class CritiqueOutput:
    """Schema for the critique reply.

    A plain Pydantic model built lazily so this module imports without pulling
    the LLM stack into a code path that only wants the probe reviewer.
    """

    _model: Any = None

    @classmethod
    def model(cls) -> Any:
        if cls._model is None:
            from pydantic import BaseModel, Field

            class _Critique(BaseModel):
                """Structured critique of one rendered shot."""

                passed: bool = Field(..., description="Does the artifact satisfy the shot's intent?")
                reasons: list[str] = Field(
                    default_factory=list,
                    description="Short machine-readable failure codes, e.g. 'subject_absent'",
                )
                notes: list[str] = Field(
                    default_factory=list,
                    description="Concrete, actionable revision instructions a human could follow",
                )
                action: str | None = Field(None, description="Revised visible action, if the action is wrong")
                lighting: str | None = Field(None, description="Revised lighting, if the lighting is wrong")
                style_grade: str | None = Field(None, description="Revised look/grade")
                camera_framing: str | None = Field(None, description="Revised framing")
                camera_movement: str | None = Field(None, description="Revised camera movement")
                narrative_intent: str | None = Field(None, description="Revised dramatic intent")
                duration_seconds: float | None = Field(None, description="Revised duration, positive seconds")
                overrides: dict[str, object] = Field(
                    default_factory=dict,
                    description=(
                        "Render-setting adjustments. Only width, height, frames, fps, "
                        "steps, loras are honored; anything else is discarded."
                    ),
                )

            cls._model = _Critique
        return cls._model


class CritiqueReviewer:
    """LLM critique of a rendered artifact against the ShotSpec's intent.

    Wraps the router rather than a provider, so the critique obeys the same
    local-first / cloud-overflow rules as the director pass and never reaches
    for a cloud key that is not there.

    Frame sampling is the reviewer's business, not the router's: this class
    receives already-sampled observations and judges them. Keeping sampling
    out means the critique prompt is a pure function of (spec, observations),
    which is what makes a cached critique reproducible.
    """

    name = "llm-critique"

    def __init__(self, router: Any, *, sample_limit: int = 4) -> None:
        self.router = router
        self.sample_limit = int(sample_limit)

    def review(
        self,
        *,
        shot_spec: Any,
        compiled: Any = None,
        artifacts: Sequence[str] = (),
        attempt: int = 1,
        observations: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> ReviewVerdict:
        """Critique one artifact.

        ``observations`` are pre-sampled frame descriptions. They are required:
        a text model cannot see an mp4, and pretending otherwise would produce
        a confident critique of nothing.
        """
        if not observations:
            return ReviewVerdict(
                passed=False,
                reviewer=self.name,
                reasons=("no_observations",),
                notes=(
                    "no sampled frames were supplied; the critique reviewer cannot "
                    "judge a video file from its path alone, so the shot is held "
                    "for an operator rather than approved",
                ),
            )

        prompt = self._build_prompt(shot_spec, compiled, artifacts, observations)
        routed = self.router.complete_structured(
            prompt,
            CritiqueOutput.model(),
            job="review.critique",
            kwargs_for=lambda _provider: {},
        )
        value = routed.value

        notes = [str(n) for n in (value.notes or []) if str(n).strip()]
        reasons = [str(r) for r in (value.reasons or []) if str(r).strip()]

        if value.passed:
            return ReviewVerdict(
                passed=True,
                reviewer=self.name,
                notes=tuple(notes or ["critique found the artifact on intent"]),
                reasons=(),
            )

        if not notes:
            # Keep the invariant: a failure must carry an actionable note.
            notes = [
                "the critique rejected this render without naming a concrete "
                "revision; an operator should inspect the artifact directly"
            ]

        structured = {
            "action": value.action,
            "lighting": value.lighting,
            "style_grade": value.style_grade,
            "camera_framing": value.camera_framing,
            "camera_movement": value.camera_movement,
            "narrative_intent": value.narrative_intent,
            "duration_seconds": value.duration_seconds,
            "overrides": dict(value.overrides or {}),
        }
        return ReviewVerdict(
            passed=False,
            reviewer=self.name,
            reasons=tuple(reasons or ("critique_failed",)),
            notes=tuple(notes),
            structured=structured,
        )

    def _build_prompt(
        self,
        shot_spec: Any,
        compiled: Any,
        artifacts: Sequence[str],
        observations: Sequence[Mapping[str, Any]],
    ) -> str:
        spec = getattr(shot_spec, "model_dump", None)
        spec_json = json.dumps(spec(), indent=2) if callable(spec) else str(shot_spec)
        prompt_text = str(getattr(compiled, "prompt", "") or "(no compiled prompt)")
        frames = json.dumps(list(observations)[: self.sample_limit], indent=2)
        return f"""You are a video QC reviewer. Judge whether the rendered clip satisfies the shot's intent.

SHOT SPEC (the intent that must be met):
{spec_json}

PROMPT SENT TO THE RENDERER (what was actually asked for):
{prompt_text}

SAMPLED FRAME OBSERVATIONS (from the render):
{frames}

ARTIFACT PATHS: {", ".join(artifacts) or "(none)"}

Judge ONLY against the shot's intent. Rules:
- passed=false requires at least one concrete, actionable note.
- reasons: short machine-readable codes (e.g. 'subject_absent', 'wrong_framing', 'text_visible').
- Set a revision field ONLY when that specific element is wrong; leave the rest null.
- overrides may only use: width, height, frames, fps, steps, loras. Never invent a key.
- Do not ask for readable text or logos to be added; they belong in the negative prompt.
"""