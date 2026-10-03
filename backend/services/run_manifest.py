"""Run manifest — the auditable, diffable record of one script-to-video run.

PROMPT-MACHINE-DIRECTIVE v1.2 requires that a run be reproducible and
auditable: the ShotSpec, the template, the overrides, the routing decisions,
the render job ids, and the artifact paths all persist per run. This module
is that record, and nothing else writes it.

Why a manifest and not just log lines
-------------------------------------
A log line answers "what happened"; a manifest answers "what would I have to
send to get the same thing again". Two runs of the same script with the same
template must produce the same prompt digest and the same seed, so a diff
between two manifests is a real diff of *inputs* rather than of wall-clock
noise. That is why:

* the compiler's ``prompt_sha256_16`` and derived ``seed`` are recorded, not
  the prompt prose itself — a digest diffs cleanly and leaks nothing;
* every wall-clock field is confined to :data:`VOLATILE_PATHS` and is excluded
  from :func:`diff_manifests` by default, so "did anything change?" is a
  one-line question with a stable answer;
* job ids and artifact paths *are* recorded (the directive requires them) but
  live under volatile keys, because a re-render legitimately produces new ones.

Deliberate non-goals
--------------------
No secrets, ever. The manifest records which provider served a request and
what it cost in tokens, never a key. :func:`assert_no_secrets` enforces that
mechanically on every write, so a future field cannot quietly introduce one.

Determinism: :func:`build_manifest` and :func:`diff_manifests` are pure. The
only clock and randomness in a manifest come from the caller's values.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

__all__ = [
    "MANIFEST_VERSION",
    "VOLATILE_PATHS",
    "SECRET_PATTERN",
    "ManifestError",
    "ShotAttempt",
    "ShotRunRecord",
    "RunManifest",
    "diff_manifests",
    "manifest_fingerprint",
    "assert_no_secrets",
]

#: Bumped when a field is removed or its meaning changes. Additive fields do
#: not bump it, so an older manifest still diffs against a newer run.
MANIFEST_VERSION = 1

#: Dotted paths whose values change between two otherwise-identical runs.
#: ``diff_manifests`` skips these unless ``include_volatile=True``.
#:
#: Artifact paths are volatile because the renderer stamps a timestamp into
#: every filename, so the *same* run re-rendered yields a different path. The
#: prompt digest and seed are deliberately NOT here: those are what "same
#: input" means, and if they move the run genuinely differs.
VOLATILE_PATHS: Tuple[str, ...] = (
    "run_id",
    "created_at",
    "finished_at",
    "duration_s",
    "router.metrics.latency_ms",
    "router.last.latency_ms",
    "shots[].last_artifact",
    "shots[].attempts[].job_id",
    "shots[].attempts[].duration_s",
    "shots[].attempts[].artifacts[]",
    "shots[].attempts[].artifacts_native[]",
    "summary.artifacts[]",
)

#: Shape of a credential that must never reach a manifest file.
SECRET_PATTERN = re.compile(
    r"(?:sk-[A-Za-z0-9]{16,}|nvapi-[A-Za-z0-9_-]{16,}|"
    r"Bearer\s+[A-Za-z0-9._-]{20,}|"
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})"
)

#: Keys whose *values* are legal even though they look credential-shaped.
_SECRET_KEY_ALLOWLIST = frozenset({"secret_present", "has_cloud_key", "consent"})


class ManifestError(ValueError):
    """A manifest could not be built, serialized, or trusted."""


# ---------------------------------------------------------------------------
# Secret hygiene
# ---------------------------------------------------------------------------


def assert_no_secrets(payload: Any, *, path: str = "$") -> None:
    """Raise if a credential-shaped string appears anywhere in *payload*.

    Key *names* are allowed to mention credentials (``has_cloud_key``); key
    *values* are not. The walk recurses into mappings and sequences, so a
    nested dict or an embedded blob is caught the same as a top-level field.
    """
    if isinstance(payload, str):
        if SECRET_PATTERN.search(payload):
            raise ManifestError(
                f"{path}: value looks like a credential; manifests must never "
                f"contain secrets (record that a key was present, not the key)"
            )
        return
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if key in _SECRET_KEY_ALLOWLIST:
                continue
            assert_no_secrets(key, path=f"{path}.{key}")
            assert_no_secrets(value, path=f"{path}.{key}")
        return
    if isinstance(payload, (list, tuple)):
        for i, item in enumerate(payload):
            assert_no_secrets(item, path=f"{path}[{i}]")


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShotAttempt:
    """One render attempt for one shot: the compile, the job, and the verdict.

    A shot that passes on the first try has exactly one attempt. A shot that
    fails review and re-renders has one attempt per pass, each carrying the
    revision notes that motivated it — so the manifest explains *why* there
    were three renders, not merely that there were.

    The review verdict is recorded in full (``reviewer``, ``passed``,
    ``reasons``, ``notes``) rather than reduced to a boolean. "It passed" and
    "it passed *because the frame probe found the clip non-frozen*" are
    different facts, and only the second one tells an operator whether the
    thing that approved the shot was actually looking at it.
    """

    attempt: int
    job_id: str = ""
    status: str = "pending"
    artifacts: Tuple[str, ...] = ()
    artifacts_native: Tuple[str, ...] = ()
    passed: Optional[bool] = None
    review_notes: Tuple[str, ...] = ()
    review_reasons: Tuple[str, ...] = ()
    reviewer: str = ""
    revision_applied: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    prompt_sha256_16: str = ""
    seed: int = -1
    template_id: str = ""
    overrides: Dict[str, Any] = field(default_factory=dict)
    duration_s: float = 0.0

    @property
    def review(self) -> Dict[str, Any]:
        """The verdict as one record, or None if review never ran."""
        if self.reviewer == "":
            return None
        return {
            "reviewer": self.reviewer,
            "passed": self.passed,
            "reasons": list(self.review_reasons),
            "notes": list(self.review_notes),
        }

    def as_dict(self) -> Dict[str, Any]:
        return {
            "attempt": self.attempt,
            "job_id": self.job_id,
            "status": self.status,
            "artifacts": list(self.artifacts),
            "artifacts_native": list(self.artifacts_native),
            "passed": self.passed,
            "review": self.review,
            "review_notes": list(self.review_notes),
            "review_reasons": list(self.review_reasons),
            "reviewer": self.reviewer,
            "revision_applied": dict(self.revision_applied),
            "error": self.error,
            "prompt_sha256_16": self.prompt_sha256_16,
            "seed": self.seed,
            "template_id": self.template_id,
            "overrides": dict(self.overrides),
            "duration_s": round(float(self.duration_s), 3),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any], *, attempt: int = 1) -> "ShotAttempt":
        return cls(
            attempt=int(raw.get("attempt", attempt)),
            job_id=str(raw.get("job_id", "")),
            status=str(raw.get("status", "pending")),
            artifacts=tuple(raw.get("artifacts", ()) or ()),
            artifacts_native=tuple(raw.get("artifacts_native", ()) or ()),
            passed=raw.get("passed"),
            review_notes=tuple(raw.get("review_notes", ()) or ()),
            review_reasons=tuple(raw.get("review_reasons", ()) or ()),
            reviewer=str(raw.get("reviewer", "")),
            revision_applied=dict(raw.get("revision_applied", {}) or {}),
            error=str(raw.get("error", "")),
            prompt_sha256_16=str(raw.get("prompt_sha256_16", "")),
            seed=int(raw.get("seed", -1)),
            template_id=str(raw.get("template_id", "")),
            overrides=dict(raw.get("overrides", {}) or {}),
            duration_s=float(raw.get("duration_s", 0.0) or 0.0),
        )


@dataclass(frozen=True)
class ShotRunRecord:
    """Everything that happened to one shot across the run."""

    shot_id: str
    sequence_index: int = 0
    version: int = 1
    final_status: str = "pending"  # passed | needs_operator | error
    attempts: List[ShotAttempt] = field(default_factory=list)
    shot_spec: Dict[str, Any] = field(default_factory=dict)
    compile_manifest: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    @property
    def attempts_used(self) -> int:
        return len(self.attempts)

    @property
    def last_artifact(self) -> str:
        """The artifact the operator should look at (latest passing, else latest)."""
        for attempt in reversed(self.attempts):
            if attempt.passed and attempt.artifacts:
                return attempt.artifacts[0]
        for attempt in reversed(self.attempts):
            if attempt.artifacts:
                return attempt.artifacts[0]
        return ""

    @property
    def passed(self) -> bool:
        return self.final_status == "passed"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "sequence_index": self.sequence_index,
            "version": self.version,
            "final_status": self.final_status,
            "attempts_used": self.attempts_used,
            "error": self.error,
            "shot_spec": dict(self.shot_spec),
            "compile": dict(self.compile_manifest),
            "last_artifact": self.last_artifact,
            "attempts": [a.as_dict() for a in self.attempts],
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ShotRunRecord":
        return cls(
            shot_id=str(raw.get("shot_id", "")),
            sequence_index=int(raw.get("sequence_index", 0)),
            version=int(raw.get("version", 1)),
            final_status=str(raw.get("final_status", "pending")),
            attempts=[
                ShotAttempt.from_dict(a, attempt=i + 1)
                for i, a in enumerate(raw.get("attempts", ()) or ())
            ],
            shot_spec=dict(raw.get("shot_spec", {}) or {}),
            compile_manifest=dict(raw.get("compile", {}) or {}),
            error=str(raw.get("error", "")),
        )


@dataclass(frozen=True)
class RunManifest:
    """The complete record of one run: input, decisions, renders, artifacts."""

    run_id: str
    shots: List[ShotRunRecord] = field(default_factory=list)
    script_path: str = ""
    script_sha256: str = ""
    created_at: str = ""
    finished_at: str = ""
    duration_s: float = 0.0
    router: Dict[str, Any] = field(default_factory=dict)
    renderer: Dict[str, Any] = field(default_factory=dict)
    review: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # completed | needs_operator | failed
    manifest_version: int = MANIFEST_VERSION

    # -- summaries -------------------------------------------------------

    @property
    def shot_count(self) -> int:
        return len(self.shots)

    @property
    def passed_shots(self) -> List[str]:
        return [s.shot_id for s in self.shots if s.final_status == "passed"]

    @property
    def operator_shots(self) -> List[str]:
        return [s.shot_id for s in self.shots if s.final_status == "needs_operator"]

    @property
    def artifacts(self) -> List[str]:
        """One artifact per passing shot, in shot order."""
        return [s.last_artifact for s in self.shots if s.passed and s.last_artifact]

    @property
    def total_attempts(self) -> int:
        return sum(s.attempts_used for s in self.shots)

    def retry_report(self) -> Dict[str, Any]:
        """Retries consumed per shot — the loop's budget, spent or not."""
        return {
            s.shot_id: {
                "attempts": s.attempts_used,
                "retries": max(0, s.attempts_used - 1),
                "final_status": s.final_status,
            }
            for s in self.shots
        }

    # -- serialization ---------------------------------------------------

    def as_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "run_id": self.run_id,
            "status": self.status,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "duration_s": round(float(self.duration_s), 3),
            "script": {"path": self.script_path, "sha256": self.script_sha256},
            "summary": {
                "shots": self.shot_count,
                "passed": len(self.passed_shots),
                "needs_operator": len(self.operator_shots),
                "total_attempts": self.total_attempts,
                "artifacts": self.artifacts,
            },
            "router": dict(self.router),
            "renderer": dict(self.renderer),
            "review": dict(self.review),
            "shots": [s.as_dict() for s in self.shots],
        }

    def to_json(self, *, indent: int = 2) -> str:
        """Canonical JSON: sorted keys, stable separators, trailing newline."""
        assert_no_secrets(self.as_dict())
        return (
            json.dumps(self.as_dict(), indent=indent, sort_keys=True, ensure_ascii=False)
            + "\n"
        )

    def save(self, path: Any) -> Path:
        """Write the manifest to *path*, refusing renderer-owned directories.

        Uses the same guard cleanup scripts use: ``D:\\Wan2GP`` and
        ``/mnt/d/wan2gp`` are one directory holding the model and output
        stores, and a manifest dropped there would be indistinguishable from
        debris in a directory the wan2gp-desktop launcher manages.
        """
        from core.path_guard import assert_deletable

        target = Path(path)
        parent = target.parent if str(target.parent) else target
        assert_deletable(parent)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_json(), encoding="utf-8")
        return target

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "RunManifest":
        version = int(raw.get("manifest_version", MANIFEST_VERSION))
        if version > MANIFEST_VERSION:
            raise ManifestError(
                f"manifest version {version} is newer than this code understands "
                f"({MANIFEST_VERSION}); upgrade before reading it"
            )
        script = raw.get("script", {}) or {}
        return cls(
            run_id=str(raw.get("run_id", "")),
            shots=[ShotRunRecord.from_dict(s) for s in raw.get("shots", ()) or ()],
            script_path=str(script.get("path", "")),
            script_sha256=str(script.get("sha256", "")),
            created_at=str(raw.get("created_at", "")),
            finished_at=str(raw.get("finished_at", "")),
            duration_s=float(raw.get("duration_s", 0.0) or 0.0),
            router=dict(raw.get("router", {}) or {}),
            renderer=dict(raw.get("renderer", {}) or {}),
            review=dict(raw.get("review", {}) or {}),
            status=str(raw.get("status", "pending")),
            manifest_version=version,
        )

    @classmethod
    def load(cls, path: Any) -> "RunManifest":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            raise ManifestError(f"{path}: manifest is not a JSON object")
        return cls.from_dict(raw)


