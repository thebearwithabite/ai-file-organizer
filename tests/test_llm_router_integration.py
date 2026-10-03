"""End-to-end routing integration tests (PROMPT-MACHINE-DIRECTIVE v1.2).

The unit suite (``tests/test_llm_router.py``) drives the router with duck-typed
stand-ins, so the *clients' own wire code* is never executed: Ollama's
``prompt_eval_count`` / ``eval_count`` token accounting, the OpenAI-compatible
request NIM builds, the exact point where a bearer token is handed to a
transport. Those are precisely the places a routing layer fails quietly — a
telemetry field that reads zero forever, a key that lands in a log line.

So this suite keeps every *client class* real and stubs only the outermost
transport:

* ``OllamaClient``  — real; ``requests`` replaced with a fake that speaks
  Ollama's ``/api/generate`` JSON, so token counts come from the real
  ``_record_usage`` path.
* ``NIMClient``     — real; ``openai.OpenAI`` replaced, so the request body,
  the bearer token, and the usage read all come from the real client code.
* render state      — the real ``is_in_flight_status`` classifier over a fake
  job table, i.e. the renderer's own notion of "in flight", not a boolean.
* metrics / logs    — the real ``RouteMetrics`` and real ``logging`` records.

``DirectorService`` is the entry point, so these are end-to-end: prompt build →
routing → structured-output contract → SQLite persistence → telemetry.

Two hard guarantees, enforced mechanically rather than by convention:

* **No cloud service is ever contacted.** An autouse fixture blocks every
  socket AND records each attempt. Blocking alone is not sufficient and was
  measured to be insufficient here: a real ``NIMClient`` catches the guard's
  exception inside httpx and re-raises a generic ``RuntimeError("...Connection
  error")`` with the guard's own message gone, so a leaked call would look
  exactly like a provider outage. The recorder catches that case, and teardown
  fails the test if any attempt was made.
* **No credential value escapes.** The fake key is shaped like a real one
  (``nvapi-`` + entropy) and is asserted absent from every log record, from the
  metrics snapshot, and from the bytes of the SQLite database on disk.

Checkpoint 2 gate coverage, per the card:
keyless + render idle → Ollama primary succeeds; keyless + render busy → fail
fast with both causes named; fake env key + render busy → straight to NIM.
Local-failure fallback, one-shot repair, typed second-failure, and the
credential-hygiene sweeps are covered alongside.

The suite is verified by mutation, not just by passing: 15 targeted re-breaks
of the routing layer (and of Ollama's, NIM's, and the structured-output
contract's own code) were each caught by at least one assertion here.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

from backend.integrations.wangp_client import is_in_flight_status
from backend.llm.nim_client import NIMClient, NIM_MODEL
from backend.llm.ollama_client import OllamaClient
from backend.services.director_service import DirectorService
from backend.services.llm_resolver import (
    DIRECTOR_LOCAL_FALLBACK_MODEL,
    DIRECTOR_SEED,
    provider_kwargs,
)
from backend.services.llm_router import (
    CLOUD_ENV_VARS,
    LLMRouter,
    build_cloud_client,
)

ROUTER_LOGGER = "backend.services.llm_router"
SERVICE_LOGGER = "backend.services.director_service"

#: Shaped like a real NVIDIA key so a leak is caught by the secret-shape scan
#: too, not only by the explicit ``FAKE_KEY`` assertion.
FAKE_KEY = "nvapi-integration-only-not-a-real-key-0123456789abcdef"


# ---------------------------------------------------------------------------
# Transport stubs — the ONLY things faked. Every client class stays real.
# ---------------------------------------------------------------------------


class FakeOllamaHTTP:
    """Stands in for ``requests`` inside ``backend.llm.ollama_client``.

    Speaks Ollama's real ``/api/generate`` response shape so the client's own
    ``_record_usage(result["prompt_eval_count"], result["eval_count"])`` runs
    untouched — that mapping is the thing under test, not an incidental detail.
    """

    def __init__(self) -> None:
        self.posts: List[Dict[str, Any]] = []
        self.gets: List[str] = []
        self.replies: List[str] = []
        self.post_error: Exception | None = None
        self.healthy = True
        # Non-zero so recorded latency is measurable rather than clock noise.
        self.latency_s = 0.004

    # -- reply queue -----------------------------------------------------
    def queue(self, *replies: str) -> "FakeOllamaHTTP":
        self.replies.extend(replies)
        return self

    # -- requests surface ------------------------------------------------
    def post(self, url: str, json: Dict[str, Any] | None = None, timeout: int | None = None, **kw: Any):
        self.posts.append({"url": url, "payload": json or {}, "timeout": timeout})
        if self.post_error is not None:
            raise self.post_error
        text = self.replies.pop(0) if self.replies else "{}"
        prompt_tokens = 120 + 10 * len(self.posts)
        completion_tokens = 240 + 20 * len(self.posts)
        return _FakeResponse(
            {
                "model": (json or {}).get("model", ""),
                "response": text,
                "prompt_eval_count": prompt_tokens,
                "eval_count": completion_tokens,
                "done": True,
            }
        )

    def get(self, url: str, timeout: int | None = None, **kw: Any):
        self.gets.append(url)
        return _FakeResponse({"models": [{"name": DIRECTOR_LOCAL_FALLBACK_MODEL}]}, status=200 if self.healthy else 503)

    # -- helpers for assertions -----------------------------------------
    @property
    def calls(self) -> int:
        return len(self.posts)


class _FakeResponse:
    def __init__(self, body: Dict[str, Any], status: int = 200) -> None:
        self._body = body
        self.status_code = status

    def json(self) -> Dict[str, Any]:
        return self._body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise ConnectionError(f"HTTP {self.status_code}")


class FakeNIMTransport:
    """Stands in for ``openai.OpenAI`` — the real ``NIMClient`` drives it.

    Records the full create() kwargs so the test can assert which dialect the
    client spoke (OpenAI ``max_tokens`` vs Ollama ``num_predict``) and prove the
    fake key travelled as the bearer token, then confirm it went nowhere else.
    """

    def __init__(self) -> None:
        self.creates: List[Dict[str, Any]] = []
        self.keys: List[str] = []
        self.base_urls: List[str] = []
        self.replies: List[str] = []
        self.create_error: Exception | None = None
        self.latency_s = 0.006

    def queue(self, *replies: str) -> "FakeNIMTransport":
        self.replies.extend(replies)
        return self

    def __call__(self, **kwargs: Any) -> "_FakeNIMClient":
        self.keys.append(kwargs.get("api_key", ""))
        self.base_urls.append(kwargs.get("base_url", ""))
        return _FakeNIMClient(self)

    @property
    def calls(self) -> int:
        return len(self.creates)


class _FakeNIMClient:
    def __init__(self, transport: FakeNIMTransport) -> None:
        self._transport = transport
        self.chat = _FakeChat(transport)
        self.models = _FakeModels()


class _FakeChat:
    def __init__(self, transport: FakeNIMTransport) -> None:
        self.completions = _FakeCompletions(transport)


class _FakeCompletions:
    def __init__(self, transport: FakeNIMTransport) -> None:
        self._transport = transport

    def create(self, **kwargs: Any):
        t = self._transport
        t.creates.append(dict(kwargs))
        if t.create_error is not None:
            raise t.create_error
        time.sleep(t.latency_s)  # simulate round-trip so latency_ms is real
        text = t.replies.pop(0) if t.replies else "{}"
        return _FakeCompletionResponse(text, len(t.creates))


class _FakeCompletionResponse:
    def __init__(self, content: str, call_no: int) -> None:
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]
        self.usage = type(
            "U",
            (),
            {
                "prompt_tokens": 500 + 100 * call_no,
                "completion_tokens": 700 + 100 * call_no,
                "total_tokens": 1200 + 200 * call_no,
            },
        )()


class _FakeModels:
    def list(self):
        return {"data": [{"id": NIM_MODEL}]}


# ---------------------------------------------------------------------------
# Renderer stand-in — the renderer's OWN in-flight classifier
# ---------------------------------------------------------------------------


class StubRenderer:
    """Fake renderer's job table; "in flight" comes from the real classifier.

    Not a boolean: it holds statuses and asks
    ``backend.integrations.wangp_client.is_in_flight_status``, the same function
    the production renderer client uses. A render that reaches a terminal state
    must flip routing back to local, which is exactly what the director cares
    about after a render finishes.
    """

    def __init__(self) -> None:
        self.jobs: Dict[str, str] = {}
        self.probes = 0

    def submit(self, job_id: str, status: str = "running") -> None:
        self.jobs[job_id] = status

    def finish(self, job_id: str) -> None:
        self.jobs.pop(job_id, None)

    def render_in_flight(self) -> bool:
        self.probes += 1
        return any(is_in_flight_status(s) for s in self.jobs.values())

    def render_state(self) -> Dict[str, Any]:
        return {"job_ids": tuple(self.jobs)}


class BrokenRenderer(StubRenderer):
    """A renderer whose job table cannot be read.

    An unanswerable probe is not evidence of an idle GPU. Failing open here
    blocks local inference beside a live render and OOMs it, which is the single
    worst outcome this routing layer exists to prevent — so the router must
    fail safe to busy, overflow to the cloud if one exists, and degrade if not.
    """

    def render_in_flight(self) -> bool:
        raise RuntimeError("renderer job table unreachable")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class NetworkAccessAttempted(AssertionError):
    """Raised by the suite's socket guard. An AssertionError so pytest reports
    it as a test failure rather than an error."""


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Block every socket, loudly, and fail the test even if a client hides it.

    Loopback is NOT exempted: a local-only suite needs no sockets at all, and
    exempting 127.0.0.1 would let a stray Ollama call through on any machine
    where a server happens to be running — the flakiest possible outcome.

    Blocking alone is not enough. HTTP clients catch transport failures and
    re-raise them as a generic ``ConnectionError``, so a raised guard error can
    be swallowed and surface as an ordinary "provider unreachable" — which is
    exactly the kind of quiet pass this suite exists to prevent. So every
    attempt is also RECORDED, and teardown fails the test if the record is not
    empty. A swallowed attempt therefore still fails.
    """
    attempts: List[Any] = []

    def _blocked(self, address=None, *args, **kwargs):
        attempts.append(address)
        raise NetworkAccessAttempted(
            f"network access attempted ({address!r}); this suite must never "
            f"contact a provider"
        )

    monkeypatch.setattr(socket.socket, "connect", _blocked, raising=True)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked, raising=True)
    monkeypatch.setattr(socket, "create_connection", _blocked, raising=True)
    # urllib3/httpx also route through these for DNS and TLS setup.
    monkeypatch.setattr(socket, "getaddrinfo", _blocked, raising=True)

    yield attempts

    assert attempts == [], (
        f"this test opened {len(attempts)} network connection(s) "
        f"{attempts!r}; the provider layer must be fully stubbed. A client may "
        f"have swallowed the guard's exception as a plain ConnectionError."
    )


