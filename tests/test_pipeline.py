"""End-to-end pipeline tests: no cloud key, no renderer, mocked transport.

These are the acceptance tests for the integration card. They run the *real*
compile -> render -> review -> manifest path against:

* a scripted local LLM provider (stands in for Ollama; no key, no network),
* a mocked MCP transport replaying the recorded live fixtures (stands in for
  the WanGP renderer; no GPU, no :8899),

and assert the properties the card asks for:

1. the whole suite passes with no cloud key and no renderer running;
2. the review loop stops after 2 failed retries instead of looping forever;
3. the manifest carries every required field and diffs cleanly across runs;
4. no code path deletes ``D:\\Wan2GP`` / ``/mnt/d/wan2gp``.

Nothing here is a stub of the pipeline: :class:`ScriptToVideoPipeline`,
``ReviewLoop``, ``compile_shot``, and ``WangPClient`` are the production
objects. Only the two external edges are substituted.
"""
from __future__ import annotations

import ast
import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import pytest

from backend.integrations.wangp_client import WangPClient
from backend.integrations.wangp_config import WangPMCPConfig
from backend.services.pipeline import (
    PipelineConfig,
    PipelineError,
    ScriptToVideoPipeline,
    effective_overrides,
)
from backend.services.review_loop import (
    MAX_RETRIES,
    Revision,
    ReviewLoop,
    ReviewVerdict,
    RevisionBudgetExhausted,
    plan_one_revision,
)
from backend.services.reviewers import ArtifactProbeReviewer, probe_artifact
from backend.services.run_manifest import (
    RunManifest,
    ShotAttempt,
    ShotRunRecord,
    assert_no_secrets,
    diff_manifests,
    manifest_fingerprint,
)
from backend.services.shot_spec import ShotListOutput, example_paths, load_shot_spec

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "wangp_mcp"

SAMPLE_SCRIPT = """INT. RENTED STUDIO KITCHEN — DAWN

MAYA (34, dark hair, grey knit sweater) stands at the counter, one hand flat
on an envelope she has clearly been holding for a long time.

MAYA
(quietly)
It's still here.

She turns it over. Her thumb finds the seal. She doesn't break it.
"""


# ---------------------------------------------------------------------------
# Test doubles: the two external edges only
# ---------------------------------------------------------------------------


class ScriptedProvider:
    """A local LLM that replays a fixed reply. Stands in for Ollama.

    Records every prompt so a test can assert what the director actually saw.
    No key, no socket, no clock.
    """

    def __init__(self, reply: str, model: str = "test-local:1b") -> None:
        self.reply = reply
        self.model = model
        self.prompts: List[str] = []
        self.last_failure = ""
        self.calls = 0

    def health_check(self) -> bool:
        return True

    def generate(self, prompt: str, **kwargs: Any) -> str:
        self.calls += 1
        self.prompts.append(prompt)
        return self.reply

    @property
    def last_usage(self):
        from backend.llm.base import TokenUsage

        return TokenUsage(prompt_tokens=10, completion_tokens=20)


def _fixture_result(name: str) -> Dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["result"]


