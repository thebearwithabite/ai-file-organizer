"""Review loop — bounded, deterministic QC over rendered artifacts.

PROMPT-MACHINE-DIRECTIVE v1.2, Phase 4: after a shot renders, a review pass
judges the artifact against the ShotSpec's intent and returns pass/fail plus
concrete revision notes. On a fail the shot may be re-compiled and re-rendered
**at most twice** before it is surfaced to the operator.

The retry budget is the whole point of this module, so it is stated three
ways, deliberately:

1. :data:`MAX_RETRIES` is a module constant. The loop reads it once, at
   construction, and clamps whatever the caller passes to
   ``0 <= retries <= MAX_RETRIES``. A caller cannot buy more iterations by
   passing a bigger number, which is what makes "no infinite retry" a
   property of the code rather than a promise in a docstring.
2. Every attempt is recorded in :class:`AttemptRecord`, including the one that
   exhausts the budget, so a caller can assert on the count after the fact
   rather than trusting the loop to have stopped.
3. :meth:`ReviewLoop.run` is a ``for`` over a precomputed range, never a
   ``while``. There is no exit condition that a failing reviewer can defeat.

Determinism
-----------
Deterministic means: the same artifacts and the same reviewer produce the same
verdicts and the same revisions, and nothing in this module consults a clock,
the network, or an RNG. Reviewers are injected, so a test can drive any
verdict sequence. :func:`plan_revisions` is a pure function of the verdict
sequence.

The LLM-backed reviewer is the one exception by nature — a model judges. It is
kept deterministic *in shape* instead: its structured output is validated
against a Pydantic schema, and a reviewer that cannot be reached fails the
shot rather than passing it silently. Silence is not a pass.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Sequence, Tuple

__all__ = [
    "MAX_RETRIES",
    "ReviewVerdict",
    "AttemptRecord",
    "ReviewOutcome",
    "Reviewer",
    "Revision",
    "ReviewLoop",
    "plan_revisions",
    "plan_one_revision",
    "RevisionBudgetExhausted",
]

logger = logging.getLogger(__name__)

#: Hard ceiling on automated re-compile + re-render retries per shot. The
#: directive allows at most 2; the loop refuses anything above this.
MAX_RETRIES = 2


class RevisionBudgetExhausted(RuntimeError):
    """A caller tried to construct a loop with a larger retry budget."""


# ---------------------------------------------------------------------------
# Reviewer contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReviewVerdict:
    """One reviewer's judgement of one artifact.

    ``passed`` is the gate. ``notes`` are the concrete revision instructions
    handed to the recompiler — free text a human can act on, never a bare
    "retry". ``reasons`` are the machine-readable failure codes the loop
    branches on, so a reviewer that cannot name a reason cannot silently
    trigger an expensive re-render.
    """

    passed: bool
    reviewer: str = ""
    notes: Tuple[str, ...] = ()
    reasons: Tuple[str, ...] = ()
    score: Optional[float] = None
    #: Machine-readable revision fields, if this reviewer produces any. Keys
    #: outside :data:`REVISION_FIELDS` (plus ``overrides``) are ignored by
    #: :func:`plan_revisions`, so a reviewer cannot widen its own authority by
    #: inventing a field name.
    structured: Optional[Mapping[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.reviewer:
            raise ValueError("ReviewVerdict.reviewer must name the reviewer")
        if not self.passed and not self.notes:
            # A failure with no instruction cannot drive a revision, so the
            # loop would burn a re-render producing the identical artifact.
            raise ValueError(
                "a failing ReviewVerdict must carry at least one concrete note; "
                "an unnamed failure cannot be acted on"
            )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "reviewer": self.reviewer,
            "notes": list(self.notes),
            "reasons": list(self.reasons),
            "score": self.score,
            "structured": dict(self.structured) if self.structured else None,
        }


class Reviewer(Protocol):
    """Judges one rendered artifact against one ShotSpec's intent."""

    name: str

    def review(
        self,
        *,
        shot_spec: Any,
        compiled: Any,
        artifacts: Sequence[str],
        attempt: int,
    ) -> ReviewVerdict:
        ...