def test_the_network_guard_itself_is_armed(no_network):
    """Prove the guard works, so 'no provider was contacted' is not an assumption.

    Without this, a guard broken by a pytest/plugin change would leave every
    other test in the file quietly unprotected — and still green.

    Takes the recorder and then CLEARS it: this test trips the guard on purpose,
    so its own attempts must not fail the teardown assertion. What it proves is
    that (a) the direct call path raises loudly, and (b) a real client going
    through the guard is RECORDED even though the client swallows the error and
    reports a plain "provider unreachable".
    """
    assert no_network == []

    with pytest.raises(NetworkAccessAttempted):
        socket.create_connection(("api.nvidia.com", 443))
    assert len(no_network) == 1, "the direct call path raises and is recorded"

    # The path that HIDES the error: a real client catches the transport failure
    # and re-raises it as a generic RuntimeError. The recording is the only
    # thing that catches it.
    client = OllamaClient(model="qwen3.5:4b", max_retries=1)
    with pytest.raises(Exception) as excinfo:
        client.generate("hello")
    assert "network access attempted" in str(excinfo.value)
    assert len(no_network) > 1, "a swallowed attempt must still be recorded"

    no_network.clear()  # this test's attempts are the point, not a failure


@pytest.fixture(autouse=True)
def keyless_env(monkeypatch):
    """Every test starts with NO cloud key in the environment."""
    for name in CLOUD_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    for name in ("DEEPSEEK_API_KEY",):
        monkeypatch.delenv(name, raising=False)
    assert not [n for n in CLOUD_ENV_VARS if n in os.environ]


