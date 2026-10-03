"""Render in-flight signal: the router's VRAM-overflow input.

Task acceptance (t_3d725aac): an explicit, reliable signal the LLM router can
query. True only while an accepted render job is queued or running; false once
that job is completed, failed, or cancelled. It must be derived from the
renderer's own job state — never inferred from GPU utilization, VRAM readings,
or process state — and it must be compatible with the renderer's existing
job-state model (``JobStatus`` / ``parse_job_status``, v1 and v2 surfaces).

Offline: a loopback mock MCP server replaying the recorded live fixtures from
``tests/fixtures/wangp_mcp/``. No real renderer, no network.
"""
from __future__ import annotations

import ast
import io
import threading
import tokenize
from pathlib import Path
from typing import Any

import pytest

from backend.integrations.wangp_client import (
    ACTIVE_JOB_STATUSES,
    TERMINAL_JOB_STATUSES,
    JobStatus,
    WangPClient,
    WangPError,
    is_in_flight_status,
    parse_job_status,
)
from tests.test_wangp_client import (
    FakeRenderer,
    MockMCP,
    V2_TOOLS,
    make_client,
    replay,
    submit_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CLIENT_SOURCE = REPO_ROOT / "backend" / "integrations" / "wangp_client.py"


def job_body(job_id: str, **overrides: Any) -> dict[str, Any]:
    """A job snapshot in the recorded live shape (what ``parse_job_status`` takes)."""
    body: dict[str, Any] = {
        "job_id": job_id,
        "done": False,
        "cancel_requested": False,
        "created_at": 0.0,
        "updated_at": 1.0,
        "events": [],
    }
    body.update(overrides)
    return body


def terminal_body(
    job_id: str, *, success: bool, cancelled: bool, errors: list[str]
) -> dict[str, Any]:
    return job_body(
        job_id,
        done=True,
        result={
            "success": success,
            "cancelled": cancelled,
            "errors": errors,
            "generated_files": [],
            "artifacts": [],
        },
    )


def envelope(body: dict[str, Any]) -> dict[str, Any]:
    """Wrap a job body as a ``tools/call`` result, as the renderer emits it."""
    return {"isError": False, "structuredContent": body}


# --------------------------------------------------------------------------- vocabulary


class TestStatusVocabulary:
    """The signal's vocabulary, checked against the renderer's status values."""

    def test_running_is_in_flight_and_every_terminal_value_is_not(self):
        assert is_in_flight_status("running") is True
        for terminal in ("completed", "failed", "cancelled"):
            assert is_in_flight_status(terminal) is False

    def test_queued_counts_as_in_flight(self):
        # The renderer reports queued work as done=false -> status "running";
        # a future snapshot that names the queue explicitly still reads busy.
        assert is_in_flight_status("queued") is True
        assert "queued" in ACTIVE_JOB_STATUSES

    def test_unknown_or_missing_status_fails_safe_to_in_flight(self):
        # Unknown must never read idle: an OOM beside a live render is worse
        # than one unnecessary cloud call.
        assert is_in_flight_status(None) is True
        assert is_in_flight_status("") is True
        assert is_in_flight_status("SOMETHING_NEW") is True
        assert is_in_flight_status("RUNNING") is True  # case-tolerant

    def test_vocabulary_sets_are_disjoint(self):
        assert not ACTIVE_JOB_STATUSES & TERMINAL_JOB_STATUSES

    def test_every_value_the_status_property_can_return_is_classified(self):
        emitted = {"running", "completed", "failed", "cancelled"}
        assert emitted <= set(ACTIVE_JOB_STATUSES) | set(TERMINAL_JOB_STATUSES)
        assert emitted & set(ACTIVE_JOB_STATUSES) == {"running"}
        assert emitted & set(TERMINAL_JOB_STATUSES) == emitted - {"running"}


# --------------------------------------------------------------------------- job-state model


class TestCompatibilityWithJobStateModel:
    """The signal reuses the existing parse; it does not re-derive status."""

    def test_in_flight_matches_status_for_every_model_value(self):
        job_id = "job-1"
        cases = {
            "running": job_body(job_id),
            "completed": terminal_body(job_id, success=True, cancelled=False, errors=[]),
            "failed": terminal_body(job_id, success=False, cancelled=False, errors=["oom"]),
            "cancelled": terminal_body(job_id, success=False, cancelled=True, errors=[]),
        }
        for expected, raw in cases.items():
            status = parse_job_status(raw)
            assert status.status == expected
            assert status.in_flight is (expected == "running")

    def test_non_done_submit_is_in_flight(self):
        status = parse_job_status(job_body("job-1"))
        assert status.done is False
        assert status.in_flight is True

    def test_parse_job_status_still_rejects_malformed_snapshots(self):
        with pytest.raises(WangPError):
            parse_job_status({"done": True})  # no job_id
        with pytest.raises(WangPError):
            parse_job_status("not-an-object")

    def test_job_status_is_still_a_frozen_value_object(self):
        status = parse_job_status(job_body("job-1"))
        assert isinstance(status, JobStatus)
        with pytest.raises(Exception):
            status.done = True  # type: ignore[misc]


# --------------------------------------------------------------------------- the signal


class TestRenderInFlightSignal:
    def test_idle_before_any_job(self):
        with MockMCP(FakeRenderer()) as mock:
            client = make_client(mock)
            assert client.render_in_flight() is False
            assert client.is_busy() is False
            assert client.active_job_ids() == ()
            state = client.render_state()
            assert state.in_flight is False and state.jobs == {} and state.probed is False

    def test_true_while_queued_or_running(self):
        renderer = FakeRenderer()
        generate = replay("gguf_q4_generate.json")
        job_id = generate["structuredContent"]["job_id"]
        renderer.generate(generate)
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            job = client.submit_render(payload, resolved)

            assert job.status == "running" and job.in_flight is True
            assert client.render_in_flight() is True
            assert client.is_busy() is True
            assert client.active_job_ids() == (job_id,)
            assert client.render_state().jobs == {job_id: "running"}
            assert client.render_state().in_flight is True

    def test_false_after_the_job_completes(self):
        renderer = FakeRenderer()
        generate = replay("gguf_q4_generate.json")
        job_id = generate["structuredContent"]["job_id"]
        renderer.generate(generate)
        renderer.jobs(replay("gguf_q4_job_final.json", job_id=job_id))
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            result = client.render(payload, resolved, timeout=30, poll_interval=0.02)

            assert result.ok and result.status == "completed"
            assert client.render_in_flight() is False
            assert client.active_job_ids() == ()
            assert client.render_state().in_flight is False

    def test_false_after_the_job_fails(self):
        renderer = FakeRenderer()
        generate = replay("gguf_q4_generate.json")
        job_id = generate["structuredContent"]["job_id"]
        renderer.generate(generate)
        renderer.jobs(
            envelope(terminal_body(job_id, success=False, cancelled=False, errors=["out of memory"]))
        )
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            with pytest.raises(WangPError):
                client.render(payload, resolved, timeout=10, poll_interval=0.02)

            # A failed render is still a finished render: VRAM is released.
            assert client.render_in_flight() is False
            assert client.render_state().jobs == {}

    def test_false_after_the_job_is_cancelled(self):
        renderer = FakeRenderer()
        generate = replay("gguf_q4_generate.json")
        job_id = generate["structuredContent"]["job_id"]
        renderer.generate(generate)
        renderer.extra_tool_results["wangp_cancel_job"] = envelope(
            terminal_body(job_id, success=False, cancelled=True, errors=[])
        )
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            job = client.submit_render(payload, resolved)
            assert client.render_in_flight() is True

            status = client.cancel_job(job.job_id)

            assert status.cancelled is True and status.status == "cancelled"
            assert client.render_in_flight() is False
            assert client.active_job_ids() == ()

    def test_cancel_request_is_not_yet_a_terminal_state(self):
        # Recorded live shape: cancel is accepted while the job is still winding
        # down (done=false). The GPU is still reserved -> still in flight.
        renderer = FakeRenderer()
        generate = replay("gguf_q4_generate.json")
        job_id = generate["structuredContent"]["job_id"]
        renderer.generate(generate)
        renderer.extra_tool_results["wangp_cancel_job"] = replay("10_cancel_int8.json", job_id=job_id)
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            job = client.submit_render(payload, resolved)

            status = client.cancel_job(job.job_id)

            assert status.cancel_requested is True and status.done is False
            assert client.render_in_flight() is True
            assert client.render_state().jobs == {job_id: "running"}

    def test_one_finished_job_among_several_keeps_the_signal_true(self):
        renderer = FakeRenderer()
        first = replay("gguf_q4_generate.json")
        first_id = first["structuredContent"]["job_id"]
        renderer.generate(first, replay("gguf_q4_generate.json", job_id="job-second"))
        renderer.jobs(
            replay("gguf_q4_job_final.json", job_id=first_id),
            envelope(terminal_body("job-second", success=True, cancelled=False, errors=[])),
        )
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            client.submit_render(payload, resolved)
            client.submit_render(payload, resolved)

            assert client.render_in_flight() is True
            client.get_job(first_id)
            assert client.render_in_flight() is True
            assert client.active_job_ids() == ("job-second",)

            client.get_job("job-second")
            assert client.render_in_flight() is False

    def test_v2_session_surface_reports_the_same_signal(self):
        renderer = FakeRenderer()
        renderer.tools_list_result = {"tools": V2_TOOLS}
        generate = replay("gguf_q4_generate.json")
        job_id = generate["structuredContent"]["job_id"]
        renderer.generate(generate)
        renderer.jobs(envelope(terminal_body(job_id, success=True, cancelled=False, errors=[])))
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            client.submit_render(payload, resolved)
            assert client.render_in_flight() is True

            client.get_job(job_id)
            assert client.render_in_flight() is False

    def test_is_busy_is_a_back_compat_alias(self):
        renderer = FakeRenderer()
        renderer.generate(replay("gguf_q4_generate.json"))
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            assert client.is_busy() == client.render_in_flight() is False
            client.submit_render(payload, resolved)
            assert client.is_busy() == client.render_in_flight() is True


# --------------------------------------------------------------------------- explicitness


def executable_source(path: Path) -> str:
    """Source with comments and string literals stripped.

    Docstrings say "never infer this from GPU utilization"; scanning raw text
    would flag the prose. Only real code tokens are checked.
    """
    kept: list[str] = []
    source = path.read_text(encoding="utf-8")
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in (
            tokenize.COMMENT,
            tokenize.STRING,
            tokenize.NL,
            tokenize.NEWLINE,
            tokenize.INDENT,
            tokenize.DEDENT,
        ):
            continue
        kept.append(token.string)
    return " ".join(kept)


class _NoNetworkTransport:
    """Transport that fails loudly — proves the signal needs no probe."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def post(self, method: str, params: Any = None, **kwargs: Any) -> Any:
        self.calls.append(method)
        raise AssertionError(f"render-state read must not touch the network (called {method!r})")

    def notify(self, method: str, params: Any = None) -> None:
        self.calls.append(method)
        raise AssertionError(f"render-state read must not touch the network (called {method!r})")


class TestSignalIsExplicitNotInferred:
    def test_reading_the_signal_never_touches_the_transport(self):
        renderer = FakeRenderer()
        renderer.generate(replay("gguf_q4_generate.json"))
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            client.submit_render(payload, resolved)

            client._transport = _NoNetworkTransport()  # any probe would raise
            assert client.render_in_flight() is True
            state = client.render_state()
            assert state.in_flight is True and state.probed is False

    def test_signal_survives_the_renderer_going_away(self):
        renderer = FakeRenderer()
        renderer.generate(replay("gguf_q4_generate.json"))
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            client.submit_render(payload, resolved)
        # Mock server shut down: the tracked job state is still authoritative.
        assert client.render_in_flight() is True

    def test_module_code_never_consults_gpu_vram_or_process_state(self):
        code = executable_source(CLIENT_SOURCE).lower()
        forbidden = (
            "nvidia-smi",
            "nvml",
            "pynvml",
            "torch",
            "memory_used",
            "memory_total",
            "utilization",
            "gpu_memory",
            "vram",
            "psutil",
            "subprocess",
            "getpid",
            "tasklist",
        )
        hits = sorted({token for token in forbidden if token in code})
        assert hits == [], f"render state must not infer activity from {hits}"

    def test_the_predicate_is_pure(self):
        tree = ast.parse(CLIENT_SOURCE.read_text(encoding="utf-8"))
        predicate = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "is_in_flight_status"
        )
        # Only str methods, and str() is the only call: the predicate is a
        # total function of its argument with no side channel.
        attributes = [node.attr for node in ast.walk(predicate) if isinstance(node, ast.Attribute)]
        assert set(attributes) <= {"strip", "lower"}
        called = [
            node.func.id
            for node in ast.walk(predicate)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        assert called == ["str"]
        # The only module-level name the body reads is the terminal vocabulary.
        # Everything else it names must be its own parameter or a local it
        # binds — subtract those and the remainder is exactly the surface it
        # reaches for, i.e. no hidden state channel.
        bound: set[str] = {a.arg for a in predicate.args.args} | {
            a.arg for a in predicate.args.kwonlyargs
        }
        reads: set[str] = set()
        for statement in predicate.body:
            for node in ast.walk(statement):
                if isinstance(node, ast.Name):
                    # A non-load context is a binding, so the name is local.
                    if not isinstance(node.ctx, ast.Load):
                        bound.add(node.id)
                    else:
                        reads.add(node.id)
                elif isinstance(node, (ast.FunctionDef, ast.Lambda)):
                    bound.update(a.arg for a in node.args.args)
                elif isinstance(node, ast.comprehension) and isinstance(node.target, ast.Name):
                    bound.add(node.target.id)
        # Annotation names (object, bool) never appear here: the walk starts at
        # the body statements, not the signature.
        assert reads - bound <= {"str", "TERMINAL_JOB_STATUSES"}
        assert "TERMINAL_JOB_STATUSES" in reads - bound

    def test_client_satisfies_the_router_render_state_protocol(self):
        # backend/services/llm_router.py asks a provider for render_in_flight().
        # Assert the structural contract without hard-wiring the router here.
        router = pytest.importorskip("backend.services.llm_router")
        assert "render_in_flight" in dir(router.RenderStateProvider)
        client = WangPClient()
        assert callable(client.render_in_flight)
        assert isinstance(client.render_in_flight(), bool)


# --------------------------------------------------------------------------- refresh


class TestRefreshRenderState:
    def test_refresh_reconciles_a_job_that_finished_unwatched(self):
        renderer = FakeRenderer()
        generate = replay("gguf_q4_generate.json")
        job_id = generate["structuredContent"]["job_id"]
        renderer.generate(generate)
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            client.submit_render(payload, resolved)
            assert client.render_in_flight() is True

            renderer.jobs(replay("gguf_q4_job_final.json", job_id=job_id))
            state = client.refresh_render_state()

            assert state.in_flight is False
            assert state.probed is True and state.stale is False
            assert state.probe_error is None
            assert state.as_manifest()["in_flight"] is False

    def test_refresh_keeps_the_signal_true_when_the_probe_fails(self):
        renderer = FakeRenderer()
        renderer.generate(replay("gguf_q4_generate.json"))
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            client.submit_render(payload, resolved)
            job_ids = client.active_job_ids()

        state = client.refresh_render_state()  # server is gone

        assert state.in_flight is True
        assert state.stale is True
        assert state.probe_error
        assert set(state.jobs) == set(job_ids)

    def test_refresh_can_probe_a_specific_subset(self):
        renderer = FakeRenderer()
        first = replay("gguf_q4_generate.json")
        first_id = first["structuredContent"]["job_id"]
        renderer.generate(first, replay("gguf_q4_generate.json", job_id="job-second"))
        renderer.jobs(replay("gguf_q4_job_final.json", job_id=first_id))
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            client.submit_render(payload, resolved)
            second = client.submit_render(payload, resolved)

            state = client.refresh_render_state(job_ids=[second.job_id])

            assert state.probed is True and state.stale is False
            assert set(state.jobs) == set(client.active_job_ids())

    def test_forget_job_is_the_escape_hatch_for_an_out_of_band_kill(self):
        renderer = FakeRenderer()
        generate = replay("gguf_q4_generate.json")
        job_id = generate["structuredContent"]["job_id"]
        renderer.generate(generate)
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            client.submit_render(payload, resolved)

            assert client.forget_job(job_id) is True
            assert client.forget_job(job_id) is False
            assert client.render_in_flight() is False

    def test_render_state_manifest_lists_in_flight_jobs(self):
        renderer = FakeRenderer()
        generate = replay("gguf_q4_generate.json")
        job_id = generate["structuredContent"]["job_id"]
        renderer.generate(generate)
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            client.submit_render(payload, resolved)
            manifest = client.render_state().as_manifest()

        assert manifest == {
            "in_flight": True,
            "jobs": {job_id: "running"},
            "probed": False,
            "stale": False,
            "probe_error": None,
        }
        assert client.render_state().job_ids == (job_id,)


# --------------------------------------------------------------------------- thread safety


class TestConcurrentAccess:
    def test_signal_reads_stay_consistent_while_jobs_are_submitted(self):
        # The router reads the signal while the render thread submits, so each
        # read must be a coherent snapshot. Cross-call equality is NOT asserted
        # (a submit can land between two calls); snapshot self-consistency and
        # monotonicity under submit-only activity are.
        renderer = FakeRenderer()
        # Distinct ids, as a real queue would have: 8 jobs in flight, not 1.
        renderer.generate(*[replay("gguf_q4_generate.json", job_id=f"job-{i}") for i in range(8)])
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            errors: list[BaseException] = []
            stop = threading.Event()

            def reader() -> None:
                seen_busy = False
                try:
                    while not stop.is_set():
                        state = client.render_state()
                        # One snapshot is internally consistent.
                        assert state.in_flight == bool(state.jobs)
                        assert bool(state.job_ids) == state.in_flight
                        assert client.is_busy() == client.render_in_flight()
                        # No job reaches a terminal state here, so busy is sticky.
                        if state.in_flight:
                            seen_busy = True
                        assert not (seen_busy and not state.in_flight)
                except BaseException as exc:  # pragma: no cover - failure path
                    errors.append(exc)

            thread = threading.Thread(target=reader, daemon=True)
            thread.start()
            try:
                for _ in range(8):
                    client.submit_render(payload, resolved)
            finally:
                stop.set()
                thread.join(timeout=5)

        assert errors == []
        assert client.render_in_flight() is True
        assert len(client.active_job_ids()) == 8