# ---------------------------------------------------------------------------
# Revisions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Revision:
    """What to change about a shot before re-rendering it.

    Deliberately narrow. A revision is a *bounded edit to the ShotSpec*, not a
    free-text instruction appended to the prompt: appending notes to a prompt
    is how a review loop silently turns into a second director. The fields
    below are the ones a reviewer is allowed to speak to.
    """

    notes: Tuple[str, ...] = ()
    action: Optional[str] = None
    lighting: Optional[str] = None
    style_grade: Optional[str] = None
    camera_framing: Optional[str] = None
    camera_movement: Optional[str] = None
    narrative_intent: Optional[str] = None
    duration_seconds: Optional[float] = None
    #: Render settings the reviewer may adjust. Keys are restricted to the six
    #: permitted overrides by the compiler, so a reviewer cannot smuggle a
    #: generation setting past the template discipline.
    overrides: Dict[str, Any] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not any(
            (
                self.action,
                self.lighting,
                self.style_grade,
                self.camera_framing,
                self.camera_movement,
                self.narrative_intent,
                self.duration_seconds,
                self.overrides,
            )
        )

    def as_dict(self) -> Dict[str, Any]:
        """Only the fields that were actually set, so a manifest stays readable."""
        out: Dict[str, Any] = {"notes": list(self.notes)}
        for name in (
            "action",
            "lighting",
            "style_grade",
            "camera_framing",
            "camera_movement",
            "narrative_intent",
            "duration_seconds",
        ):
            value = getattr(self, name)
            if value is not None:
                out[name] = value
        if self.overrides:
            out["overrides"] = dict(self.overrides)
        return out

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "Revision":
        return cls(
            notes=tuple(raw.get("notes", ()) or ()),
            action=raw.get("action"),
            lighting=raw.get("lighting"),
            style_grade=raw.get("style_grade"),
            camera_framing=raw.get("camera_framing"),
            camera_movement=raw.get("camera_movement"),
            narrative_intent=raw.get("narrative_intent"),
            duration_seconds=(
                float(raw["duration_seconds"]) if raw.get("duration_seconds") is not None else None
            ),
            overrides=dict(raw.get("overrides", {}) or {}),
        )

    def apply_to(self, spec: Any) -> Any:
        """Return a new ShotSpec with this revision applied. Pure.

        Uses ``model_copy(update=...)`` on a *validated* spec and re-validates,
        so a revision that would produce an invalid shot raises rather than
        poisoning the next compile.
        """
        from backend.services.shot_spec import validate_shot_spec

        data = spec.model_dump()
        if self.action is not None:
            data["action"] = self.action
        if self.lighting is not None:
            data["lighting"] = self.lighting
        if self.style_grade is not None:
            data["style_grade"] = self.style_grade
        if self.narrative_intent is not None:
            data["narrative_intent"] = self.narrative_intent
        if self.duration_seconds is not None:
            data["duration_seconds"] = self.duration_seconds
        camera = dict(data.get("camera") or {})
        if self.camera_framing is not None:
            camera["framing"] = self.camera_framing
        if self.camera_movement is not None:
            camera["movement"] = self.camera_movement
        if len(camera) != len(data.get("camera") or {}):
            data["camera"] = camera
        return validate_shot_spec(data, source="review_loop.revision")


#: Revision keys a reviewer may set, mapped to the ShotSpec path they write.
REVISION_FIELDS = (
    "action",
    "lighting",
    "style_grade",
    "camera_framing",
    "camera_movement",
    "narrative_intent",
    "duration_seconds",
)


def plan_revisions(
    verdicts: Sequence[ReviewVerdict],
    *,
    max_retries: int = MAX_RETRIES,
) -> List[Revision]:
    """Turn a verdict sequence into the revisions to attempt, in order.

    Pure, and the single place the retry budget is turned into a work list.
    A passing verdict ends the plan. A verdict that carries no actionable
    field ends it too — re-rendering an unmodified shot reproduces the same
    artifact and wastes the GPU, which is worse than surfacing to the
    operator immediately. Notes that name no settable field are preserved as
    notes so the operator still sees them.

    Length is at most ``max_retries``; the caller renders until the plan is
    exhausted or a shot passes.
    """
    from backend.services.prompt_compiler import ALLOWED_OVERRIDE_KEYS

    revisions: List[Revision] = []
    for verdict in verdicts:
        if verdict.passed or len(revisions) >= max(0, int(max_retries)):
            break
        revision = _revision_from_verdict(verdict, ALLOWED_OVERRIDE_KEYS)
        if revision is None or revision.is_empty():
            break
        revisions.append(revision)
    return revisions


def plan_one_revision(verdict: ReviewVerdict) -> Optional[Revision]:
    """The single revision *this* verdict calls for, or None.

    One verdict, one revision. The loop asks again after each subsequent
    failure, so a reviewer that keeps returning structured corrections gets the
    full retry budget rather than a single pre-computed plan.
    """
    from backend.services.prompt_compiler import ALLOWED_OVERRIDE_KEYS

    return _revision_from_verdict(verdict, ALLOWED_OVERRIDE_KEYS)