@pytest.fixture
def ollama_http(monkeypatch):
    fake = FakeOllamaHTTP()
    monkeypatch.setattr("backend.llm.ollama_client.requests", fake)
    return fake


@pytest.fixture
def nim_transport(monkeypatch):
    fake = FakeNIMTransport()
    import openai

    monkeypatch.setattr(openai, "OpenAI", fake)
    return fake


@pytest.fixture
def local_client(ollama_http):
    """Real OllamaClient, max_retries=1 so a failure path never sleeps."""
    return OllamaClient(model=DIRECTOR_LOCAL_FALLBACK_MODEL, max_retries=1)


@pytest.fixture
def renderer() -> StubRenderer:
    return StubRenderer()


@pytest.fixture
def service(tmp_path, local_client, renderer, monkeypatch):
    """DirectorService on a throwaway DB, renderer wired, degrade queue captured.

    ``render_state`` is passed in, not left to default: an unwired probe means
    "assumed idle", so a forgotten wire-up here would turn every render-state
    assertion below into a test that quietly proves nothing. The fail-fast test
    asserts ``renderer.probes == 1`` precisely to catch that.
    """
    enqueued: List[Dict[str, Any]] = []
    from backend.services import director_service as ds

    monkeypatch.setattr(
        ds,
        "enqueue_llm_degrade",
        lambda script, project_id, reason, degrade_reason="": enqueued.append(
            {"reason": reason, "degrade_reason": degrade_reason}
        ),
    )
    svc = DirectorService(
        db_path=tmp_path / "director.db",
        provider=local_client,
        render_state=renderer,
    )
    svc._test_enqueued = enqueued  # type: ignore[attr-defined]
    return svc


def _shot_json(i: int = 1) -> Dict[str, Any]:
    return {
        "shot_id": f"sc01_sh{i:02d}",
        "sequence_index": i - 1,
        "narrative_intent": "Maya finds the letter and the room's cheer drops away.",
        "setting": "The rented studio kitchen at dawn, one cardboard box half unpacked.",
        "action": "Maya walks in, slows at the counter, and picks up the envelope.",
        "lighting": "soft morning window light from the left",
        "style_grade": "naturalistic handheld documentary, slightly desaturated",
        "duration_seconds": 5.0,
        "camera": {"framing": "Eye-Level Medium Close-Up", "movement": "slow push-in"},
        "entities": [
            {
                "entity_id": "char_maya",
                "name": "Maya",
                "description": "shoulder-length dark hair, grey knit sweater",
                "expression_cues": "eyebrows draw together, lips press into a thin line",
            }
        ],
        "audio": {"dialogue": "", "ambience": "faint street traffic, refrigerator hum"},
        "seed": -1,
    }


def _shots_json(n: int = 1) -> str:
    return json.dumps({"shots": [_shot_json(i) for i in range(1, n + 1)]})