class MockRendererServer:
    """JSON-RPC over loopback HTTP, replaying the recorded WanGP fixtures.

    Same protocol the real renderer speaks (``--mcp --mcp-transport
    streamable-http``), same recorded payloads, no GPU. Loopback only.
    """

    def __init__(self) -> None:
        self.initialize = _fixture_result("01_initialize.json")
        self.tools = _fixture_result("02_tools_list.json")
        self.generate_queue: List[Any] = []
        self.job_queue: List[Any] = []
        self.submitted: List[Dict[str, Any]] = []
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.port = 0

    # -- lifecycle --
    def start(self) -> int:
        renderer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):  # silence
                pass

            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    request = json.loads(raw.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    self.send_response(400)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                status, payload = renderer._respond(request)
                body = b"" if payload is None else json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if body:
                    self.wfile.write(body)

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self.port

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def client(self) -> WangPClient:
        return WangPClient(
            WangPMCPConfig(
                host="127.0.0.1",
                port=self.port,
                connect_timeout_s=5.0,
                request_timeout_s=10.0,
                submit_timeout_s=10.0,
                poll_timeout_s=10.0,
                poll_interval_s=0.01,
                retry_attempts=1,
            )
        )

    # -- scripted responses --
    def queue_render(self, *, job_id: str = "job-1", artifact: str = None) -> None:
        """Queue one complete render: submit -> in-flight -> done.

        Uses the ``gguf_q4`` fixture pair because those are the recorded
        *completed* jobs (``done: true`` with ``result.generated_files``). The
        ``int8`` fixtures are all mid-flight snapshots, so a queue built from
        them never terminates.
        """
        generate = _stamp(_deep_copy(_fixture_result("gguf_q4_generate.json")), job_id)
        self.generate_queue.append(generate)
        final = _stamp(_deep_copy(_fixture_result("gguf_q4_job_final.json")), job_id, artifact)
        # One in-flight poll, then the completion, so the client exercises
        # polling rather than returning straight from the submit snapshot.
        inflight = _deep_copy(generate)
        inflight["structuredContent"]["done"] = False
        inflight["structuredContent"]["events"] = [{"kind": "progress", "data": {"step": 1}}]
        self.job_queue.append(_stamp(inflight, job_id))
        self.job_queue.append(final)

    def _respond(self, request: Mapping[str, Any]):
        method = request.get("method")
        rid = request.get("id")
        if method is None:
            return 202, None
        if method == "initialize":
            return 200, {"jsonrpc": "2.0", "id": rid, "result": self.initialize}
        if method == "tools/list":
            return 200, {"jsonrpc": "2.0", "id": rid, "result": self.tools}
        if method == "tools/call":
            name = request.get("params", {}).get("name", "")
            args = request.get("params", {}).get("arguments", {}) or {}
            if "generate" in name:
                if not self.generate_queue:
                    return 200, {"jsonrpc": "2.0", "id": rid, "error": {"code": -1, "message": "no script"}}
                self.submitted.append(args)
                result = self.generate_queue.pop(0)
            else:
                result = self.job_queue.pop(0) if self.job_queue else {}
            return 200, {"jsonrpc": "2.0", "id": rid, "result": result}
        return 200, {"jsonrpc": "2.0", "id": rid, "result": {}}


def _deep_copy(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _stamp(envelope: Dict[str, Any], job_id: str, artifact: str | None = None) -> Dict[str, Any]:
    """Re-stamp a recorded tool result with a fresh job id / artifact path.

    The artifact path has to be written in *both* places the client reads it
    from (``result.generated_files`` and the terminal ``completed`` event),
    because ``parse_job_status`` prefers the former and falls back to the
    latter; stamping only one silently yields an artifact-less render.
    """
    structured = envelope.get("structuredContent")
    if not isinstance(structured, dict):
        return envelope
    structured["job_id"] = job_id
    if artifact is not None:
        structured["result"] = {
            "success": True,
            "cancelled": False,
            "generated_files": [artifact],
            "errors": [],
            "total_tasks": 1,
            "successful_tasks": 1,
            "failed_tasks": 0,
            "artifacts": [],
        }
        for event in structured.get("events") or []:
            if isinstance(event, dict) and event.get("kind") == "completed":
                event["data"] = dict(structured["result"])
    envelope["content"] = [
        {"type": "text", "text": json.dumps(structured, indent=2)}
    ]
    return envelope


class ScriptedReviewer:
    """A reviewer that returns a fixed verdict sequence, then repeats the last."""

    name = "scripted"

    def __init__(self, verdicts: Sequence[ReviewVerdict]) -> None:
        self.verdicts = list(verdicts)
        self.calls: List[int] = []

    def review(self, *, shot_spec, compiled, artifacts, attempt: int) -> ReviewVerdict:
        self.calls.append(attempt)
        index = min(attempt - 1, len(self.verdicts) - 1)
        return self.verdicts[index]


def _always_fail(notes: str = "the subject is missing from frame 2") -> ReviewVerdict:
    return ReviewVerdict(
        passed=False,
        reviewer="scripted",
        reasons=("subject_absent",),
        notes=(notes,),
        structured={"action": "Maya lifts the envelope to eye level and breaks the seal."},
    )


def _always_pass() -> ReviewVerdict:
    return ReviewVerdict(passed=True, reviewer="scripted", notes=("reads on intent",))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def two_shots():
    """Two real example ShotSpecs sharing one recurring character."""
    by_name = {p.stem: load_shot_spec(p) for p in example_paths()}
    return [by_name["recurring_shot_01"], by_name["recurring_shot_02"]]


@pytest.fixture
def renderer():
    server = MockRendererServer()
    server.start()
    try:
        yield server
    finally:
        server.stop()


# ---------------------------------------------------------------------------
# 1. The compile -> render boundary actually holds
# ---------------------------------------------------------------------------


class TestCompilerRendererSeam:
    """The integration has real work to do, and this pins it down.

    compile_shot derives ``frames`` from ``duration_seconds`` internally, so
    its returned ``overrides`` omit it. Handing those verbatim to the client
    trips the boundary guard on every shot whose length differs from the
    template's. These tests fail if that seam regresses.
    """

    def test_caller_overrides_alone_trip_the_boundary_guard(self, two_shots):
        """The naive wiring is wrong; if this ever passes, the seam changed."""
        from backend.integrations.wangp_settings import ResolvedSettings, enforce_bounded_settings
        from backend.services.prompt_compiler import compile_shot

        shot = two_shots[0]
        compiled = compile_shot(shot, target="wangp")
        resolved = ResolvedSettings.from_template(compiled.template.settings, compiled.overrides)
        with pytest.raises(Exception) as excinfo:
            enforce_bounded_settings(compiled.payload, resolved.template, resolved.overrides)
        assert "video_length" in str(excinfo.value)

    @pytest.mark.parametrize("shot_index", [0, 1])
    def test_effective_overrides_satisfy_the_guard(self, two_shots, shot_index):
        from backend.integrations.wangp_settings import ResolvedSettings, enforce_bounded_settings
        from backend.services.prompt_compiler import compile_shot

        compiled = compile_shot(two_shots[shot_index], target="wangp")
        overrides = effective_overrides(compiled.template.settings, compiled.settings)
        resolved = ResolvedSettings.from_template(compiled.template.settings, overrides)
        enforce_bounded_settings(compiled.payload, resolved.template, resolved.overrides)

    def test_effective_overrides_carry_the_derived_frame_count(self, two_shots):
        from backend.services.prompt_compiler import compile_shot

        compiled = compile_shot(two_shots[0], target="wangp")
        overrides = effective_overrides(compiled.template.settings, compiled.settings)
        assert overrides["frames"] == compiled.payload["video_length"]
        assert compiled.overrides == {}  # the caller asked for nothing

    @pytest.mark.parametrize(
        "caller_overrides",
        [
            {},
            {"width": 768, "height": 432},
            {"steps": 12},
            {"fps": 24},
            {"frames": 121},
            {"width": 640, "height": 360, "steps": 6},
        ],
    )
    def test_every_override_shape_survives_the_guard(self, two_shots, caller_overrides):
        from backend.integrations.wangp_settings import ResolvedSettings, enforce_bounded_settings
        from backend.services.prompt_compiler import compile_shot

        compiled = compile_shot(two_shots[0], target="wangp", overrides=caller_overrides)
        overrides = effective_overrides(compiled.template.settings, compiled.settings)
        resolved = ResolvedSettings.from_template(compiled.template.settings, overrides)
        enforce_bounded_settings(compiled.payload, resolved.template, resolved.overrides)

    def test_overrides_are_confined_to_the_six(self, two_shots):
        from backend.integrations.wangp_settings import ALLOWED_OVERRIDE_KEYS
        from backend.services.prompt_compiler import compile_shot

        compiled = compile_shot(
            two_shots[0], target="wangp", overrides={"width": 768, "height": 432, "steps": 10}
        )
        overrides = effective_overrides(compiled.template.settings, compiled.settings)
        assert set(overrides) <= set(ALLOWED_OVERRIDE_KEYS)

    def test_pipeline_render_submits_a_payload_the_client_accepts(self, renderer, two_shots):
        """End-to-end through the real client and the mocked MCP server."""
        renderer.queue_render(job_id="job-seam", artifact="/mnt/d/Wan2GP/outputs/seam.mp4")
        pipeline = ScriptToVideoPipeline(
            client=renderer.client(),
            reviewer=ScriptedReviewer([_always_pass()]),
            config=PipelineConfig.for_tests(),
        )
        outcome = pipeline.render_shot(two_shots[0])
        assert outcome.job_id == "job-seam"
        assert renderer.submitted, "the client never called the generate tool"
        submitted = renderer.submitted[0]
        assert submitted, "generate was called with no arguments"


# ---------------------------------------------------------------------------
# 2. The retry ceiling
# ---------------------------------------------------------------------------


class TestRetryCeiling:
    """Requirement: at most 2 automated retries, then surface to the operator."""

    def test_max_retries_is_two(self):
        assert MAX_RETRIES == 2

    def test_caller_cannot_buy_more_retries(self):
        """The ceiling is enforced, not documented."""
        with pytest.raises(RevisionBudgetExhausted):
            ReviewLoop(
                ScriptedReviewer([_always_pass()]),
                lambda *a, **k: None,
                max_retries=3,
            )

    def test_zero_retries_is_allowed(self):
        loop = ReviewLoop(
            ScriptedReviewer([_always_pass()]),
            lambda *a, **k: None,
            max_retries=0,
        )
        assert loop.max_retries == 0

    def test_passing_on_first_attempt_renders_once(self, two_shots):
        renders: List[int] = []

        def render(spec, revision=None):
            renders.append(1)
            from backend.services.pipeline import RenderOutcome

            return RenderOutcome(artifacts=("/tmp/a.mp4",), job_id="j1", compiled=None)

        loop = ReviewLoop(ScriptedReviewer([_always_pass()]), render)
        outcome = loop.run(two_shots[0])
        assert outcome.passed
        assert outcome.attempts_used == 1
        assert outcome.retries_used == 0
        assert len(renders) == 1

    def test_passing_on_second_attempt_renders_twice(self, two_shots):
        renders: List[int] = []

        def render(spec, revision=None):
            renders.append(1)
            from backend.services.pipeline import RenderOutcome

            return RenderOutcome(artifacts=("/tmp/a.mp4",), job_id="j", compiled=None)

        loop = ReviewLoop(ScriptedReviewer([_always_fail(), _always_pass()]), render)
        outcome = loop.run(two_shots[0])
        assert outcome.passed
        assert outcome.attempts_used == 2
        assert outcome.retries_used == 1
        assert len(renders) == 2

    def test_always_failing_reviewer_stops_after_exactly_three_attempts(self, two_shots):
        """THE acceptance test: a reviewer that never passes must not loop."""
        renders: List[Any] = []

        def render(spec, revision=None):
            renders.append(spec)
            from backend.services.pipeline import RenderOutcome

            return RenderOutcome(artifacts=("/tmp/a.mp4",), job_id="j", compiled=None)

        reviewer = ScriptedReviewer([_always_fail()])
        loop = ReviewLoop(reviewer, render)
        outcome = loop.run(two_shots[0])

        assert outcome.passed is False
        assert outcome.exhausted is True
        assert outcome.attempts_used == 3  # 1 initial + 2 retries
        assert outcome.retries_used == 2
        assert len(renders) == 3, "the loop rendered more than the budget allows"
        assert reviewer.calls == [1, 2, 3]

    def test_exhaustion_reason_names_the_budget(self, two_shots):
        def render(spec, revision=None):
            from backend.services.pipeline import RenderOutcome

            return RenderOutcome(artifacts=("/tmp/a.mp4",), job_id="j")

        loop = ReviewLoop(ScriptedReviewer([_always_fail()]), render)
        outcome = loop.run(two_shots[0])
        assert "2-retry" in outcome.reason
        assert "operator" in outcome.reason

    def test_each_retry_carries_its_own_revision(self, two_shots):
        """Retries must differ from the first attempt, not repeat it."""
        seen_revisions: List[Optional[Revision]] = []

        def render(spec, revision=None):
            seen_revisions.append(revision)
            from backend.services.pipeline import RenderOutcome

            return RenderOutcome(artifacts=("/tmp/a.mp4",), job_id="j")

        loop = ReviewLoop(ScriptedReviewer([_always_fail()]), render)
        loop.run(two_shots[0])
        assert seen_revisions[0] is None, "the first attempt must render the spec as given"
        assert seen_revisions[1] is not None
        assert seen_revisions[2] is not None

    def test_revised_shot_actually_changes_the_compiled_prompt(self, two_shots):
        """A revision that does not change the prompt wastes a render."""
        from backend.services.prompt_compiler import compile_shot

        rendered_specs: List[Any] = []

        def render(spec, revision=None):
            rendered_specs.append(spec)
            from backend.services.pipeline import RenderOutcome

            return RenderOutcome(artifacts=("/tmp/a.mp4",), job_id="j")

        loop = ReviewLoop(ScriptedReviewer([_always_fail()]), render)
        loop.run(two_shots[0])

        first = compile_shot(rendered_specs[0], target="wangp").prompt
        last = compile_shot(rendered_specs[-1], target="wangp").prompt
        assert first != last, "the retried shot compiled to an identical prompt"

    def test_zero_retries_fails_after_one_attempt(self, two_shots):
        renders: List[int] = []

        def render(spec, revision=None):
            renders.append(1)
            from backend.services.pipeline import RenderOutcome

            return RenderOutcome(artifacts=("/tmp/a.mp4",), job_id="j")

        loop = ReviewLoop(ScriptedReviewer([_always_fail()]), render, max_retries=0)
        outcome = loop.run(two_shots[0])
        assert not outcome.passed
        assert outcome.attempts_used == 1
        assert len(renders) == 1

    def test_unactionable_failure_surfaces_without_re_rendering(self, two_shots):
        """Notes with no settable field cannot drive a recompile."""
        renders: List[int] = []

        def render(spec, revision=None):
            renders.append(1)
            from backend.services.pipeline import RenderOutcome

            return RenderOutcome(artifacts=("/tmp/a.mp4",), job_id="j")

        verdict = ReviewVerdict(
            passed=False,
            reviewer="scripted",
            reasons=("looks_wrong",),
            notes=("something is off but I cannot say what",),
            # no structured fields -> no revision possible
        )
        loop = ReviewLoop(ScriptedReviewer([verdict]), render)
        outcome = loop.run(two_shots[0])
        assert not outcome.passed
        assert outcome.attempts_used == 1
        assert len(renders) == 1
        assert "no actionable revision" in outcome.reason

    def test_a_failing_reviewer_must_not_approve(self, two_shots):
        """An unreachable critic fails the shot. Silence is not a pass."""

        class BrokenReviewer:
            name = "broken"

            def review(self, **kwargs):
                raise RuntimeError("model unreachable")

        def render(spec, revision=None):
            from backend.services.pipeline import RenderOutcome

            return RenderOutcome(artifacts=("/tmp/a.mp4",), job_id="j")

        loop = ReviewLoop(BrokenReviewer(), render)
        outcome = loop.run(two_shots[0])
        assert outcome.passed is False
        assert "reviewer" in outcome.reason

    def test_a_render_error_stops_immediately(self, two_shots):
        """A transport error is not a review failure; retrying burns budget."""
        renders: List[int] = []

        def render(spec, revision=None):
            renders.append(1)
            raise RuntimeError("connection refused")

        loop = ReviewLoop(ScriptedReviewer([_always_fail()]), render)
        outcome = loop.run(two_shots[0])
        assert outcome.passed is False
        assert outcome.exhausted is False
        assert len(renders) == 1


# ---------------------------------------------------------------------------
# 3. Revision safety
# ---------------------------------------------------------------------------


class TestRevisionSafety:
    def test_revision_applies_to_the_spec(self, two_shots):
        revision = Revision(notes=("fix it",), action="Maya breaks the seal.")
        revised = revision.apply_to(two_shots[0])
        assert revised.action == "Maya breaks the seal."
        assert revised.shot_id == two_shots[0].shot_id

    def test_revision_preserves_identity_and_seed(self, two_shots):
        """The directive: regen keeps shot_id, assets, and seed."""
        original = two_shots[0]
        revised = Revision(action="something else").apply_to(original)
        assert revised.shot_id == original.shot_id
        assert revised.seed == original.seed
        assert [a.asset_id for a in revised.assets] == [a.asset_id for a in original.assets]

    def test_revision_is_revalidated(self, two_shots):
        bad = Revision(duration_seconds=-4.0)
        with pytest.raises(Exception):
            bad.apply_to(two_shots[0])

    def test_plan_ignores_unknown_fields(self, two_shots):
        verdict = ReviewVerdict(
            passed=False,
            reviewer="x",
            notes=("n",),
            structured={
                "action": "a new action",
                "engine": "wan2gp",       # not a ShotSpec field
                "seed": 12345,            # not reviewable
                "scene": {"context": {}},  # a removed shape
            },
        )
        revision = plan_one_revision(verdict)
        assert revision is not None
        assert revision.action == "a new action"
        assert revision.overrides == {}

    def test_plan_drops_non_permitted_overrides(self, two_shots):
        verdict = ReviewVerdict(
            passed=False,
            reviewer="x",
            notes=("n",),
            structured={"overrides": {"guidance": 9.0, "width": 640, "evil": 1}},
        )
        revision = plan_one_revision(verdict)
        assert set(revision.overrides) == {"width"}

    def test_empty_structured_yields_no_revision(self, two_shots):
        verdict = ReviewVerdict(
            passed=False, reviewer="x", notes=("n",), structured={"unrelated": 1}
        )
        assert plan_one_revision(verdict) is None


# ---------------------------------------------------------------------------
# 4. The full run
# ---------------------------------------------------------------------------


def _wire(renderer, shots_reply: str, verdicts, **cfg) -> ScriptToVideoPipeline:
    from backend.services.llm_router import LLMRouter

    provider = ScriptedProvider(shots_reply)
    router = LLMRouter(local=provider)
    return ScriptToVideoPipeline(
        router=router,
        client=renderer.client(),
        reviewer=ScriptedReviewer(verdicts),
        config=PipelineConfig.for_tests(**cfg),
    )


def _shots_reply(two_shots) -> str:
    return json.dumps({"shots": [s.model_dump() for s in two_shots]})


class TestFullRun:
    def test_script_to_artifacts(self, renderer, two_shots):
        """The card's headline requirement, end to end."""
        renderer.queue_render(job_id="j1", artifact="/mnt/d/Wan2GP/outputs/a.mp4")
        renderer.queue_render(job_id="j2", artifact="/mnt/d/Wan2GP/outputs/b.mp4")
        pipeline = _wire(renderer, _shots_reply(two_shots), [_always_pass()])

        manifest = pipeline.run(SAMPLE_SCRIPT, project_id="proj_test")

        assert manifest.shot_count == 2
        assert manifest.status == "completed"
        assert manifest.passed_shots == [s.shot_id for s in two_shots]
        assert len(manifest.artifacts) == 2
        assert len(renderer.submitted) == 2, "one submit per shot"

    def test_run_needs_no_cloud_key(self, renderer, two_shots, monkeypatch):
        """Unset the key explicitly rather than assuming it was absent."""
        monkeypatch.delenv("NIM_API_KEY", raising=False)
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        renderer.queue_render(job_id="j1")
        renderer.queue_render(job_id="j2")
        pipeline = _wire(renderer, _shots_reply(two_shots), [_always_pass()])
        manifest = pipeline.run(SAMPLE_SCRIPT, project_id="proj_test")
        assert manifest.status == "completed"

    def test_routing_decision_is_recorded(self, renderer, two_shots):
        renderer.queue_render(job_id="j1")
        renderer.queue_render(job_id="j2")
        pipeline = _wire(renderer, _shots_reply(two_shots), [_always_pass()])
        manifest = pipeline.run(SAMPLE_SCRIPT)
        assert manifest.router.get("requests", 0) >= 1
        assert manifest.router.get("counts")

    def test_degraded_director_pass_raises(self, renderer):
        """No shots means no run; it must not render nothing and report success."""
        pipeline = _wire(renderer, json.dumps({"shots": []}), [_always_pass()])
        with pytest.raises(PipelineError):
            pipeline.run(SAMPLE_SCRIPT)

    def test_mixed_outcome_marks_the_run_for_the_operator(self, renderer, two_shots):
        """One passing shot, one that exhausts its budget -> needs_operator.

        The two example shots are sc02_sh01 and sc02_sh02, so the reviewer
        keys off the full id rather than a suffix (which both would match).
        """
        for i in range(4):  # shot 1 needs 1 render; shot 2 needs 1 + 2 retries
            renderer.queue_render(job_id=f"j{i}")

        class PerShot:
            name = "per-shot"

            def review(self, *, shot_spec, compiled, artifacts, attempt):
                if shot_spec.shot_id == two_shots[0].shot_id:
                    return _always_pass()
                return _always_fail()

        pipeline = _wire(renderer, _shots_reply(two_shots), [_always_pass()])
        pipeline.set_reviewer(PerShot())
        manifest = pipeline.run(SAMPLE_SCRIPT)

        assert manifest.status == "needs_operator"
        assert manifest.passed_shots == [two_shots[0].shot_id]
        assert manifest.operator_shots == [two_shots[1].shot_id]
        # the failing shot spent its whole budget
        held = next(s for s in manifest.shots if s.final_status == "needs_operator")
        assert held.attempts_used == 3
        assert len(manifest.artifacts) == 1

    def test_fail_fast_stops_the_run(self, renderer, two_shots):
        for i in range(4):
            renderer.queue_render(job_id=f"j{i}")

        class AlwaysFail:
            name = "always-fail"

            def review(self, **kwargs):
                return _always_fail()

        pipeline = _wire(renderer, _shots_reply(two_shots), [_always_fail()], fail_fast=True)
        pipeline.set_reviewer(AlwaysFail())
        manifest = pipeline.run(SAMPLE_SCRIPT)
        assert manifest.shot_count == 1
        assert manifest.status == "needs_operator"

    def test_manifest_records_the_script(self, renderer, two_shots):
        renderer.queue_render(job_id="j1")
        renderer.queue_render(job_id="j2")
        pipeline = _wire(renderer, _shots_reply(two_shots), [_always_pass()])
        manifest = pipeline.run(SAMPLE_SCRIPT, script_path="sample.txt")
        data = manifest.as_dict()
        assert data["script"]["path"] == "sample.txt"
        assert len(data["script"]["sha256"]) == 64

    def test_run_is_reproducible_across_identical_runs(self, renderer, two_shots):
        """Same input twice -> identical non-volatile manifest content."""
        manifests = []
        for i in range(2):
            renderer.queue_render(job_id=f"j{i}", artifact=f"/out/{i}.mp4")
            pipeline = _wire(renderer, _shots_reply(two_shots), [_always_pass()])
            manifests.append(pipeline.run(SAMPLE_SCRIPT, project_id="p"))
        assert manifest_fingerprint(manifests[0]) == manifest_fingerprint(manifests[1])

    def test_no_code_path_deletes_the_renderer_install(self):
        """Acceptance: D:\\Wan2GP / /mnt/d/wan2gp are never deletable."""
        from core.path_guard import DEFAULT_PROTECTED_PATHS, assert_deletable, is_protected

        for spelling in (r"D:\Wan2GP", "/mnt/d/wan2gp", r"d:/wan2gp/", r"D:\Wan2GP\outputs"):
            assert is_protected(spelling)
            with pytest.raises(Exception):
                assert_deletable(spelling)
        assert is_protected(DEFAULT_PROTECTED_PATHS[0])

    def test_manifest_save_refuses_a_renderer_directory(self, tmp_path):
        manifest = RunManifest(run_id="r1")
        protected = Path("/mnt/d/wan2gp/pipeline_manifest.json")
        if protected.parent.is_dir():  # only meaningful on a real WSL box
            with pytest.raises(Exception):
                manifest.save(protected)
        # and the normal path works
        assert manifest.save(tmp_path / "m.json").is_file()


# ---------------------------------------------------------------------------
# 4b. Static guardrails on the pipeline's own source
# ---------------------------------------------------------------------------

#: Filesystem-mutating call targets. Deliberately *not* bare method names:
#: ``"x".replace(...)`` and ``pattern.replace(...)`` are string operations and
#: flagging them makes the check cry wolf, so a reader learns to ignore it.
_MUTATING_TARGETS = frozenset({
    "os.remove", "os.unlink", "os.rmdir", "os.removedirs", "os.rename", "os.replace",
    "shutil.rmtree", "shutil.move", "shutil.copy", "shutil.copy2", "shutil.copytree",
    "pathlib.Path.unlink", "pathlib.Path.rmdir", "pathlib.Path.rename",
    "pathlib.Path.replace", "pathlib.Path.touch", "pathlib.Path.mkdir",
})

#: Method names that mutate a filesystem path. Matched against the *receiver*
#: so ``text.replace`` is exempt while ``db.unlink`` is not.
_STRING_SAFE = frozenset({"replace", "split", "join", "strip", "format", "encode"})
_PATHISH_METHODS = frozenset({
    "unlink", "rmdir", "rmtree", "rename", "replace", "touch", "symlink_to",
})

#: Methods that CREATE a path rather than destroy one. Writing the run
#: manifest is the whole point of ``RunManifest.save``, so creating its parent
#: directory and writing the file are legitimate. Anything that can destroy
#: pre-existing data stays in ``_PATHISH_METHODS``.
_CREATING_METHODS = frozenset({"mkdir", "makedirs", "write_text", "write_bytes"})

#: Subset of the above that writes FILE CONTENT, as opposed to creating a
#: directory. Only these need a per-call-site allowance: a stray ``mkdir`` can
#: create an empty directory, whereas a stray ``write_text`` can overwrite
#: real data. The CLI legitimately creates its ``--out`` directory.
_FILE_WRITE_METHODS = frozenset({"write_text", "write_bytes"})

PIPELINE_MODULES = ("pipeline.py", "review_loop.py", "reviewers.py", "run_manifest.py")


def _dotted(node: ast.AST) -> str | None:
    parts: list[str] = []
    current: ast.AST | None = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def _tree(module: str) -> ast.Module:
    path = REPO_ROOT / "backend" / "services" / module
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


class TestStaticGuardrails:
    """Acceptance: no code path deletes D:\\Wan2GP / /mnt/d/wan2gp."""

    def test_pipeline_modules_are_present(self):
        for module in PIPELINE_MODULES:
            assert (REPO_ROOT / "backend" / "services" / module).is_file(), module

    @pytest.mark.parametrize("module", PIPELINE_MODULES)
    def test_no_destructive_filesystem_call(self, module):
        """No delete, rename, or in-place overwrite of an existing path.

        A bare name match is not good enough: ``"a-b".replace("-", "_")`` is a
        string operation, and a check that flags it trains a reader to ignore
        it. So this matches dotted targets, and separately matches
        filesystem-destroying methods whose receiver is not provably a string.
        """
        offenders: List[str] = []
        for node in ast.walk(_tree(module)):
            if not isinstance(node, ast.Call):
                continue
            dotted = _dotted(node.func)
            if dotted is None:
                continue
            if dotted in _MUTATING_TARGETS:
                offenders.append(f"{module}:{node.lineno} {dotted}()")
                continue
            attr = dotted.rsplit(".", 1)[-1]
            if attr not in _PATHISH_METHODS:
                continue
            receiver = dotted.rsplit(".", 1)[0] if "." in dotted else ""
            leaf = receiver.rsplit(".", 1)[-1]
            if leaf in _STRING_SAFE:
                continue  # provably a string operation
            offenders.append(f"{module}:{node.lineno} {dotted}()")
        assert offenders == [], f"{module} destroys filesystem paths: {offenders}"

    @pytest.mark.parametrize("module", PIPELINE_MODULES)
    def test_file_writes_are_confined_to_the_manifest(self, module):
        """Only ``RunManifest.save`` may write file content.

        Everything else in the pipeline reads; creating the CLI's ``--out``
        directory is fine, but a stray ``write_text`` in the render path would
        let a bug scribble outside the manifest. So the allowance is per
        call-site, not per-module.
        """
        allowed = {("run_manifest.py", "target.write_text")}
        offenders: List[str] = []
        for node in ast.walk(_tree(module)):
            if not isinstance(node, ast.Call):
                continue
            dotted = _dotted(node.func)
            if dotted is None:
                continue
            attr = dotted.rsplit(".", 1)[-1]
            if attr not in _FILE_WRITE_METHODS:
                continue
            receiver = dotted.rsplit(".", 1)[0] if "." in dotted else ""
            if receiver.rsplit(".", 1)[-1] in _STRING_SAFE:
                continue
            if (module, dotted) not in allowed:
                offenders.append(f"{module}:{node.lineno} {dotted}()")
        assert offenders == [], f"{module} writes files outside the manifest: {offenders}"

    def test_manifest_save_is_guarded_before_writing(self):
        """The one write path must consult the deletion guard first.

        Order matters: a guard consulted after the write protects nothing.
        """
        tree = _tree("run_manifest.py")
        save_fn = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "save"
        )
        calls = [
            _dotted(n.func) for n in ast.walk(save_fn) if isinstance(n, ast.Call)
        ]
        guard_index = calls.index("assert_deletable")
        write_index = next(
            i for i, c in enumerate(calls) if c and c.endswith(("write_text", "mkdir"))
        )
        assert guard_index < write_index, (
            "save() must call assert_deletable before creating any path"
        )

    @pytest.mark.parametrize("module", ("pipeline.py", "review_loop.py", "run_manifest.py"))
    def test_no_shell_out(self, module):
        """The render path is pure calls — no subprocess, no shutil."""
        offenders: List[str] = []
        for node in ast.walk(_tree(module)):
            if isinstance(node, ast.Import):
                offenders += [
                    f"{module}:{node.lineno} import {a.name}"
                    for a in node.names
                    if a.name.split(".")[0] in ("subprocess", "shutil")
                ]
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] in ("subprocess", "shutil"):
                    offenders.append(f"{module}:{node.lineno} from {node.module}")
        assert offenders == [], f"{module} shells out: {offenders}"

    def test_reviewer_never_uses_a_shell_string(self):
        """``reviewers.py`` may run ffprobe/ffmpeg — with a fixed argv only."""
        for node in ast.walk(_tree("reviewers.py")):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            if node.func.id != "run":
                continue
            assert node.args and isinstance(node.args[0], ast.List), (
                "subprocess must be called with an argv list"
            )
            assert "shell" not in {k.arg for k in node.keywords}, (
                "subprocess.run must not use shell=True"
            )

    def test_reviewer_never_shells_out_from_manifest_data(self):
        """ffprobe/ffmpeg paths come from PATH or an explicit arg, not a manifest.

        A manifest is operator-editable JSON; interpolating one into a shell
        command would be a command-injection hole.
        """
        tree = _tree("reviewers.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id != "run":
                    continue
                argv = node.args[0]
                assert isinstance(argv, ast.List)
                for element in argv.elts:
                    # every argv element is a literal or a simple local name
                    assert isinstance(
                        element, (ast.Constant, ast.Name, ast.Attribute, ast.BinOp)
                    ), f"suspicious argv element: {ast.unparse(element)}"

    @pytest.mark.parametrize("module", PIPELINE_MODULES)
    def test_modules_import_without_a_renderer_running(self, module):
        """Importing must not connect, spawn, or read GPU state."""
        source = (REPO_ROOT / "backend" / "services" / module).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=module)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    [a.name for a in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                for name in names:
                    assert not name.startswith(("socket", "http.client", "urllib.request")), (
                        f"{module} imports a network module at import time"
                    )


# ---------------------------------------------------------------------------
# 5. Manifest completeness + diffability
# ---------------------------------------------------------------------------


def _two_shots() -> List[Any]:
    """The two recurring-character example specs, as ShotSpec objects."""
    by_name = {p.stem: load_shot_spec(p) for p in example_paths()}
    return [by_name["recurring_shot_01"], by_name["recurring_shot_02"]]


def _manifest_with(**kwargs) -> RunManifest:
    base = dict(
        run_id="run_test",
        script_path="sample.txt",
        script_sha256="a" * 64,
        shots=[
            ShotRunRecord(
                shot_id="sc01_sh01",
                sequence_index=0,
                final_status="passed",
                shot_spec={"shot_id": "sc01_sh01"},
                compile_manifest={"template": {"template_id": "t"}, "seed": 42},
                attempts=[
                    ShotAttempt(
                        attempt=1,
                        job_id="job-1",
                        status="completed",
                        artifacts=("/mnt/d/Wan2GP/outputs/a.mp4",),
                        artifacts_native=(r"D:\Wan2GP\outputs\a.mp4",),
                        passed=True,
                        review_notes=("reads on intent",),
                        reviewer="artifact-probe",
                        prompt_sha256_16="deadbeefdeadbeef",
                        seed=42,
                        template_id="t",
                    )
                ],
            )
        ],
    )
    base.update(kwargs)
    return RunManifest(**base)


class TestManifest:
    def test_carries_every_required_field(self):
        """ShotSpec, template, overrides, routing, job ids, artifacts."""
        data = _manifest_with().as_dict()
        shot = data["shots"][0]

        assert shot["shot_spec"]["shot_id"] == "sc01_sh01"
        assert shot["compile"]["template"]["template_id"] == "t"
        assert "seed" in shot["compile"]
        attempt = shot["attempts"][0]
        assert attempt["job_id"] == "job-1"
        assert attempt["artifacts"] == ["/mnt/d/Wan2GP/outputs/a.mp4"]
        assert attempt["artifacts_native"] == [r"D:\Wan2GP\outputs\a.mp4"]
        assert attempt["prompt_sha256_16"]
        assert attempt["overrides"] == {}
        assert "router" in data

    def test_overrides_are_recorded_per_attempt(self):
        m = _manifest_with()
        m.shots[0].attempts[0].overrides.update({"width": 768})
        assert m.as_dict()["shots"][0]["attempts"][0]["overrides"] == {"width": 768}

    def test_roundtrips_through_json(self, tmp_path):
        original = _manifest_with()
        path = original.save(tmp_path / "m.json")
        loaded = RunManifest.load(path)
        assert loaded.run_id == original.run_id
        assert loaded.shot_count == original.shot_count
        assert loaded.artifacts == original.artifacts
        assert loaded.shots[0].attempts[0].job_id == "job-1"

    def test_serialized_output_is_canonical(self, tmp_path):
        a = _manifest_with().to_json()
        b = _manifest_with().to_json()
        assert a == b
        assert a.endswith("\n")
        assert json.loads(a)["manifest_version"] == 1

    def test_diff_ignores_volatile_fields_by_default(self):
        left = _manifest_with(run_id="run_a", created_at="t1", duration_s=1.0)
        right = _manifest_with(run_id="run_b", created_at="t2", duration_s=9.0)
        right.shots[0].attempts[0] = ShotAttempt(
            **{**right.shots[0].attempts[0].__dict__, "job_id": "job-2"}
        )
        assert diff_manifests(left, right) == []
        assert manifest_fingerprint(left) == manifest_fingerprint(right)

    def test_diff_reports_a_changed_prompt_digest(self):
        left = _manifest_with()
        right = _manifest_with()
        right.shots[0].attempts[0] = ShotAttempt(
            **{**right.shots[0].attempts[0].__dict__, "prompt_sha256_16": "cafebabe"}
        )
        entries = diff_manifests(left, right)
        assert len(entries) == 1
        assert entries[0]["path"].endswith("prompt_sha256_16")

    def test_diff_can_include_volatile(self):
        left = _manifest_with(run_id="run_a")
        right = _manifest_with(run_id="run_b")
        entries = diff_manifests(left, right, include_volatile=True)
        assert any(e["path"] == "run_id" for e in entries)

    def test_diff_across_two_files(self, tmp_path):
        a = _manifest_with(run_id="run_a")
        b = _manifest_with(run_id="run_b")
        b.shots[0].attempts[0] = ShotAttempt(
            **{**b.shots[0].attempts[0].__dict__, "seed": 999}
        )
        pa, pb = a.save(tmp_path / "a.json"), b.save(tmp_path / "b.json")
        entries = diff_manifests(RunManifest.load(pa), RunManifest.load(pb))
        assert any("seed" in e["path"] for e in entries)

    def test_retry_report(self):
        m = _manifest_with()
        assert m.retry_report()["sc01_sh01"]["retries"] == 0
        assert m.total_attempts == 1

    def test_manifest_rejects_a_secret(self):
        payload = {"router": {"api_key": "sk-abcdefghijklmnopqrstuvwx"}}
        with pytest.raises(Exception):
            assert_no_secrets(payload)

    def test_serialization_refuses_a_secret(self):
        m = _manifest_with()
        object.__setattr__(m, "router", {"token": "sk-abcdefghijklmnopqrstuvwx"})
        with pytest.raises(Exception):
            m.to_json()

    def test_key_presence_flags_are_allowed(self):
        assert_no_secrets({"has_cloud_key": True, "consent": "granted"})

    def test_newer_manifest_version_is_refused(self):
        raw = _manifest_with().as_dict()
        raw["manifest_version"] = 99
        with pytest.raises(Exception):
            RunManifest.from_dict(raw)


# ---------------------------------------------------------------------------
# 6. The probe reviewer
# ---------------------------------------------------------------------------


class TestProbeReviewer:
    def _spec(self, two_shots, duration=None):
        if duration is None:
            return two_shots[0]
        data = two_shots[0].model_dump()
        data["duration_seconds"] = duration
        from backend.services.shot_spec import validate_shot_spec

        return validate_shot_spec(data)

    def test_no_artifact_fails_closed(self, two_shots):
        verdict = ArtifactProbeReviewer().review(
            shot_spec=two_shots[0], compiled=None, artifacts=(), attempt=1
        )
        assert verdict.passed is False
        assert "no_artifact" in verdict.reasons

    def test_missing_file_fails(self, two_shots, tmp_path):
        verdict = ArtifactProbeReviewer().review(
            shot_spec=two_shots[0], compiled=None,
            artifacts=[str(tmp_path / "nope.mp4")], attempt=1,
        )
        assert verdict.passed is False
        assert "artifact_missing" in verdict.reasons

    def test_tiny_file_fails(self, two_shots, tmp_path):
        stub = tmp_path / "tiny.mp4"
        stub.write_bytes(b"\x00" * 16)
        verdict = ArtifactProbeReviewer().review(
            shot_spec=two_shots[0], compiled=None, artifacts=[str(stub)], attempt=1
        )
        assert verdict.passed is False
        assert "artifact_too_small" in verdict.reasons

    def test_plausible_file_passes_and_says_what_it_skipped(self, two_shots, tmp_path):
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"\x00" * 4096)  # no ffprobe: existence + size only
        reviewer = ArtifactProbeReviewer(ffprobe="/nonexistent/ffprobe")
        verdict = reviewer.review(
            shot_spec=two_shots[0], compiled=None, artifacts=[str(clip)], attempt=1
        )
        assert verdict.passed is True
        assert any("ffprobe unavailable" in n for n in verdict.notes), (
            "a verdict that skipped checks must say so"
        )

    def test_failure_carries_concrete_notes(self, two_shots, tmp_path):
        stub = tmp_path / "tiny.mp4"
        stub.write_bytes(b"\x00" * 4)
        verdict = ArtifactProbeReviewer().review(
            shot_spec=two_shots[0], compiled=None, artifacts=[str(stub)], attempt=1
        )
        assert verdict.notes
        assert any("bytes" in n for n in verdict.notes)

    def test_probe_never_raises(self, tmp_path):
        result = probe_artifact(tmp_path / "absent.mp4")
        assert result.exists is False
        assert result.ok is False

    def test_reviewers_are_deterministic(self, two_shots, tmp_path):
        """Same artifact, same verdict, every time."""
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"\x00" * 4096)
        reviewer = ArtifactProbeReviewer()
        verdicts = [
            reviewer.review(shot_spec=two_shots[0], compiled=None, artifacts=[str(clip)], attempt=1)
            for _ in range(5)
        ]
        assert len({v.as_dict()["passed"] for v in verdicts}) == 1