def _revision_from_verdict(
    verdict: ReviewVerdict, allowed_overrides: Sequence[str]
) -> Optional[Revision]:
    """Build a Revision from a verdict's structured fields, if it has any.

    A verdict produced by an LLM-backed reviewer arrives with a ``structured``
    mapping that may carry settable fields alongside the notes. Anything
    outside the allowed set is dropped rather than passed on, so a
    hallucinated override key dies here instead of at the compiler's boundary
    check.
    """
    payload = verdict.structured
    if not isinstance(payload, Mapping):
        return None

    fields: Dict[str, Any] = {}
    for name in REVISION_FIELDS:
        value = payload.get(name)
        if isinstance(value, str) and value.strip():
            fields[name] = value.strip()
        elif name == "duration_seconds":
            try:
                if payload.get(name) is not None:
                    number = float(payload[name])
                    if number > 0:
                        fields[name] = number
            except (TypeError, ValueError):
                pass

    overrides = payload.get("overrides")
    clean_overrides: Dict[str, Any] = {}
    if isinstance(overrides, Mapping):
        for key, value in overrides.items():
            if str(key) in allowed_overrides:
                clean_overrides[str(key)] = value

    if not fields and not clean_overrides:
        return None

    return Revision(
        notes=tuple(verdict.notes),
        overrides=clean_overrides,
        **fields,
    )


# ---------------------------------------------------------------------------
# Attempt/outcome records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttemptRecord:
    """One render + review cycle, recorded whether it passed or not.

    ``compiled`` is carried so the caller can record the prompt digest, seed,
    and template that produced *this* attempt — without it, a retried shot's
    manifest would show only the first compile's provenance and the audit
    trail would misattribute every later render.
    """

    attempt: int
    verdict: Optional[ReviewVerdict] = None
    artifacts: Tuple[str, ...] = ()
    job_id: str = ""
    status: str = "pending"
    revision: Optional[Revision] = None
    error: str = ""
    compiled: Any = None
    artifacts_native: Tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return bool(self.verdict and self.verdict.passed)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "attempt": self.attempt,
            "status": self.status,
            "job_id": self.job_id,
            "artifacts": list(self.artifacts),
            "artifacts_native": list(self.artifacts_native),
            "passed": self.passed,
            "error": self.error,
            "review": self.verdict.as_dict() if self.verdict else None,
            "revision": self.revision.as_dict() if self.revision else None,
        }


@dataclass(frozen=True)
class ReviewOutcome:
    """The result of reviewing one shot to exhaustion (or to a pass)."""

    shot_id: str
    passed: bool
    attempts: List[AttemptRecord] = field(default_factory=list)
    exhausted: bool = False
    reason: str = ""

    @property
    def attempts_used(self) -> int:
        return len(self.attempts)

    @property
    def retries_used(self) -> int:
        return max(0, self.attempts_used - 1)

    @property
    def best_artifact(self) -> str:
        for record in reversed(self.attempts):
            if record.passed and record.artifacts:
                return record.artifacts[0]
        for record in reversed(self.attempts):
            if record.artifacts:
                return record.artifacts[0]
        return ""

    def notes(self) -> List[str]:
        """Every reviewer note across attempts, in order, de-duplicated."""
        out: List[str] = []
        for record in self.attempts:
            if record.verdict:
                out.extend(record.verdict.notes)
        seen: set = set()
        return [n for n in out if not (n in seen or seen.add(n))]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "passed": self.passed,
            "exhausted": self.exhausted,
            "reason": self.reason,
            "attempts_used": self.attempts_used,
            "retries_used": self.retries_used,
            "attempts": [a.as_dict() for a in self.attempts],
        }


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------