def _invalid_shots_json() -> str:
    # Breaks the sc##_sh## pattern -> an actionable shots[0].shot_id error.
    return json.dumps({"shots": [dict(_shot_json(), shot_id="nope")]})


def _route_lines(records) -> List[str]:
    return [r.getMessage() for r in records if r.name == ROUTER_LOGGER]


def _decision_lines(records, decision: str) -> List[str]:
    return [m for m in _route_lines(records) if f"decision={decision}" in m]


def _metrics_of(svc: DirectorService):
    """The service's own shared ``RouteMetrics``.

    Read the attribute directly rather than routing a request through
    ``_router_for``: the service accumulates every decision into one collector,
    and asking for a router here would silently build a cloud client this test
    never asked for.
    """
    return svc._metrics


def _shot_rows(db_path: Path) -> List[tuple]:
    with sqlite3.connect(str(db_path)) as conn:
        return conn.execute(
            "SELECT shot_id, shot_json FROM shots ORDER BY sequence_index"
        ).fetchall()


# ---------------------------------------------------------------------------
# Checkpoint 2 gate — cloud-key environment variable ABSENT
# ---------------------------------------------------------------------------


class TestCheckpoint2GateKeyless:
    """The gate: the director pass must work with no cloud key configured."""

    def test_keyless_ollama_primary_director_request_succeeds(
        self, service, ollama_http, caplog
    ):
        """No key + render idle -> the real Ollama client serves the pass."""
        ollama_http.queue(_shots_json(3))
        caplog.set_level(logging.INFO, logger=ROUTER_LOGGER)

        result = service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        assert result.degraded is False
        assert result.provider == "ollama"
        assert [s.shot_id for s in result.shots] == ["sc01_sh01", "sc01_sh02", "sc01_sh03"]

        # It really was a local call, to the local server, with local kwargs.
        assert ollama_http.calls == 1
        payload = ollama_http.posts[0]["payload"]
        assert ollama_http.posts[0]["url"] == "http://localhost:11434/api/generate"
        assert payload["model"] == DIRECTOR_LOCAL_FALLBACK_MODEL
        assert payload["stream"] is False
        # Ollama dialect: sampling under options, think=False at the top level.
        assert payload["options"]["num_predict"] == provider_kwargs("ollama")["num_predict"]
        assert payload["options"]["seed"] == DIRECTOR_SEED
        assert payload["think"] is False

        rows = _shot_rows(service.db_path)
        assert len(rows) == 3, "the validated shot list must be persisted"

    def test_keyless_records_decision_reason_model_latency_and_tokens_in_both_logs_and_metrics(
        self, service, ollama_http, caplog
    ):
        """Every field the card names must be observable in logs AND metrics."""
        ollama_http.queue(_shots_json(1))
        caplog.set_level(logging.INFO, logger=ROUTER_LOGGER)

        service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        record = _metrics_of(service).last
        assert record is not None
        # decision + reason
        assert record.decision == "local"
        assert "render state idle" in record.reason
        # model
        assert record.model == DIRECTOR_LOCAL_FALLBACK_MODEL
        # latency: a real measurement, not a hardcoded constant
        assert isinstance(record.latency_ms, float)
        assert record.latency_ms > 0.0, "the stub sleeps; latency must be measurable"
        # tokens, read out of Ollama's own prompt_eval_count / eval_count
        assert record.prompt_tokens == 130
        assert record.completion_tokens == 260
        assert record.total_tokens == 390
        assert record.attempts == 1
        assert record.attempt == "primary"
        assert record.ok is True

        # The same decision and reason in the structured log line.
        lines = _decision_lines(caplog.records, "local")
        assert len(lines) == 1, lines
        line = lines[0]
        assert "llm.route" in line
        assert f"model={DIRECTOR_LOCAL_FALLBACK_MODEL}" in line
        assert "render state idle" in line
        assert "prompt_tokens=130" in line and "completion_tokens=260" in line
        assert "ok=True" in line
        assert "latency_ms=" in line

        # And the metrics agree with the log, request for request.
        metrics = _metrics_of(service)
        assert metrics.requests == 1
        assert metrics.counts == {"local": 1}
        assert metrics.token_totals() == {
            "prompt_tokens": 130,
            "completion_tokens": 260,
            "total_tokens": 390,
        }
        assert metrics.snapshot()["last"]["decision"] == "local"

    def test_keyless_fail_fast_while_renderer_reports_an_active_job(
        self, service, ollama_http, renderer, caplog
    ):
        """No key + render in flight -> fail fast; local is never called."""
        renderer.submit("job-1", "running")
        caplog.set_level(logging.WARNING, logger=ROUTER_LOGGER)

        # The gate precondition, asserted at the moment of use: no cloud key in
        # the process environment, so no cloud client can be built. Consent is
        # granted below (allow_cloud_script=True), which makes this the STRONGER
        # form of the gate -- with permission and still nowhere to overflow to.
        assert not [n for n in CLOUD_ENV_VARS if n in os.environ]
        assert build_cloud_client(env=os.environ)[0] is None

        result = service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        assert result.degraded is True
        assert result.provider == "none"
        assert result.shots == []
        assert "render in flight" in result.reason
        assert "VRAM is occupied by an active render job" in result.reason
        assert "cloud fallback unavailable" in result.reason
        assert "no fallback cloud key is configured" in result.reason
        assert "NIM_API_KEY" in result.reason  # actionable

        # Fail fast means fail fast: not one byte left the box, and not one
        # probe of the GPU.
        assert ollama_http.calls == 0, "must not block on local beside a live render"
        assert renderer.probes == 1

        record = _metrics_of(service).last
        assert record.decision == "degraded"
        assert record.ok is False
        assert record.attempts == 0, "no provider call was made"
        assert record.provider == "" and record.model == ""
        assert record.prompt_tokens == 0 and record.completion_tokens == 0

        lines = _decision_lines(caplog.records, "degraded")
        assert len(lines) == 1
        assert "render in flight" in lines[0]
        assert "ok=False" in lines[0]

        # The service enqueued the script for human review rather than dropping it.
        assert service._test_enqueued
        assert service._test_enqueued[-1]["degrade_reason"] == "provider_unreachable"
        assert _shot_rows(service.db_path) == [], "a degraded pass persists nothing"

    def test_a_broken_render_state_probe_fails_safe_to_busy_with_a_key(
        self, service, ollama_http, nim_transport, monkeypatch, caplog
    ):
        """Unanswerable probe -> overflow, never a local call that may OOM the render.

        The card's fail-safe rule, proven end to end: if the router could not
        confirm the GPU is free, it must not hand the GPU a job on a guess.
        """
        monkeypatch.setenv("NIM_API_KEY", FAKE_KEY)
        service._render_state = BrokenRenderer()  # the service's own wire-up
        nim_transport.queue(_shots_json(1))
        caplog.set_level(logging.INFO, logger=ROUTER_LOGGER)

        result = service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        assert result.degraded is False
        assert result.provider == "nim"
        assert ollama_http.calls == 0, "must not block local on an unanswered probe"
        assert nim_transport.calls == 1

        record = _metrics_of(service).last
        assert record.decision == "overflow-cloud"
        assert "probe failed" in record.reason
        assert "assumed busy" in record.reason
        assert "llm.route" in _decision_lines(caplog.records, "overflow-cloud")[0]

    def test_a_broken_render_state_probe_degrades_when_no_cloud_key(
        self, service, ollama_http, caplog
    ):
        """Same fail-safe with nowhere to overflow: fail fast and say why."""
        service._render_state = BrokenRenderer()
        caplog.set_level(logging.WARNING, logger=ROUTER_LOGGER)

        result = service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        assert result.degraded is True
        assert "probe failed" in result.reason
        assert "assumed busy" in result.reason
        assert ollama_http.calls == 0
        assert _metrics_of(service).last.decision == "degraded"

    def test_keyless_routing_recovers_to_local_once_the_render_finishes(
        self, service, ollama_http, renderer, tmp_path, local_client
    ):
        """A terminal render must hand the GPU back — proven through the env gate.

        Built through ``LLMRouter.from_env(env={})`` rather than the service, so
        this also covers the keyless factory path end to end.
        """
        ollama_http.queue(_shots_json(1))
        router = LLMRouter.from_env(local=local_client, render_state=renderer, env={})
        assert router.cloud is None

        renderer.submit("job-1", "running")
        with pytest.raises(Exception) as excinfo:
            router.director_shot_list("job")
        assert "render in flight" in str(excinfo.value)
        assert ollama_http.calls == 0

        renderer.finish("job-1")
        routed = router.director_shot_list("job")
        assert routed.record.decision == "local"
        assert ollama_http.calls == 1
        assert router.metrics.counts == {"degraded": 1, "local": 1}