# ---------------------------------------------------------------------------
# Diffing
# ---------------------------------------------------------------------------


def _flatten(payload: Any, prefix: str = "") -> Dict[str, Any]:
    """Flatten nested mappings to ``a.b.c`` -> scalar. Lists keep their index."""
    out: Dict[str, Any] = {}
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            out.update(_flatten(value, path))
    elif isinstance(payload, list):
        for i, item in enumerate(payload):
            out.update(_flatten(item, f"{prefix}[{i}]"))
    else:
        out[prefix] = payload
    return out


def _is_volatile(path: str) -> bool:
    """True when *path* matches a known-volatile pattern at any list depth.

    Patterns use ``[]`` to mean "any index", so ``shots[].attempts[].job_id``
    matches ``shots[3].attempts[0].job_id``.
    """
    for pattern in VOLATILE_PATHS:
        regex = _VOLATILE_CACHE.get(pattern)
        if regex is None:
            regex = _VOLATILE_CACHE[pattern] = re.compile(
                "^" + re.escape(pattern).replace(re.escape("[]"), r"\[\d+\]") + "$"
            )
        if regex.match(path):
            return True
    return False


_VOLATILE_CACHE: Dict[str, "re.Pattern[str]"] = {}


def diff_manifests(
    left: Any,
    right: Any,
    *,
    include_volatile: bool = False,
) -> List[Dict[str, Any]]:
    """Field-level diff of two manifests (RunManifests or mappings).

    Returns a sorted list of ``{"path", "left", "right"}`` entries. Volatile
    fields are excluded by default, so an unchanged input that was re-rendered
    diffs to ``[]`` while a changed prompt digest shows up immediately.
    """
    left_dict = left.as_dict() if isinstance(left, RunManifest) else left
    right_dict = right.as_dict() if isinstance(right, RunManifest) else right
    if not isinstance(left_dict, Mapping) or not isinstance(right_dict, Mapping):
        raise ManifestError("diff_manifests expects RunManifest objects or mappings")

    flat_left = _flatten(dict(left_dict))
    flat_right = _flatten(dict(right_dict))

    entries: List[Dict[str, Any]] = []
    for path in sorted(set(flat_left) | set(flat_right)):
        if not include_volatile and _is_volatile(path):
            continue
        lhs = flat_left.get(path)
        rhs = flat_right.get(path)
        if lhs != rhs:
            entries.append({"path": path, "left": lhs, "right": rhs})
    return entries


def manifest_fingerprint(manifest: Any, *, include_volatile: bool = False) -> str:
    """Stable sha256 over the manifest's non-volatile content.

    Two runs of the same script against the same template share a fingerprint;
    changing one character of the prompt changes it. This is the single-value
    answer to "is this the same run?".
    """
    data = manifest.as_dict() if isinstance(manifest, RunManifest) else manifest
    flat = _flatten(dict(data))
    stable = {
        path: value
        for path, value in flat.items()
        if include_volatile or not _is_volatile(path)
    }
    blob = json.dumps(stable, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()