class ReviewLoop:
    """Run review attempts for one shot with a hard retry ceiling.

    ``render(shot_spec, revision) -> RenderOutcome`` is injected: it compiles
    the (possibly revised) shot and renders it, returning the artifacts and the
    renderer job id. Keeping that behind a callable is what lets the whole loop
    be tested against a mocked transport with no renderer running.
    """

    def __init__(
        self,
        reviewer: Reviewer,
        render: Callable[..., Any],
        *,
        max_retries: int = MAX_RETRIES,
        plan_revision: Callable[..., Optional[Revision]] = plan_one_revision,
    ) -> None:
        if int(max_retries) < 0:
            raise ValueError(f"max_retries must be >= 0, got {max_retries!r}")
        if int(max_retries) > MAX_RETRIES:
            raise RevisionBudgetExhausted(
                f"max_retries={max_retries} exceeds the hard ceiling of {MAX_RETRIES}. "
                f"The directive allows at most {MAX_RETRIES} automated retries per "
                f"shot; anything beyond that is an operator decision, not an "
                f"automated one."
            )
        self.reviewer = reviewer
        self.render = render
        self.max_retries = int(max_retries)
        self.plan_revision = plan_revision

    def run(self, shot_spec: Any) -> ReviewOutcome:
        """Review one shot until it passes, the budget runs out, or a
        revision stops being possible.

        The loop shape is ``for attempt_no in range(1, self.max_retries + 2)``
        — one initial render plus at most ``max_retries`` re-renders. A
        reviewer that fails forever therefore terminates after
        ``max_retries + 1`` attempts; that is asserted in the tests.
        """
        shot_id = getattr(shot_spec, "shot_id", "") or "unknown"
        records: List[AttemptRecord] = []
        current_spec = shot_spec
        revision: Optional[Revision] = None

        # +2: the first attempt plus max_retries retries.
        for attempt_no in range(1, self.max_retries + 2):
            logger.info(
                "review loop: %s attempt %d/%d", shot_id, attempt_no, self.max_retries + 1
            )
            try:
                rendered = self.render(current_spec, revision)
            except Exception as exc:
                records.append(
                    AttemptRecord(
                        attempt=attempt_no,
                        status="render_error",
                        revision=revision,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                # A render error is not a review failure, so it is surfaced
                # immediately: retrying a transport error just burns the
                # budget without ever producing an artifact to judge.
                return ReviewOutcome(
                    shot_id=shot_id,
                    passed=False,
                    attempts=records,
                    exhausted=False,
                    reason=f"render failed on attempt {attempt_no}: {exc}",
                )

            artifacts = tuple(getattr(rendered, "artifacts", ()) or ())
            job_id = str(getattr(rendered, "job_id", "") or "")
            compiled = getattr(rendered, "compiled", None)

            try:
                verdict = self.reviewer.review(
                    shot_spec=current_spec,
                    compiled=compiled,
                    artifacts=artifacts,
                    attempt=attempt_no,
                )
            except Exception as exc:
                # An unreachable reviewer fails the shot. It does not pass it:
                # "no critic" must never mean "approved".
                records.append(
                    AttemptRecord(
                        attempt=attempt_no,
                        status="review_error",
                        artifacts=artifacts,
                        job_id=job_id,
                        revision=revision,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                return ReviewOutcome(
                    shot_id=shot_id,
                    passed=False,
                    attempts=records,
                    exhausted=False,
                    reason=f"reviewer {self.reviewer.name!r} failed on attempt {attempt_no}: {exc}",
                )

            records.append(
                AttemptRecord(
                    attempt=attempt_no,
                    verdict=verdict,
                    artifacts=artifacts,
                    job_id=job_id,
                    status="completed",
                    revision=revision,
                    compiled=compiled,
                    artifacts_native=tuple(
                        getattr(rendered, "artifacts_native", ()) or ()
                    ),
                )
            )

            if verdict.passed:
                return ReviewOutcome(
                    shot_id=shot_id, passed=True, attempts=records, exhausted=False
                )

            if attempt_no > self.max_retries:
                break  # budget spent; fall through to surface

            # Each failing attempt plans its own revision from its own
            # verdict. Planning once up front from a single verdict would
            # yield one revision and cap the loop at one retry, which is the
            # bug the (max_retries - 1) attempt count used to hide.
            next_revision = self.plan_revision(verdict)

            if next_revision is None or next_revision.is_empty():
                return ReviewOutcome(
                    shot_id=shot_id,
                    passed=False,
                    attempts=records,
                    exhausted=False,
                    reason=(
                        f"review failed with no actionable revision "
                        f"({', '.join(verdict.reasons) or 'no reason code'}); "
                        f"surfacing to the operator instead of re-rendering an "
                        f"unmodified shot"
                    ),
                )

            revision = next_revision
            try:
                current_spec = revision.apply_to(current_spec)
            except Exception as exc:
                failed = records[-1]
                records[-1] = AttemptRecord(
                    attempt=failed.attempt,
                    verdict=failed.verdict,
                    artifacts=failed.artifacts,
                    job_id=failed.job_id,
                    status="revision_rejected",
                    revision=revision,
                    compiled=failed.compiled,
                    artifacts_native=failed.artifacts_native,
                    error=f"revision would produce an invalid ShotSpec: {exc}",
                )
                return ReviewOutcome(
                    shot_id=shot_id,
                    passed=False,
                    attempts=records,
                    exhausted=False,
                    reason=f"revision rejected by the schema: {exc}",
                )

        reasons: List[str] = []
        for record in records:
            if record.verdict and not record.verdict.passed:
                reasons.extend(record.verdict.reasons or record.verdict.notes)
        return ReviewOutcome(
            shot_id=shot_id,
            passed=False,
            attempts=records,
            exhausted=True,
            reason=(
                f"exhausted the {self.max_retries}-retry budget without a passing "
                f"review; operator decision required"
                + (f" (last: {reasons[-1]})" if reasons else "")
            ),
        )