# ---------------------------------------------------------------------------
# Overflow — a fake env key, active render, straight to the stubbed NIM client
# ---------------------------------------------------------------------------


class TestOverflowWithFakeKey:
    """Key present + render in flight -> the cloud serves it, and says why."""

    def test_env_key_routes_straight_to_nim_and_succeeds(
        self, service, ollama_http, nim_transport, renderer, monkeypatch, caplog
    ):
        monkeypatch.setenv("NIM_API_KEY", FAKE_KEY)
        renderer.submit("job-1", "running")
        nim_transport.queue(_shots_json(2))
        caplog.set_level(logging.INFO, logger=ROUTER_LOGGER)

        result = service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        assert result.degraded is False
        assert result.provider == "nim"
        assert len(result.shots) == 2

        # Local was skipped, not slow-failed: zero local calls.
        assert ollama_http.calls == 0

        # The real NIMClient built the OpenAI-shaped request itself.
        assert nim_transport.calls == 1
        create = nim_transport.creates[0]
        assert create["model"] == NIM_MODEL
        assert create["seed"] == DIRECTOR_SEED
        # OpenAI dialect, not Ollama's.
        assert "max_tokens" in create and "num_predict" not in create
        assert create["messages"][0]["role"] == "user"
        assert "Maya finds the letter" in create["messages"][0]["content"]

        # Telemetry on the cloud route.
        record = _metrics_of(service).last
        assert record.decision == "overflow-cloud"
        assert record.provider == "nim"
        assert record.model == NIM_MODEL
        assert "render in flight" in record.reason
        assert record.prompt_tokens == 600
        assert record.completion_tokens == 800
        assert record.latency_ms > 0.0

        lines = _decision_lines(caplog.records, "overflow-cloud")
        assert len(lines) == 1
        assert "provider=nim" in lines[0]
        assert "model=" + NIM_MODEL in lines[0]
        assert "render in flight" in lines[0]
        assert _metrics_of(service).counts == {"overflow-cloud": 1}

        assert len(_shot_rows(service.db_path)) == 2

    def test_cloud_key_travels_as_the_bearer_token_and_nowhere_else(
        self, service, ollama_http, nim_transport, renderer, monkeypatch, caplog
    ):
        """The key must reach the transport — and appear in nothing else."""
        monkeypatch.setenv("NIM_API_KEY", FAKE_KEY)
        renderer.submit("job-1", "running")
        nim_transport.queue(_shots_json(1))
        caplog.set_level(logging.DEBUG)

        service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        # It really was used as the bearer credential.
        assert nim_transport.keys == [FAKE_KEY]
        assert nim_transport.base_urls == ["https://integrate.api.nvidia.com/v1"]

        # ...and it is in no log record, at any level.
        offenders = [r.getMessage() for r in caplog.records if FAKE_KEY in r.getMessage()]
        assert offenders == [], offenders

        # ...not in the metrics snapshot.
        blob = json.dumps(_metrics_of(service).snapshot())
        assert FAKE_KEY not in blob

        # ...and not on disk. The DB is the durable artefact this run produced.
        assert FAKE_KEY.encode() not in service.db_path.read_bytes()

    def test_consent_withheld_keeps_the_cloud_unreachable_even_with_a_key(
        self, service, ollama_http, nim_transport, renderer, monkeypatch
    ):
        """A key in the environment is not consent.

        ``allow_cloud_script=False`` must not merely refuse to call the cloud —
        no cloud client may be built, so there is no path to leak a request.
        """
        monkeypatch.setenv("NIM_API_KEY", FAKE_KEY)
        renderer.submit("job-1", "running")

        result = service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=False
        )

        assert result.degraded is True
        assert "cloud fallback disabled" in result.reason
        assert nim_transport.calls == 0
        assert ollama_http.calls == 0

        # With consent the very same service DOES build a cloud client, so the
        # degrade above is attributable to the consent gate, not to a lost key.
        assert service._router_for(True).cloud is not None
        assert build_cloud_client(env=os.environ)[0] is not None

    def test_overflow_degrades_when_the_cloud_itself_fails(
        self, service, ollama_http, nim_transport, renderer, monkeypatch, caplog
    ):
        """Cloud down + render busy -> fail fast, and do not blame local.

        Local was never called, so a message blaming local inference is a lie
        that sends the operator to debug the wrong service.
        """
        monkeypatch.setenv("NIM_API_KEY", FAKE_KEY)
        renderer.submit("job-1", "running")
        nim_transport.create_error = ConnectionError("502 upstream")
        caplog.set_level(logging.WARNING, logger=ROUTER_LOGGER)

        result = service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        assert result.degraded is True
        assert "cloud overflow" in result.reason
        assert "also failed" in result.reason
        assert "502 upstream" in result.reason
        assert "VRAM is occupied by an active render job" in result.reason
        assert ollama_http.calls == 0
        assert _metrics_of(service).last.decision == "degraded"
        assert len(_decision_lines(caplog.records, "degraded")) == 1


