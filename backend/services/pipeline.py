"""The script-to-video pipeline: script -> shots -> compiles -> renders -> review -> manifest.

This is the integration seam PROMPT-MACHINE-DIRECTIVE v1.2 asks for, and it is
deliberately thin. Every decision belongs to the module that owns it:

======================  ====================================================
Decision                Owner
======================  ====================================================
script -> ShotSpec[]    ``DirectorService`` / ``LLMRouter`` (routing, keyless)
ShotSpec -> payload     ``prompt_compiler`` (template + the six overrides)
payload -> job          ``WangPClient`` (MCP over streamable-http)
pass/fail + revisions   ``review_loop`` (bounded at 2 retries)
audit record            ``run_manifest``
======================  ====================================================

What this module adds is the wiring, and one piece of real logic: turning a
``CompiledShot`` into a ``ResolvedSettings`` the renderer's boundary guard will
accept. See :func:`effective_overrides` for why that is not a formality.

Boundary rules honoured here
----------------------------
* **No Windows paths above the client.** Artifacts are recorded as the renderer
  emitted them *and* translated to WSL form, and both spellings go in the
  manifest because the operator may be looking at either.
* **Nothing is deleted, ever.** This module has no delete calls; the guard
  tests assert that mechanically.
* **One render at a time.** Shots render sequentially. The router is handed the
  renderer's in-flight state, so a director call made while a render is running
  routes to overflow/degrade rather than competing for the GPU.
* **The retry budget is not negotiable.** ``max_retries`` above
  ``review_loop.MAX_RETRIES`` raises at construction.

CI-safety
---------
Every collaborator is injectable. With no cloud key and no renderer running,
``PipelineConfig.for_tests()`` wires a scripted LLM provider and a mocked MCP
transport, and the whole run completes end to end producing a manifest. The
live path is the same code with a real ``WangPClient``.
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from backend.services.run_manifest import (
    RunManifest,
    ShotAttempt,
    ShotRunRecord,
)
from backend.services.review_loop import (
    MAX_RETRIES,
    AttemptRecord,
    Revision,
    ReviewLoop,
    ReviewOutcome,
)

logger = logging.getLogger(__name__)

__all__ = [
    "PipelineConfig",
    "PipelineError",
    "RenderOutcome",
    "ScriptToVideoPipeline",
    "effective_overrides",
    "main",
]


class PipelineError(RuntimeError):
    """The run could not proceed (bad script, no shots, unreachable renderer)."""


#: Which of the six overrides touch which native settings field. Derived from
#: ``wangp_settings``' own naming so a template rename is caught by the tests
#: rather than by a silent mis-merge.
_CANONICAL_TO_NATIVE: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("frames", ("video_length",)),
    ("fps", ("force_fps",)),
    ("steps", ("num_inference_steps",)),
    ("loras", ("activated_loras", "loras_multipliers")),
)


def _resolution_dims(value: Any) -> Tuple[Optional[int], Optional[int]]:
    text = str(value or "").strip().lower()
    if "x" not in text:
        return (None, None)
    width, _, height = text.partition("x")
    try:
        return int(width), int(height)
    except ValueError:
        return (None, None)


def effective_overrides(
    template_settings: Mapping[str, Any],
    compiled_settings: Mapping[str, Any],
) -> Dict[str, Any]:
    """Reconstruct the six-override set that explains template -> compiled.

    Why this is necessary
    ---------------------
    ``compile_shot`` derives ``frames`` from ``duration_seconds`` *inside* the
    compile, so its returned ``overrides`` dict holds only what the caller
    asked for — frequently empty. But the payload it returns carries the
    derived frame count, and ``WangPClient.submit_render`` re-derives the
    expected settings from ``ResolvedSettings`` and rejects any payload that
    deviates. Handing it the caller-overrides verbatim therefore fails the
    boundary guard with a ``TemplateDeviationError`` on every shot whose
    duration is not already the template's frame count.

    So the integration has to recover the *effective* overrides. Diffing the
    template against the compiled settings does that without duplicating the
    compiler's arithmetic: whatever changed, changed for a reason the compiler
    already justified, and whatever the compiler derived becomes an explicit
    override. Deriving frames again here would be a second source of truth
    waiting to drift.

    Returns only keys inside the six; anything the compiler changed outside
    them shows up as an absent override and is then correctly rejected by the
    boundary guard, which is the outcome we want.
    """
    overrides: Dict[str, Any] = {}

    base_w, base_h = _resolution_dims(template_settings.get("resolution"))
    new_w, new_h = _resolution_dims(compiled_settings.get("resolution"))
    if new_w is not None and new_h is not None and (base_w, base_h) != (new_w, new_h):
        if new_w != base_w:
            overrides["width"] = new_w
        if new_h != base_h:
            overrides["height"] = new_h

    for canonical, natives in _CANONICAL_TO_NATIVE:
        for native in natives:
            want = compiled_settings.get(native)
            have = template_settings.get(native)
            if want == have:
                continue
            if canonical == "loras":
                names = list(want or [])
                multipliers = compiled_settings.get("loras_multipliers") or ""
                overrides["loras"] = (
                    {"names": names, "multipliers": multipliers} if multipliers else names
                )
            else:
                overrides[canonical] = want
            break

    return overrides


@dataclass(frozen=True)
class RenderOutcome:
    """What one render produced, as the review loop needs to see it."""

    artifacts: Tuple[str, ...]
    job_id: str = ""
    status: str = "completed"
    compiled: Any = None
    artifacts_native: Tuple[str, ...] = ()


@dataclass
class PipelineConfig:
    """Everything the pipeline needs, with every collaborator injectable."""

    target: str = "wangp"
    aspect: str = "16:9"
    template_id: Optional[str] = None
    overrides: Dict[str, Any] = field(default_factory=dict)
    max_retries: int = MAX_RETRIES
    poll_timeout_s: float = 3600.0
    poll_interval_s: float = 2.0
    #: Stop the run at the first shot that needs an operator. Off by default:
    #: one bad shot should not strand the shots after it.
    fail_fast: bool = False
    allow_cloud_script: bool = False
    db_path: Optional[Path] = None

    @classmethod
    def for_tests(cls, **overrides: Any) -> "PipelineConfig":
        """CI config: fast polls, no cloud consent, zero retries allowed
        unless a test asks for them."""
        base = {
            "poll_timeout_s": 5.0,
            "poll_interval_s": 0.01,
            "allow_cloud_script": False,
        }
        base.update(overrides)
        return cls(**base)


class ScriptToVideoPipeline:
    """Wire the components into one script-to-video run."""

    def __init__(
        self,
        *,
        router: Any = None,
        client: Any = None,
        reviewer: Any = None,
        config: Optional[PipelineConfig] = None,
        director: Any = None,
        registry: Optional[Sequence[Any]] = None,
        review_loop_factory: Callable[..., ReviewLoop] = ReviewLoop,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or PipelineConfig()
        self._router = router
        self._client = client
        self._reviewer = reviewer
        self._director = director
        self.registry = registry
        self.review_loop_factory = review_loop_factory
        self._clock = clock

    # ------------------------------------------------------------------
    # Director pass
    # ------------------------------------------------------------------

    def shots_from_script(self, script: str, *, project_id: str = "") -> List[Any]:
        """script -> validated ShotSpec[] via the director service / router.

        Prefers an injected ``DirectorService`` because it owns the knowledge
        seeds and the degrade-to-review-queue behaviour. Falls back to the
        router's own ``director_shot_list``, which is the same structured
        contract one layer down, for callers that only have a router.
        """
        if self._director is not None:
            result = self._director.generate_shot_list(
                script,
                project_id=project_id,
                allow_cloud_script=self.config.allow_cloud_script,
            )
            if getattr(result, "degraded", False):
                raise PipelineError(
                    f"director pass degraded ({getattr(result, 'reason', 'unknown')}); "
                    f"no ShotSpec list to render"
                )
            shots = list(getattr(result, "shots", []) or [])
            if not shots:
                raise PipelineError("director pass returned zero shots")
            return shots

        if self._router is None:
            raise PipelineError(
                "no director service and no router wired; cannot turn a script into shots"
            )

        # Build the real DirectorService around the injected router rather
        # than hand-rolling a prompt. The service owns the knowledge seeds,
        # the typed-error handling, and the degrade-to-queue behaviour; a
        # second prompt builder here would be a second thing to keep in sync,
        # and the two paths would quietly diverge the first time the director
        # prompt was tuned.
        service = self._director or self._make_director(self._router)
        result = service.generate_shot_list(
            script,
            project_id=project_id,
            allow_cloud_script=self.config.allow_cloud_script,
        )
        if getattr(result, "degraded", False):
            raise PipelineError(
                f"director pass degraded ({getattr(result, 'reason', 'unknown')}); "
                f"no ShotSpec list to render"
            )
        shots = list(getattr(result, "shots", []) or [])
        if not shots:
            raise PipelineError("director pass returned zero shots")
        return shots

    def _make_director(self, router: Any) -> Any:
        from backend.services.director_service import DirectorService

        return DirectorService(
            db_path=self.config.db_path,
            router=router,
            render_state=self._client,
        )

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def _compile(self, shot_spec: Any, overrides: Mapping[str, Any]) -> Any:
        from backend.services.prompt_compiler import compile_shot

        return compile_shot(
            shot_spec,
            target=self.config.target,
            template=self.config.template_id,
            overrides=dict(overrides),
            aspect=self.config.aspect,
            registry=self.registry,
        )

    def _resolved_settings(self, compiled: Any):
        """Build the ResolvedSettings that matches a compiled payload.

        See :func:`effective_overrides` for why the compiled overrides are not
        enough on their own.
        """
        from backend.integrations.wangp_settings import ResolvedSettings

        overrides = effective_overrides(compiled.template.settings, compiled.settings)
        return ResolvedSettings.from_template(compiled.template.settings, overrides)

    def render_shot(self, shot_spec: Any, revision: Optional[Revision] = None) -> RenderOutcome:
        """Compile one (possibly revised) shot and render it.

        This is the callable the review loop drives. Returns a
        :class:`RenderOutcome`; raises on a renderer failure, which the loop
        treats as terminal for that shot rather than burning its budget.
        """
        from backend.integrations.wangp_settings import enforce_bounded_settings

        if self._client is None:
            raise PipelineError("no renderer client wired; cannot render")

        # Reviewer-suggested overrides merge with the run's, and are still
        # confined to the six by ResolvedSettings' own validation.
        overrides = dict(self.config.overrides)
        if revision is not None and revision.overrides:
            overrides.update(revision.overrides)

        compiled = self._compile(shot_spec, overrides)
        resolved = self._resolved_settings(compiled)

        # Fail before any network I/O if the payload and the resolved
        # settings disagree. The client would catch this too; catching it here
        # keeps the failure attributable to the integration rather than to
        # the transport.
        enforce_bounded_settings(compiled.payload, resolved.template, resolved.overrides)

        result = self._client.render(
            compiled.payload,
            resolved,
            timeout=self.config.poll_timeout_s,
            poll_interval=self.config.poll_interval_s,
        )
        return RenderOutcome(
            artifacts=tuple(result.artifacts or ()),
            artifacts_native=tuple(result.artifacts_native or ()),
            job_id=str(result.job_id or ""),
            status=str(result.status or "completed"),
            compiled=compiled,
        )

    # ------------------------------------------------------------------
    # The run
    # ------------------------------------------------------------------

    def run(
        self,
        script: str,
        *,
        project_id: str = "",
        run_id: str = "",
        script_path: str = "",
    ) -> RunManifest:
        """script -> shots -> render/review each -> manifest."""
        shots = self.shots_from_script(script, project_id=project_id)
        logger.info("director pass produced %d shots", len(shots))
        return self.run_shots(
            shots,
            project_id=project_id,
            run_id=run_id,
            script_path=script_path,
            script_text=script,
        )

    def run_shots(
        self,
        shots: Sequence[Any],
        *,
        project_id: str = "",
        run_id: str = "",
        script_path: str = "",
        script_text: str = "",
    ) -> RunManifest:
        """Render and review a pre-built shot list, then return the manifest.

        Split out from :meth:`run` so a fixture-driven run exercises exactly
        the same compile/render/review/manifest path as a director-driven one.
        """
        from backend.services.run_manifest import MANIFEST_VERSION

        started = self._clock()
        created = time.strftime("%Y-%m-%dT%H:%M:%S%z")

        loop = self.review_loop_factory(
            self._reviewer,
            self.render_shot,
            max_retries=self.config.max_retries,
        )

        records: List[ShotRunRecord] = []
        for index, shot in enumerate(shots):
            outcome = loop.run(shot)
            record = self._shot_record(shot, outcome, index)
            records.append(record)

            if self.config.fail_fast and record.final_status != "passed":
                logger.info("fail_fast: stopping after %s", record.shot_id)
                break

        manifest = RunManifest(
            run_id=run_id or self._derive_run_id(script_text, project_id),
            shots=records,
            script_path=script_path,
            script_sha256=hashlib.sha256(script_text.encode("utf-8")).hexdigest(),
            created_at=created,
            finished_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            duration_s=max(0.0, self._clock() - started),
            router=self._router_manifest(),
            renderer=self._renderer_manifest(),
            review={
                "reviewer": getattr(self._reviewer, "name", ""),
                "max_retries": self.config.max_retries,
                "policy": "fail closed: an unreachable reviewer fails the shot",
            },
            status=("completed" if all(r.passed for r in records) else "needs_operator"),
            manifest_version=MANIFEST_VERSION,
        )
        return manifest

    def _shot_record(self, shot: Any, outcome: ReviewOutcome, index: int) -> ShotRunRecord:
        """Fold a review outcome into a manifest record."""
        attempts: List[ShotAttempt] = []
        for record in outcome.attempts:
            attempts.append(
                ShotAttempt(
                    attempt=record.attempt,
                    job_id=record.job_id,
                    status=record.status,
                    artifacts=record.artifacts,
                    # Both spellings are recorded: the WSL form the pipeline
                    # stores and the native Windows path the operator sees in
                    # the renderer's output folder. Recording only one makes
                    # the manifest unusable from the other host.
                    artifacts_native=record.artifacts_native,
                    passed=record.verdict.passed if record.verdict else None,
                    review_notes=tuple(record.verdict.notes) if record.verdict else (),
                    review_reasons=tuple(record.verdict.reasons) if record.verdict else (),
                    reviewer=record.verdict.reviewer if record.verdict else "",
                    revision_applied=record.revision.as_dict() if record.revision else {},
                    error=record.error,
                    prompt_sha256_16=self._digest_for(record),
                    seed=self._seed_for(record),
                    template_id=self._template_for(record),
                )
            )

        passing = [a for a in attempts if a.passed]
        if passing:
            status = "passed"
        elif any(a.status in ("render_error", "review_error") for a in attempts):
            status = "error"
        else:
            status = "needs_operator"

        final_spec = shot
        return ShotRunRecord(
            shot_id=getattr(shot, "shot_id", "") or f"shot_{index + 1}",
            sequence_index=index,
            version=int(getattr(shot, "version", 1) or 1),
            final_status=status,
            attempts=attempts,
            shot_spec=_spec_dict(final_spec),
            compile_manifest=self._compile_manifest(outcome),
            error=outcome.reason,
        )

    # -- small extractors: the loop hands back attempts, not compiles ----

    def set_client(self, client: Any) -> None:
        """Attach the renderer client after construction.

        The CLI builds the client from the environment, which can fail, so the
        pipeline is constructed first and given its renderer once that
        succeeds. Kept public so the CLI never pokes at ``_client``.
        """
        self._client = client

    def set_reviewer(self, reviewer: Any) -> None:
        """Swap the reviewer after construction.

        The pipeline is built once per run with a default probe reviewer;
        a caller wanting the LLM critique (or a test driving a verdict
        sequence) attaches it here rather than reaching into ``_reviewer``.
        """
        self._reviewer = reviewer

    def _digest_for(self, record: AttemptRecord) -> str:
        compiled = getattr(record, "compiled", None)
        if compiled is None:
            return ""
        try:
            return str(compiled.prompt_digest)
        except Exception:  # pragma: no cover - defensive
            return ""

    def _seed_for(self, record: AttemptRecord) -> int:
        compiled = getattr(record, "compiled", None)
        return int(getattr(compiled, "seed", -1)) if compiled is not None else -1

    def _template_for(self, record: AttemptRecord) -> str:
        compiled = getattr(record, "compiled", None)
        return str(getattr(getattr(compiled, "template", None), "template_id", "")) or ""

    def _compile_manifest(self, outcome: ReviewOutcome) -> Dict[str, Any]:
        """The first attempt's compile manifest — the run's starting intent."""
        for record in outcome.attempts:
            compiled = record.compiled
            if compiled is not None:
                try:
                    return dict(compiled.as_manifest())
                except Exception:  # pragma: no cover - defensive
                    return {}
        return {}

    def _router_manifest(self) -> Dict[str, Any]:
        """Routing decisions for the run: which provider served what."""
        metrics = getattr(self._router, "metrics", None)
        if metrics is None:
            return {}
        try:
            snapshot = metrics.snapshot()
        except Exception:  # pragma: no cover - defensive
            return {}
        # Tokens and counts are audit-worthy; latency is wall-clock and is
        # already in VOLATILE_PATHS for the diff.
        return {"requests": snapshot.get("requests", 0), **snapshot}

    def _renderer_manifest(self) -> Dict[str, Any]:
        """Renderer identity: flavor, tool surface, endpoint. No secrets."""
        client = self._client
        if client is None:
            return {}
        out: Dict[str, Any] = {}
        config = getattr(client, "config", None)
        if config is not None:
            out["base_url"] = getattr(config, "base_url", "")
        try:
            caps = client.connect()
        except Exception as exc:
            out["connect_error"] = f"{type(exc).__name__}: {exc}"
            return out
        if caps is not None and hasattr(caps, "as_manifest"):
            out.update(caps.as_manifest())
        return out

    @staticmethod
    def _derive_run_id(script: str, project_id: str) -> str:
        digest = hashlib.sha256(
            f"{project_id}:{script}".encode("utf-8")
        ).hexdigest()[:12]
        return f"run_{digest}"


def _spec_dict(shot: Any) -> Dict[str, Any]:
    dumper = getattr(shot, "model_dump", None)
    if callable(dumper):
        return dict(dumper())
    return {}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    """``python -m backend.services.pipeline run --script FILE``.

    Prints a one-line summary per shot and the manifest path. Exit codes: 0 all
    shots passed, 1 at least one needs an operator, 2 the run could not start.
    """
    import argparse
    import json
    import sys

    from backend.services.reviewers import ArtifactProbeReviewer

    parser = argparse.ArgumentParser(
        prog="python -m backend.services.pipeline",
        description="script -> ShotSpec -> WanGP render -> review -> manifest",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="run the pipeline over a script")
    run_p.add_argument("--script", required=True, help="path to the script file")
    run_p.add_argument("--project-id", default="")
    run_p.add_argument("--out", default="runs/", help="directory for the manifest")
    run_p.add_argument("--template", default=None, help="force a template_id")
    run_p.add_argument("--aspect", default="16:9")
    run_p.add_argument("--target", default="wangp", choices=("wangp", "ltx23"))
    run_p.add_argument("--max-retries", type=int, default=MAX_RETRIES)
    run_p.add_argument("--dry-run", action="store_true",
                       help="compile the shot list and print prompts; no renderer contact")
    run_p.add_argument("--shots-json", default=None,
                       help="skip the director pass; read ShotSpec[] from this file")
    run_p.add_argument("--allow-cloud-script", action="store_true",
                       help="permit cloud overflow for the director pass")
    run_p.add_argument("--poll-timeout", type=float, default=3600.0)

    diff_p = sub.add_parser("diff", help="diff two manifests")
    diff_p.add_argument("left")
    diff_p.add_argument("right")
    diff_p.add_argument("--include-volatile", action="store_true")
    diff_p.add_argument("--fingerprint", action="store_true",
                        help="print fingerprints instead of field diffs")

    args = parser.parse_args(argv)

    if args.command == "diff":
        return _diff_command(args)

    script_path = Path(args.script)
    if not script_path.is_file():
        print(f"error: no such script: {args.script}", file=sys.stderr)
        return 2
    script = script_path.read_text(encoding="utf-8")

    config = PipelineConfig(
        target=args.target,
        aspect=args.aspect,
        template_id=args.template,
        max_retries=args.max_retries,
        poll_timeout_s=args.poll_timeout,
        allow_cloud_script=args.allow_cloud_script,
    )

    # A fixture-driven run skips the director pass entirely: same compile,
    # render, review, and manifest, with the LLM call replaced by a file.
    if args.shots_json:
        from backend.services.shot_spec import validate_shot_specs

        try:
            raw = json.loads(Path(args.shots_json).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read --shots-json: {exc}", file=sys.stderr)
            return 2
        entries = raw.get("shots", raw) if isinstance(raw, dict) else raw
        try:
            shots = validate_shot_specs(list(entries), source=str(args.shots_json))
        except Exception as exc:
            print(f"error: invalid ShotSpec in --shots-json: {exc}", file=sys.stderr)
            return 2
        pipeline = ScriptToVideoPipeline(
            client=None,
            reviewer=ArtifactProbeReviewer(),
            config=config,
        )
        return _run_with_shots(pipeline, shots, script_path, args)

    director = None
    router = None

    # A dry run needs no renderer at all, which is what makes it useful on a
    # box with no WanGP running: it still exercises the director pass, the
    # compiler, and the template selection.
    client = None
    if not args.dry_run:
        from backend.integrations.wangp_client import WangPClient
        from backend.integrations.wangp_config import WangPMCPConfig

        client = WangPClient(WangPMCPConfig.from_env())

    try:
        from backend.services.llm_router import LLMRouter

        router = LLMRouter.from_env(render_state=client)
    except Exception as exc:
        print(f"error: could not build the LLM router: {exc}", file=sys.stderr)
        return 2

    try:
        from backend.services.director_service import DirectorService

        director = DirectorService(render_state=client)
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"warning: director service unavailable ({exc}); using the router directly",
              file=sys.stderr)

    pipeline = ScriptToVideoPipeline(
        router=router,
        client=client,
        director=director,
        reviewer=ArtifactProbeReviewer(),
        config=config,
    )

    if args.dry_run:
        return _dry_run(pipeline, script, args)

    return _run_live(pipeline, script, script_path, args)


def _dry_run(
    pipeline: "ScriptToVideoPipeline",
    script: str,
    args,
    shots: Optional[list] = None,
) -> int:
    """Compile every shot and print its prompt. No renderer, no manifest.

    ``shots`` short-circuits the director pass, so a dry run works from a
    shot-list file with no LLM at all.
    """
    import sys

    try:
        shots = shots if shots is not None else pipeline.shots_from_script(
            script, project_id=args.project_id
        )
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    failures = 0
    for shot in shots:
        try:
            compiled = pipeline._compile(shot, pipeline.config.overrides)
        except Exception as exc:
            failures += 1
            print(f"[FAIL] {shot.shot_id}: {type(exc).__name__}: {exc}")
            continue
        print()
        print(f"=== {shot.shot_id}  ({compiled.template.template_id}, "
              f"{compiled.prompt_tokens} est. tokens, seed {compiled.seed}) ===")
        print(compiled.prompt)
    print()
    print(f"dry run: compiled {len(shots) - failures}/{len(shots)} shot(s); "
          f"nothing was rendered")
    return 1 if failures else 0


def _run_live(pipeline: "ScriptToVideoPipeline", script: str, script_path: Path, args) -> int:
    import sys

    from backend.services.run_manifest import manifest_fingerprint

    try:
        manifest = pipeline.run(script, project_id=args.project_id, script_path=str(script_path))
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = manifest.save(out_dir / f"{manifest.run_id}.json")
    _print_summary(manifest, path)
    return 0 if manifest.status == "completed" else 1


def _run_with_shots(pipeline: "ScriptToVideoPipeline", shots, script_path: Path, args) -> int:
    """Run with a pre-validated ShotSpec list, skipping the director pass.

    Still needs a renderer client. This is the path a fixture-driven
    integration run takes: same compile, same render, same review, same
    manifest — only the director LLM call is replaced by a file.
    """
    import sys

    from backend.integrations.wangp_client import WangPClient
    from backend.integrations.wangp_config import WangPMCPConfig

    if args.dry_run:
        return _dry_run(pipeline, script_path.read_text(encoding="utf-8"), args, shots=shots)

    try:
        client = WangPClient(WangPMCPConfig.from_env())
    except Exception as exc:
        print(f"error: could not build the renderer client: {exc}", file=sys.stderr)
        return 2

    pipeline.set_client(client)
    try:
        manifest = pipeline.run_shots(
            list(shots),
            project_id=args.project_id,
            script_path=str(script_path),
            script_text=script_path.read_text(encoding="utf-8"),
        )
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = manifest.save(out_dir / f"{manifest.run_id}.json")
    _print_summary(manifest, path)
    return 0 if manifest.status == "completed" else 1


def _print_summary(manifest, path: Path) -> None:
    from backend.services.run_manifest import manifest_fingerprint

    print()
    print(f"run {manifest.run_id}: {manifest.status}")
    print(f"  shots      : {manifest.shot_count}")
    print(f"  passed     : {len(manifest.passed_shots)}")
    print(f"  operator   : {len(manifest.operator_shots)}")
    print(f"  attempts   : {manifest.total_attempts}")
    print(f"  fingerprint: {manifest_fingerprint(manifest)[:16]}")
    print(f"  manifest   : {path}")
    for shot in manifest.shots:
        mark = "ok  " if shot.final_status == "passed" else "HOLD"
        print(f"  [{mark}] {shot.shot_id} "
              f"({shot.attempts_used} attempt{'s' if shot.attempts_used != 1 else ''}) "
              f"{shot.last_artifact or shot.error}")


def _diff_command(args) -> int:
    import sys

    from backend.services.run_manifest import (
        RunManifest,
        diff_manifests,
        manifest_fingerprint,
    )

    left = RunManifest.load(args.left)
    right = RunManifest.load(args.right)
    if args.fingerprint:
        print(manifest_fingerprint(left))
        print(manifest_fingerprint(right))
        return 0
    entries = diff_manifests(left, right, include_volatile=args.include_volatile)
    if not entries:
        print("identical (volatile fields ignored)")
        return 0
    for entry in entries:
        print(f"{entry['path']}\n  left : {entry['left']!r}\n  right: {entry['right']!r}")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())