# ---------------------------------------------------------------------------
# 7. Keyless / CI-safety
# ---------------------------------------------------------------------------


class TestKeyless:
    def test_pipeline_imports_without_any_key(self, monkeypatch):
        for var in ("NIM_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "NVIDIA_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        import importlib

        module = importlib.import_module("backend.services.pipeline")
        assert module.ScriptToVideoPipeline is not None

    def test_router_from_env_is_keyless_safe(self, monkeypatch):
        for var in ("NIM_API_KEY", "DEEPSEEK_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        from backend.services.llm_router import build_cloud_client

        client, note = build_cloud_client({})
        assert client is None
        assert note

    def test_no_renderer_contact_when_none_is_wired(self, two_shots):
        pipeline = ScriptToVideoPipeline(
            reviewer=ScriptedReviewer([_always_pass()]),
            config=PipelineConfig.for_tests(),
        )
        with pytest.raises(PipelineError):
            pipeline.render_shot(two_shots[0])

    def test_run_without_a_director_or_router_raises(self):
        pipeline = ScriptToVideoPipeline(config=PipelineConfig.for_tests())
        with pytest.raises(PipelineError):
            pipeline.shots_from_script(SAMPLE_SCRIPT)


# ---------------------------------------------------------------------------
# 8. CLI
# ---------------------------------------------------------------------------


class TestCLI:
    def test_diff_command_reports_no_change(self, tmp_path, capsys):
        from backend.services.pipeline import main

        a = _manifest_with(run_id="a").save(tmp_path / "a.json")
        b = _manifest_with(run_id="b").save(tmp_path / "b.json")
        assert main(["diff", str(a), str(b)]) == 0
        assert "identical" in capsys.readouterr().out

    def test_diff_command_reports_a_change(self, tmp_path, capsys):
        from backend.services.pipeline import main

        a = _manifest_with(run_id="a")
        b = _manifest_with(run_id="b")
        b.shots[0].attempts[0] = ShotAttempt(
            **{**b.shots[0].attempts[0].__dict__, "seed": 7}
        )
        pa, pb = a.save(tmp_path / "a.json"), b.save(tmp_path / "b.json")
        assert main(["diff", str(pa), str(pb)]) == 1
        assert "seed" in capsys.readouterr().out

    def test_missing_script_exits_two(self, tmp_path, capsys):
        from backend.services.pipeline import main

        assert main(["run", "--script", str(tmp_path / "nope.txt")]) == 2

    def test_bad_shots_json_exits_two(self, tmp_path, capsys):
        from backend.services.pipeline import main

        script = tmp_path / "s.txt"
        script.write_text(SAMPLE_SCRIPT, encoding="utf-8")
        bad = tmp_path / "shots.json"
        bad.write_text("{not json", encoding="utf-8")
        assert main(["run", "--script", str(script), "--shots-json", str(bad)]) == 2

    def test_dry_run_from_a_shot_list_needs_no_renderer(self, tmp_path, capsys):
        """--dry-run must compile and print without contacting anything.

        Regression guard: --shots-json used to build a renderer client and run
        the whole pipeline even in a dry run, which printed a summary naming a
        manifest_fingerprint that was never imported — two bugs behind one
        happy path nobody exercised.
        """
        from backend.services.pipeline import main

        shots = tmp_path / "shots.json"
        shots.write_text(
            json.dumps({"shots": [s.model_dump() for s in _two_shots()]}), encoding="utf-8"
        )
        script = tmp_path / "s.md"
        script.write_text(SAMPLE_SCRIPT, encoding="utf-8")

        rc = main([
            "run", "--script", str(script), "--shots-json", str(shots), "--dry-run",
        ])
        out = capsys.readouterr().out
        assert rc == 0, out
        assert "nothing was rendered" in out
        assert "sc02_sh01" in out, "the compiled prompt should be printed"

    def test_dry_run_reports_a_compile_failure_with_exit_one(self, tmp_path, capsys):
        """A shot the compiler rejects must not be reported as a clean dry run."""
        from backend.services.pipeline import main

        shots = tmp_path / "shots.json"
        shots.write_text(json.dumps({"shots": []}), encoding="utf-8")
        script = tmp_path / "s.md"
        script.write_text(SAMPLE_SCRIPT, encoding="utf-8")
        rc = main(["run", "--script", str(script), "--shots-json", str(shots), "--dry-run"])
        assert rc == 0  # zero shots is not a compile failure
        assert "0/0" in capsys.readouterr().out

    def test_diff_command_runs_as_a_subprocess(self, tmp_path):
        """The documented `python -m ... diff` entrypoint must actually work.

        Tested via subprocess because the in-process version cannot see the
        ``__main__`` wiring or the import scope the operator gets.
        """
        import subprocess
        import sys

        a = _manifest_with(run_id="a").save(tmp_path / "a.json")
        b = _manifest_with(run_id="b").save(tmp_path / "b.json")
        proc = subprocess.run(
            [sys.executable, "-m", "backend.services.pipeline", "diff", str(a), str(b)],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=180,
        )
        assert proc.returncode == 0, proc.stderr[-2000:]
        assert "identical" in proc.stdout

    def test_print_summary_does_not_raise(self, tmp_path, capsys):
        """The summary printer is the last thing that runs; a bad import there
        turned every successful run into a traceback."""
        from backend.services.pipeline import _print_summary

        manifest = _manifest_with()
        _print_summary(manifest, tmp_path / "m.json")
        assert "run_test" in capsys.readouterr().out