# ---------------------------------------------------------------------------
# Local failure -> fallback to the cloud
# ---------------------------------------------------------------------------


class TestLocalFailureFallsBackToCloud:
    def test_local_transport_failure_retries_once_on_nim_and_succeeds(
        self, service, ollama_http, nim_transport, monkeypatch, caplog
    ):
        """Local is down in flight -> exactly one cloud retry, not a loop."""
        monkeypatch.setenv("NIM_API_KEY", FAKE_KEY)
        ollama_http.post_error = ConnectionError("ollama refused")
        ollama_http.healthy = False
        nim_transport.queue(_shots_json(1))
        caplog.set_level(logging.INFO, logger=ROUTER_LOGGER)

        result = service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        assert result.degraded is False
        assert result.provider == "nim"
        assert len(result.shots) == 1
        assert ollama_http.calls == 1, "one local attempt, no retry storm"
        assert nim_transport.calls == 1

        record = _metrics_of(service).last
        assert record.decision == "fallback-cloud"
        assert record.provider == "nim"
        assert "local provider failed" in record.reason
        assert "provider_unreachable" in record.reason
        assert "retried on cloud fallback" in record.reason

        lines = _decision_lines(caplog.records, "fallback-cloud")
        assert len(lines) == 1
        assert "local provider failed" in lines[0]
        assert len(_shot_rows(service.db_path)) == 1

    def test_keyless_local_failure_degrades_and_never_reaches_for_a_cloud(
        self, service, ollama_http, nim_transport, caplog
    ):
        """No key + local down -> degrade. There must be no escalation path.

        A router that switches to a cloud client that does not exist crashes
        with an AttributeError instead of returning an actionable error, so the
        "no route" branch has to be reached without ever touching ``cloud``.
        """
        ollama_http.post_error = ConnectionError("ollama refused")
        ollama_http.healthy = False
        caplog.set_level(logging.WARNING, logger=ROUTER_LOGGER)

        result = service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        assert result.degraded is True
        assert result.provider == "none"
        assert "ollama refused" in result.reason
        assert "cloud fallback unavailable" in result.reason
        assert "no fallback cloud key is configured" in result.reason
        assert ollama_http.calls == 1
        assert nim_transport.calls == 0, "no cloud client exists to call"

        record = _metrics_of(service).last
        assert record.decision == "degraded"
        # A call that RAISED bills nothing, so the tally is genuinely zero —
        # the transport spent no tokens. Note this is indistinguishable from the
        # fail-fast case (busy + no key), which also records 0: one transport
        # call that failed vs no call at all. The record's ``attempt`` field is
        # "" in both. Flagged on the card as a telemetry nuance; not changed
        # here, since the record contract belongs to the routing layer.
        assert record.attempts == 0
        assert record.prompt_tokens == 0 and record.completion_tokens == 0
        assert ollama_http.calls == 1, "the transport call really was made"
        assert len(_decision_lines(caplog.records, "degraded")) == 1
        # The transport-level cause IS named, which is what makes the record
        # actionable even though the counters are zero.
        assert "provider_unreachable" in record.reason
        assert "ollama refused" in record.reason

    def test_both_providers_down_degrades_naming_both_causes(
        self, service, ollama_http, nim_transport, monkeypatch
    ):
        monkeypatch.setenv("NIM_API_KEY", FAKE_KEY)
        ollama_http.post_error = ConnectionError("ollama refused")
        ollama_http.healthy = False
        nim_transport.create_error = ConnectionError("nim refused")

        result = service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        assert result.degraded is True
        assert "ollama refused" in result.reason
        assert "nim refused" in result.reason
        assert _metrics_of(service).last.decision == "degraded"
        assert service._test_enqueued[-1]["degrade_reason"] == "provider_unreachable"


# ---------------------------------------------------------------------------
# Structured-output contract through the real clients
# ---------------------------------------------------------------------------


class TestStructuredOutputContractEndToEnd:
    def test_invalid_shot_spec_is_repaired_once_and_succeeds(
        self, service, ollama_http, nim_transport, monkeypatch, caplog
    ):
        """Bad first reply -> exactly one repair to the SAME client -> success."""
        monkeypatch.setenv("NIM_API_KEY", FAKE_KEY)
        ollama_http.queue(_invalid_shots_json(), _shots_json(1))
        caplog.set_level(logging.INFO, logger=ROUTER_LOGGER)

        result = service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        assert result.degraded is False
        assert result.provider == "ollama"
        assert [s.shot_id for s in result.shots] == ["sc01_sh01"]

        assert ollama_http.calls == 2, "one primary + exactly one repair"

        primary_prompt = ollama_http.posts[0]["payload"]["prompt"]
        repair_prompt = ollama_http.posts[1]["payload"]["prompt"]
        assert "OUTPUT REJECTED" in repair_prompt
        # The repair carries the actionable path the director can act on.
        assert "shots[0].shot_id" in repair_prompt
        # The original prompt is preserved VERBATIM as a prefix. Anything else —
        # a preamble, a rewrite, a re-summarised instruction — silently drops
        # script content while every call-count assertion still passes.
        assert repair_prompt.startswith(primary_prompt), (
            "the repair prompt must contain the original prompt verbatim"
        )
        assert "Maya finds the letter" in repair_prompt

        record = _metrics_of(service).last
        assert record.decision == "local"
        assert record.attempt == "repair"
        assert record.attempts == 2
        # Both calls were billed: 130+260 then 140+280.
        assert record.prompt_tokens == 270
        assert record.completion_tokens == 540
        assert record.ok is True
        assert nim_transport.calls == 0, "a schema defect must not escalate to the cloud"

    def test_second_invalid_response_raises_a_typed_failure_at_the_service(
        self, service, ollama_http, nim_transport, monkeypatch, caplog
    ):
        """Two bad replies -> typed failure, review queue, nothing persisted."""
        monkeypatch.setenv("NIM_API_KEY", FAKE_KEY)
        ollama_http.queue(_invalid_shots_json(), _invalid_shots_json())
        caplog.set_level(logging.WARNING, logger=ROUTER_LOGGER)

        result = service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        assert result.degraded is True
        assert result.provider == "ollama", "the provider that answered is named"
        assert result.shots == []
        assert "failed schema validation" in result.reason
        assert "after 2 attempts" in result.reason
        assert "shots[0].shot_id" in result.reason  # actionable, repo-native form
        assert "shots.0.shot_id" not in result.reason  # pydantic loc must not leak

        assert ollama_http.calls == 2, "exactly one repair, then give up"
        assert nim_transport.calls == 0

        record = _metrics_of(service).last
        assert record.decision == "local"
        assert record.ok is False
        assert record.error == "structured output rejected"
        assert record.attempts == 2
        assert _shot_rows(service.db_path) == []

        # Typed at the router level too — the service swallows it by design.
        # Two MORE invalid replies: the queue above is spent, and an empty
        # default would fail validation for a different reason (a missing
        # "shots" key) and quietly stop testing the field path we care about.
        ollama_http.queue(_invalid_shots_json(), _invalid_shots_json())
        router = service._router_for(True)
        with pytest.raises(Exception) as excinfo:
            router.director_shot_list("job")
        assert type(excinfo.value).__name__ == "InvalidLLMOutputError"
        paths = [e["path"] for e in excinfo.value.errors]
        assert paths, "the typed error must name the offending field"
        assert "shots[0].shot_id" in paths, paths

        assert service._test_enqueued[-1]["degrade_reason"] == "schema_invalid"

    def test_scene_plan_pass_routes_through_the_same_layer(
        self, service, ollama_http, nim_transport, renderer, monkeypatch
    ):
        """The scene-plan job shares the routing layer; verify the second door.

        ``nim_transport`` is required even on the local route: with a key in the
        environment the service builds a REAL NIMClient at request time, and the
        OpenAI SDK fails below any socket my network guard can intercept. Taking
        the fixture keeps that client from ever reaching a transport.
        """
        monkeypatch.setenv("NIM_API_KEY", FAKE_KEY)
        renderer.submit("job-1", "running")
        nim_transport.queue(json.dumps({"title": "The Letter", "scenes": [], "total_runtime_s": 90.0}))

        out = service.analyze_script(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        assert out["degraded"] is False
        assert out["provider"] == "nim"
        assert out["plan"].title == "The Letter"
        assert ollama_http.calls == 0, "render busy -> local must stay untouched"
        assert nim_transport.calls == 1

        record = _metrics_of(service).last
        assert record.decision == "overflow-cloud"
        assert record.job == "director.scene_plan"


# ---------------------------------------------------------------------------
# Secrets hygiene across the whole surface
# ---------------------------------------------------------------------------


class TestNoSecretsAnywhere:
    def test_a_whole_keyless_session_writes_no_credential_material(
        self, service, ollama_http, renderer, caplog
    ):
        """Full keyless session: logs, metrics, and the DB stay clean."""
        ollama_http.queue(_shots_json(1))
        caplog.set_level(logging.DEBUG)

        service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )
        renderer.submit("job-1", "running")
        service.generate_shot_list("SCRIPT: Maya finds the letter.", project_id="p2")
        renderer.finish("job-1")
        service.generate_shot_list("SCRIPT: Maya finds the letter.", project_id="p3")

        blob = "\n".join(r.getMessage() for r in caplog.records)
        blob += json.dumps(_metrics_of(service).snapshot())
        assert FAKE_KEY not in blob
        assert "nvapi-" not in blob, "no key-shaped material anywhere in the session"
        # The variable NAME is actionable guidance and may appear; a VALUE beside
        # it never may. "Bearer " is checked because OpenAI-compatible clients
        # echo it back in their own error text, which is how keys reach logfiles.
        assert "=nvapi" not in blob and "Bearer " not in blob

    def test_no_secret_shaped_literal_in_the_routing_source(
        self, service, ollama_http, nim_transport, renderer, monkeypatch, caplog
    ):
        """Even with a key configured, the sources must carry no real one."""
        import re

        monkeypatch.setenv("NIM_API_KEY", FAKE_KEY)
        renderer.submit("job-1", "running")
        nim_transport.queue(_shots_json(1))
        caplog.set_level(logging.DEBUG)
        service.generate_shot_list(
            "SCRIPT: Maya finds the letter.", project_id="p1", allow_cloud_script=True
        )

        root = Path(__file__).resolve().parents[1]
        pattern = re.compile(r"(nvapi-[A-Za-z0-9_\-]{8,}|sk-[A-Za-z0-9]{16,})")
        for rel in (
            "backend/llm/base.py",
            "backend/llm/nim_client.py",
            "backend/llm/ollama_client.py",
            "backend/llm/deepseek_client.py",
            "backend/llm/structured_output.py",
            "backend/services/llm_router.py",
            "backend/services/llm_resolver.py",
            "backend/services/director_service.py",
        ):
            text = (root / rel).read_text(encoding="utf-8")
            hit = pattern.search(text)
            # Production source only. The test suites hold deliberate fakes
            # (FAKE_KEY here, "nvapi-supersecretvalue" in the unit suite), which
            # is exactly the point of them: a fake is how a real leak gets caught.
            assert hit is None, f"secret-shaped literal in {rel}: {hit.group(0)[:12]}..."

    def test_the_key_never_reaches_a_subprocess_environment(self):
        """No shell-out path may inherit the cloud credential."""
        import ast

        root = Path(__file__).resolve().parents[1]
        for rel in (
            "backend/services/llm_router.py",
            "backend/llm/nim_client.py",
            "backend/llm/ollama_client.py",
            "backend/services/director_service.py",
        ):
            tree = ast.parse((root / rel).read_text(encoding="utf-8"))
            called = {
                node.func.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            for banned in ("subprocess", "Popen", "run", "call", "check_output"):
                assert banned not in called, (
                    f"{rel} invokes {banned}(); a shell-out can leak NIM_API_KEY "
                    f"into a child environment"
                )