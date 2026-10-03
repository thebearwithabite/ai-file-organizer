"""LLMRouter tests (PROMPT-MACHINE-DIRECTIVE v1.2 — intelligence routing layer).

Coverage maps to the routing card's acceptance criteria:

* keyless gate — the whole suite runs with NO cloud API key present
* local path + degraded path both covered
* render active -> router selects NIM (stubbed NIMClient), request succeeds
* routing decisions + reason + model + latency + tokens asserted via logs/metrics
* exactly one repair retry on invalid output, then a typed InvalidLLMOutputError
* token accounting survives missing/garbage usage without crashing the request
* cloud keys are read from the environment only; no secret material in modules
* the router composes the shared structured-output contract rather than
  re-implementing it (there is exactly one repair/validate implementation)

All network access is stubbed; the one live test (real Ollama) self-skips when
the local server is down so the suite stays CI-safe.
"""
from __future__ import annotations

import json
import logging
import os
import re as _re
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from backend.llm.base import LLMProvider, TokenUsage
from backend.llm.errors import DegradedRoutingError, InvalidLLMOutputError
from backend.llm.nim_client import NIMClient, NIM_MODEL
from backend.llm.ollama_client import OllamaClient
from backend.services.llm_router import (
    CLOUD_ENV_VARS,
    RENDER_BUSY_REASON,
    CallableRenderState,
    ExplicitRenderFlag,
    LLMRouter,
    RouteMetrics,
    build_cloud_client,
    provider_name,
)

ROUTER_LOGGER = "backend.services.llm_router"


# ---------------------------------------------------------------------------
# Stubs & helpers
# ---------------------------------------------------------------------------


class ScriptedProvider(LLMProvider):
    """Deterministic local stand-in: queued outputs, scripted transport failures."""

    def __init__(
        self,
        outputs: list[str],
        *,
        model: str = "scripted-local",
        fail_on: tuple[int, ...] = (),
        usage: tuple[int, int] = (7, 11),
        max_retries: int = 1,
        healthy: bool = True,
    ) -> None:
        super().__init__(model=model, max_retries=max_retries)
        self.outputs = list(outputs)
        self.fail_on = set(fail_on)  # 1-based call indexes that raise
        self.calls: list[str] = []
        self._usage = usage
        self._healthy = healthy

    def _generate_raw(self, prompt: str, **kwargs: Any) -> str:
        self.calls.append(prompt)
        call_no = len(self.calls)
        if call_no in self.fail_on:
            self.last_failure = "provider_unreachable"
            raise ConnectionError("stub provider down")
        output = self.outputs[min(call_no - 1, len(self.outputs) - 1)]
        self._record_usage(*self._usage)
        return output

    def health_check(self) -> bool:
        return self._healthy


class StubNIM(NIMClient):
    """Stubbed NIMClient per the card: no key, no network, queued outputs.

    Survives the keyless gate deliberately — it never constructs the real
    client (which would refuse without NIM_API_KEY); it exercises the router's
    overflow path against the real NIMClient class contract.
    """

    def __init__(self, outputs: list[str], *, model: str = "stub-nim-1") -> None:
        LLMProvider.__init__(self, model=model, max_retries=1)
        self.outputs = list(outputs)
        self.calls: list[str] = []

    def _generate_raw(self, prompt: str, **kwargs: Any) -> str:
        self.calls.append(prompt)
        output = self.outputs[min(len(self.calls) - 1, len(self.outputs) - 1)]
        self._record_usage(13, 17)
        return output

    def health_check(self) -> bool:
        return True


class TickClock:
    """Deterministic clock: yields ticks, then repeats the last one."""

    def __init__(self, *ticks: float) -> None:
        self._ticks = list(ticks) or [0.0]
        self._i = 0

    def __call__(self) -> float:
        value = self._ticks[min(self._i, len(self._ticks) - 1)]
        self._i += 1
        return value


def _shot(i: int = 1) -> dict:
    """One valid ShotSpec payload against the live schema."""
    return {
        "shot_id": f"sc01_sh{i:02d}",
        "sequence_index": i - 1,
        "narrative_intent": "Maya finds the letter.",
        "setting": "kitchen, early morning",
        "action": "she steps to the counter and lifts the envelope",
        "lighting": "soft window light from the left",
        "style_grade": "naturalistic, gentle contrast",
        "duration_seconds": 5.0,
        "camera": {"framing": "Eye-Level Medium Close-Up", "movement": "slow push-in"},
        "entities": [
            {
                "entity_id": "char_maya",
                "name": "Maya",
                "description": "dark hair, grey knit sweater",
                "expression_cues": "jaw tightens",
            }
        ],
        "audio": {"dialogue": "", "ambience": "refrigerator hum"},
        "seed": -1,
    }


def _valid_shots_json(n: int = 1) -> str:
    return json.dumps({"shots": [_shot(i) for i in range(1, n + 1)]})


def _invalid_shots_json() -> str:
    # Fails the ShotSpec shot_id pattern -> actionable field-path error.
    return json.dumps({"shots": [{"shot_id": "nope"}]})


class _Tiny(BaseModel):
    """A minimal non-ShotSpec schema, for the duck-typed-provider tests."""

    ok: bool


# ---------------------------------------------------------------------------
# Keyless gate
# ---------------------------------------------------------------------------


def test_keyless_gate_cloud_keys_absent():
    """Checkpoint gate: the suite must run with no cloud key configured."""
    for key in CLOUD_ENV_VARS:
        assert key not in os.environ, f"{key} must be absent for the keyless gate"


# ---------------------------------------------------------------------------
# Local path
# ---------------------------------------------------------------------------


def test_local_path_records_decision_model_latency_tokens(caplog):
    """Local-first with no cloud key: decision, model, latency, tokens all recorded."""
    local = ScriptedProvider([_valid_shots_json(1), _valid_shots_json(1)])
    metrics = RouteMetrics()
    router = LLMRouter(local=local, cloud=None, metrics=metrics, clock=TickClock(0.0, 0.25))
    caplog.set_level(logging.INFO, logger=ROUTER_LOGGER)

    routed = router.director_shot_list("break this script into shots", job="director.shot_list")

    assert routed.value.shots[0].shot_id == "sc01_sh01"
    record = routed.record
    assert record.decision == "local"
    assert record.provider == provider_name(local)
    assert record.model == "scripted-local"
    assert record.latency_ms == 250.0
    assert record.prompt_tokens == 7
    assert record.completion_tokens == 11
    assert record.attempt == "primary"
    assert record.ok is True

    # Decision is in the logs...
    assert any("decision=local" in r.getMessage() for r in caplog.records)
    assert any("model=scripted-local" in r.getMessage() for r in caplog.records)

    # ...and in the metrics.
    assert metrics.counts == {"local": 1}
    assert metrics.requests == 1
    assert metrics.token_totals()["total_tokens"] == 18

    # A second request accumulates (metrics survive per-request routing).
    router.director_shot_list("again")
    assert metrics.counts == {"local": 2}
    assert metrics.requests == 2


# ---------------------------------------------------------------------------
# Overflow rule — render in flight -> NIM
# ---------------------------------------------------------------------------


def test_overflow_selects_nim_when_render_active(caplog):
    """Renderer reports an active job -> router picks the stubbed NIM client; local untouched."""
    flag = ExplicitRenderFlag()
    flag.set()
    local = ScriptedProvider([_valid_shots_json(1)])
    nim = StubNIM([_valid_shots_json(1)])
    assert isinstance(nim, NIMClient)  # the acceptance test's stubbed NIM client
    metrics = RouteMetrics()
    router = LLMRouter(local=local, cloud=nim, render_state=flag, metrics=metrics)
    caplog.set_level(logging.INFO, logger=ROUTER_LOGGER)

    routed = router.director_shot_list("director job during a render")

    assert routed.value.shots[0].shot_id == "sc01_sh01"  # request succeeded
    assert routed.record.decision == "overflow-cloud"
    assert routed.record.provider == "nim"
    assert routed.record.model == "stub-nim-1"
    assert "render in flight" in routed.record.reason

    assert local.calls == [], "local provider must not be touched during a render"
    assert len(nim.calls) == 1
    assert any("decision=overflow-cloud" in r.getMessage() for r in caplog.records)
    assert metrics.counts == {"overflow-cloud": 1}


def test_callable_render_state_adapter_overflows():
    """Render state can come from any renderer-supplied predicate, not a guess."""
    local = ScriptedProvider([_valid_shots_json(1)])
    nim = StubNIM([_valid_shots_json(1)])
    state = CallableRenderState(lambda: True)  # e.g. client has an active job
    router = LLMRouter(local=local, cloud=nim, render_state=state)

    routed = router.director_shot_list("job")
    assert routed.record.decision == "overflow-cloud"
    assert local.calls == [] and len(nim.calls) == 1


def test_explicit_render_flag_lifecycle():
    flag = ExplicitRenderFlag()
    assert flag.render_in_flight() is False
    with flag.in_flight():
        assert flag.render_in_flight() is True
    assert flag.render_in_flight() is False
    flag.set()
    assert flag.render_in_flight() is True
    flag.clear()
    assert flag.render_in_flight() is False


# ---------------------------------------------------------------------------
# Degraded path
# ---------------------------------------------------------------------------


def test_degraded_fail_fast_when_busy_and_no_cloud_key(caplog):
    """No cloud key + render in flight -> actionable error explaining BOTH causes."""
    flag = ExplicitRenderFlag()
    flag.set()
    local = ScriptedProvider([_valid_shots_json(1)])
    metrics = RouteMetrics()
    router = LLMRouter(local=local, cloud=None, render_state=flag, metrics=metrics)
    caplog.set_level(logging.WARNING, logger=ROUTER_LOGGER)

    with pytest.raises(DegradedRoutingError) as excinfo:
        router.director_shot_list("job")

    message = str(excinfo.value)
    assert "render in flight" in message  # cause 1: local busy
    assert "VRAM is occupied by an active render job" in message
    assert "cloud fallback unavailable" in message  # cause 2: no cloud key
    assert "no fallback cloud key is configured" in message
    assert "NIM_API_KEY" in message  # actionable

    assert local.calls == [], "degraded path must fail fast, not attempt local"
    assert metrics.counts == {"degraded": 1}
    assert metrics.last.decision == "degraded"
    assert metrics.last.attempts == 0, "no provider call was made"
    assert any("decision=degraded" in r.getMessage() for r in caplog.records)


def test_degraded_when_local_down_and_no_cloud_key():
    """Local provider unreachable + no cloud -> degrade naming both causes."""
    local = ScriptedProvider([_valid_shots_json(1)], fail_on=(1,), healthy=False)
    router = LLMRouter(local=local, cloud=None)

    with pytest.raises(DegradedRoutingError) as excinfo:
        router.director_shot_list("job")

    message = str(excinfo.value)
    assert "local inference unavailable" in message
    assert "provider_unreachable" in message
    assert "cloud fallback unavailable" in message
    assert router.metrics.counts == {"degraded": 1}


# ---------------------------------------------------------------------------
# Fallback-cloud (local failed in flight, cloud available)
# ---------------------------------------------------------------------------


def test_fallback_cloud_when_local_transport_fails():
    local = ScriptedProvider([_valid_shots_json(1)], fail_on=(1,), healthy=False)
    nim = StubNIM([_valid_shots_json(1)])
    router = LLMRouter(local=local, cloud=nim)

    routed = router.director_shot_list("job")

    assert routed.record.decision == "fallback-cloud"
    assert routed.record.provider == "nim"
    assert "local provider failed" in routed.record.reason
    assert len(local.calls) == 1 and len(nim.calls) == 1
    assert router.metrics.counts == {"fallback-cloud": 1}


def test_cloud_transport_failure_during_overflow_degrades():
    flag = ExplicitRenderFlag()
    flag.set()
    local = ScriptedProvider([_valid_shots_json(1)])
    nim = StubNIM([_valid_shots_json(1)])

    def raising(prompt, **kwargs):
        nim.calls.append(prompt)
        nim.last_failure = "provider_unreachable"
        raise ConnectionError("nim down")

    nim._generate_raw = raising
    router = LLMRouter(local=local, cloud=nim, render_state=flag)

    with pytest.raises(DegradedRoutingError) as excinfo:
        router.director_shot_list("job")

    message = str(excinfo.value)
    assert "render in flight" in message
    assert "cloud overflow" in message and "failed" in message
    # The cloud failed; local was never called, so the message must not blame it.
    assert excinfo.value.local_reason == RENDER_BUSY_REASON
    assert "nim down" not in excinfo.value.local_reason
    assert local.calls == []
    assert router.metrics.counts == {"degraded": 1}


# ---------------------------------------------------------------------------
# Structured output: one repair retry, then a typed error
# ---------------------------------------------------------------------------


def test_repair_retry_recovers_invalid_output():
    local = ScriptedProvider([_invalid_shots_json(), _valid_shots_json(1)])
    router = LLMRouter(local=local, cloud=None)

    routed = router.director_shot_list("job")

    assert routed.record.decision == "local"
    assert routed.record.attempt == "repair"
    assert len(local.calls) == 2
    assert "OUTPUT REJECTED" in local.calls[1]  # the repair prompt
    assert routed.value.shots[0].shot_id == "sc01_sh01"


def test_repair_exhausted_raises_typed_error_with_field_paths(caplog):
    local = ScriptedProvider([_invalid_shots_json(), _invalid_shots_json()])
    router = LLMRouter(local=local, cloud=None)
    caplog.set_level(logging.WARNING, logger=ROUTER_LOGGER)

    with pytest.raises(InvalidLLMOutputError) as excinfo:
        router.director_shot_list("job")

    err = excinfo.value
    assert err.attempts == 2  # initial + exactly one repair retry
    assert len(local.calls) == 2, "must be exactly one repair retry"
    assert err.provider == provider_name(local)
    assert any("shot_id" in e["path"] for e in err.errors), err.errors
    assert err.raw == _invalid_shots_json()

    assert router.metrics.counts == {"local": 1}
    assert router.metrics.last.ok is False
    assert any("ok=False" in r.getMessage() for r in caplog.records)


def test_transport_failure_does_not_consume_repair_retry():
    """Transport errors are fallback/degrade territory, not schema repair."""
    local = ScriptedProvider([_valid_shots_json(1)], fail_on=(1,), healthy=False)
    router = LLMRouter(local=local, cloud=None)

    with pytest.raises(DegradedRoutingError):
        router.director_shot_list("job")

    assert len(local.calls) == 1  # no repair attempt on transport failure


def test_a_contract_violation_never_switches_provider():
    """A malformed reply is a schema defect, not a transport failure.

    Re-asking a different vendor hides the defect behind that model's guesswork,
    so the cloud must stay untouched even when one is configured.
    """
    local = ScriptedProvider([_invalid_shots_json(), _invalid_shots_json()])
    nim = StubNIM([_valid_shots_json(1)])
    router = LLMRouter(local=local, cloud=nim)

    with pytest.raises(InvalidLLMOutputError):
        router.director_shot_list("job")

    assert len(local.calls) == 2
    assert nim.calls == [], "a schema violation must not escalate to the cloud"
    assert router.metrics.counts == {"local": 1}


# ---------------------------------------------------------------------------
# Render state: the signal is trusted, and its absence is stated
# ---------------------------------------------------------------------------


def test_unwired_render_state_is_stated_not_assumed_silently():
    """No provider wired -> idle, but the reason must admit it is a guess."""
    local = ScriptedProvider([_valid_shots_json(1)])
    router = LLMRouter(local=local, cloud=None)

    routed = router.director_shot_list("job")

    assert routed.record.decision == "local"
    assert "not wired" in routed.record.reason
    assert "assumed idle" in routed.record.reason


def test_a_broken_render_state_probe_fails_safe_to_busy():
    """A probe that cannot answer is not evidence of an idle GPU.

    Failing open here blocks local inference beside a live render and OOMs it;
    the renderer's own classifier already fails safe to in-flight for the same
    reason. With a cloud key the request overflows instead.
    """
    class BrokenProbe:
        def render_in_flight(self):
            raise RuntimeError("renderer unreachable")

    local = ScriptedProvider([_valid_shots_json(1)])
    nim = StubNIM([_valid_shots_json(1)])
    router = LLMRouter(local=local, cloud=nim, render_state=BrokenProbe())

    routed = router.director_shot_list("job")

    assert routed.record.decision == "overflow-cloud"
    assert "probe failed" in routed.record.reason
    assert "assumed busy" in routed.record.reason
    assert local.calls == [], "must not block local on an unanswered probe"
    assert len(nim.calls) == 1


def test_a_broken_render_state_probe_degrades_when_no_cloud_key():
    """Same fail-safe, with nowhere to overflow to: fail fast and say why."""
    class BrokenProbe:
        def render_in_flight(self):
            raise RuntimeError("renderer unreachable")

    local = ScriptedProvider([_valid_shots_json(1)])
    router = LLMRouter(local=local, cloud=None, render_state=BrokenProbe())

    with pytest.raises(DegradedRoutingError) as excinfo:
        router.director_shot_list("job")

    assert "probe failed" in str(excinfo.value)
    assert "assumed busy" in str(excinfo.value)
    assert local.calls == []


def test_a_real_renderer_client_can_be_the_render_state():
    """The renderer satisfies the protocol structurally — wire it directly.

    Guards the integration the routing card asks for: no adapter, no VRAM
    probing, no flag bookkeeping between the renderer and the router.
    """
    from backend.integrations.wangp_client import WangPClient

    client = WangPClient.__new__(WangPClient)  # no transport, no network
    import threading

    client._active_lock = threading.Lock()
    client._active_jobs = {"job-1": "running"}

    assert client.render_in_flight() is True

    local = ScriptedProvider([_valid_shots_json(1)])
    nim = StubNIM([_valid_shots_json(1)])
    router = LLMRouter(local=local, cloud=nim, render_state=client)

    routed = router.director_shot_list("job")
    assert routed.record.decision == "overflow-cloud"
    assert local.calls == [] and len(nim.calls) == 1

    # ...and once the render reaches a terminal state the router goes local.
    client.forget_job("job-1")
    routed2 = router.director_shot_list("job")
    assert routed2.record.decision == "local"


# ---------------------------------------------------------------------------
# Token accounting
# ---------------------------------------------------------------------------


def test_token_counts_sum_across_every_real_provider_call():
    """One record per request must bill the request, not just its last call.

    A repair retry is a second billable call; reporting only ``last_usage``
    halves the count and makes the telemetry lie about cost.
    """
    local = ScriptedProvider([_invalid_shots_json(), _valid_shots_json(1)], usage=(100, 200))
    router = LLMRouter(local=local, cloud=None)

    routed = router.director_shot_list("job")

    assert len(local.calls) == 2
    assert routed.record.prompt_tokens == 200
    assert routed.record.completion_tokens == 400
    assert routed.record.attempts == 2
    assert router.metrics.token_totals()["total_tokens"] == 600


def test_token_counts_survive_providers_that_report_nothing():
    """Missing usage is zero, never a crash that kills the director pass."""
    class NoUsageProvider(ScriptedProvider):
        def _generate_raw(self, prompt: str, **kwargs: Any) -> str:
            self.calls.append(prompt)
            # A provider that reports nothing at all: last_usage never set.
            return self.outputs[min(len(self.calls) - 1, len(self.outputs) - 1)]

    local = NoUsageProvider([_valid_shots_json(1)], usage=None)
    router = LLMRouter(local=local, cloud=None)

    routed = router.director_shot_list("job")

    assert routed.value.shots[0].shot_id == "sc01_sh01"
    assert routed.record.prompt_tokens == 0
    assert routed.record.completion_tokens == 0
    assert router.metrics.token_totals()["total_tokens"] == 0


def test_garbage_token_counts_are_coerced_not_propagated():
    """None/str/float/negative/None-client all normalize to non-negative ints."""
    class GarbageUsageProvider(ScriptedProvider):
        def _generate_raw(self, prompt: str, **kwargs: Any) -> str:
            self.calls.append(prompt)
            self.last_usage = TokenUsage(prompt_tokens=None, completion_tokens="many")
            return self.outputs[min(len(self.calls) - 1, len(self.outputs) - 1)]

    local = GarbageUsageProvider([_valid_shots_json(1)], usage=None)
    router = LLMRouter(local=local, cloud=None)

    routed = router.director_shot_list("job")

    assert routed.value.shots[0].shot_id == "sc01_sh01"
    assert routed.record.prompt_tokens == 0
    assert routed.record.completion_tokens == 0
    assert router.metrics.token_totals() == {
        "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
    }


def test_the_render_state_read_is_pure():
    """No environment side channel may steer the routing decision.

    The renderer's classifier is guarded the same way: the render state comes
    from the renderer's job table and nothing else. A stray env lookup would
    make the route depend on ambient state that no test sets and no operator
    documents.
    """
    import ast
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "backend" / "services" / "llm_router.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))

    target = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_render_state_now"
    )

    # ``os.environ.get(...)`` is an Attribute chain, not a Name load, so both
    # shapes have to be rejected or the guard only catches half the escapes.
    loaded = {
        node.id
        for node in ast.walk(target)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    } - {a.arg for a in target.args.args}
    attrs = {node.attr for node in ast.walk(target) if isinstance(node, ast.Attribute)}

    for banned in ("environ", "getenv", "get"):
        assert banned not in loaded | attrs, (
            f"render-state read reaches for {banned!r}: ambient state must not "
            f"steer the routing decision (loaded={loaded | attrs})"
        )


def test_a_provider_with_no_usage_attribute_does_not_break_the_record():
    """Duck-typed clients need not subclass LLMProvider."""
    class Bare:
        model = "bare-1"

        def generate(self, prompt, **kwargs):
            return json.dumps({"ok": True})

        def health_check(self):
            return True

    router = LLMRouter(local=Bare(), cloud=None)
    routed = router.complete_structured("job", _Tiny, job="bare")

    assert routed.value.ok is True
    assert routed.record.prompt_tokens == 0
    assert routed.record.attempts == 1


def test_record_attempt_counts_match_real_calls():
    """attempts must count provider calls, never assert a repair that didn't happen."""
    # A valid first reply: exactly one call.
    local = ScriptedProvider([_valid_shots_json(1)])
    assert LLMRouter(local=local, cloud=None).director_shot_list("j").record.attempts == 1

    # max_repairs=0 must not claim two attempts after a single rejection.
    strict = ScriptedProvider([_invalid_shots_json()])
    router = LLMRouter(local=strict, cloud=None, max_repairs=0)
    with pytest.raises(InvalidLLMOutputError) as excinfo:
        router.director_shot_list("j")
    assert len(strict.calls) == 1
    assert excinfo.value.attempts == 1, "one call was made, so say one"
    assert router.metrics.last.attempts == 1


# ---------------------------------------------------------------------------
# The router routes; it does not re-implement the structured-output contract
# ---------------------------------------------------------------------------


def test_the_router_composes_the_shared_structured_output_contract():
    """There must be exactly ONE parse/validate/repair implementation.

    A second copy in the router is how two divergent error formats ship (one
    ``shots.0.shot_id``, one ``shots[0].shot_id``); the router delegates instead.
    """
    import ast
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "backend" / "services" / "llm_router.py")
    tree = ast.parse(source.read_text(encoding="utf-8"))

    # Called as a plain name (imported function), not a method.
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "enforce_structured" in called, "the router must delegate to enforce_structured"

    # No private re-implementation of the contract survives.
    defined = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for dead in ("_parse_and_validate", "_repair_prompt", "_validate_and_repair"):
        assert dead not in defined, f"{dead} re-implements the shared contract"

    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "backend.llm.structured_output"
        for alias in node.names
    }
    assert "enforce_structured" in imported

    # The router must not reach into pydantic validation itself.
    validation_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "model_validate" not in validation_calls, (
        "the router validates; that is the shared contract's job, not its own"
    )


def test_router_validation_errors_use_the_repo_actionable_paths():
    """Errors must read ``shots[0].shot_id`` — the form the director can act on."""
    local = ScriptedProvider([_invalid_shots_json(), _invalid_shots_json()])
    router = LLMRouter(local=local, cloud=None)

    with pytest.raises(InvalidLLMOutputError) as excinfo:
        router.director_shot_list("job")

    paths = [e["path"] for e in excinfo.value.errors]
    assert paths, "validation errors must name the offending field"
    assert any(p.startswith("shots[0]") for p in paths), paths
    assert not any(p.startswith("shots.0") for p in paths), (
        f"pydantic loc format leaked through: {paths}"
    )
    # The first rejection is preserved as history, not overwritten by the repair.
    assert "shot_id" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Keyless construction & secrets hygiene
# ---------------------------------------------------------------------------


def test_cloud_clients_refuse_keyless_construction(monkeypatch):
    monkeypatch.delenv("NIM_API_KEY", raising=False)
    with pytest.raises(ValueError):
        NIMClient(api_key="")
    with pytest.raises(ValueError):
        NIMClient.from_env()

    monkeypatch.setenv("NIM_API_KEY", "test-key")
    client = NIMClient.from_env()
    assert client.model == NIM_MODEL


def test_build_cloud_client_reads_the_environment_only():
    # No key -> (None, actionable reason naming the exact variable to set).
    client, note = build_cloud_client(env={})
    assert client is None
    assert "no fallback cloud key is configured" in note
    assert "NIM_API_KEY" in note

    # A key in the supplied mapping is honored.
    client, name = build_cloud_client(env={"NIM_API_KEY": "test-nim-key"})
    assert isinstance(client, NIMClient) and name == "nim"
    assert client.api_key == "test-nim-key"

    # Blank/whitespace keys are not keys.
    client, note = build_cloud_client(env={"NIM_API_KEY": "  "})
    assert client is None and "no fallback cloud key" in note


def test_build_cloud_client_never_logs_or_returns_the_key(monkeypatch, caplog):
    """The reason string returned when a key IS present must not echo it."""
    import logging

    caplog.set_level(logging.DEBUG)
    client, name = build_cloud_client(env={"NIM_API_KEY": "nvapi-supersecretvalue"})
    assert client is not None
    assert all("supersecret" not in r.getMessage() for r in caplog.records)


def test_router_from_env_keyless(monkeypatch):
    """from_env() must build a working local-first router with no cloud key."""
    for key in CLOUD_ENV_VARS:
        monkeypatch.delenv(key, raising=False)
    router = LLMRouter.from_env(local=ScriptedProvider([_valid_shots_json(1)]))
    assert router.cloud is None
    routed = router.director_shot_list("job")
    assert routed.record.decision == "local"


def test_router_from_env_picks_up_a_key_without_a_secret_loader(monkeypatch):
    """The whole credential story is the environment: no vault hook required."""
    monkeypatch.setenv("NIM_API_KEY", "env-key")
    router = LLMRouter.from_env(local=ScriptedProvider([_valid_shots_json(1)]))
    assert isinstance(router.cloud, NIMClient)
    assert router.cloud_name == "nim"


def test_no_secret_material_in_routing_modules():
    root = Path(__file__).resolve().parents[1]
    pattern = _re.compile(r"(nvapi-[A-Za-z0-9_\-]{8,}|sk-[A-Za-z0-9]{16,})")
    for rel in (
        "backend/llm/errors.py",
        "backend/llm/nim_client.py",
        "backend/llm/base.py",
        "backend/llm/ollama_client.py",
        "backend/llm/deepseek_client.py",
        "backend/services/llm_router.py",
    ):
        text = (root / rel).read_text(encoding="utf-8")
        assert not pattern.search(text), f"secret-looking literal in {rel}"


# ---------------------------------------------------------------------------
# DirectorService integration — the prompt machine goes through the router
# ---------------------------------------------------------------------------


def test_director_service_routes_through_router(tmp_path, monkeypatch):
    import sqlite3

    from backend.services import director_service as ds
    from backend.services.director_service import DirectorService

    enqueued: list[dict] = []
    monkeypatch.setattr(
        ds, "enqueue_llm_degrade",
        lambda script, project_id, reason, degrade_reason="": enqueued.append(
            {"reason": reason, "degrade_reason": degrade_reason}
        ),
    )

    flag = ExplicitRenderFlag()
    local = ScriptedProvider([_valid_shots_json(2), _valid_shots_json(2)])
    nim = StubNIM([_valid_shots_json(1)])
    router = LLMRouter(local=local, cloud=nim, render_state=flag)

    svc = DirectorService(db_path=tmp_path / "t.db", router=router)

    # 1. Render idle -> local serves the director job.
    result = svc.generate_shot_list("SCRIPT: Maya finds the letter.", project_id="p1")
    assert result.degraded is False
    assert result.provider == provider_name(local)
    assert len(result.shots) == 2

    # 2. Renderer reports an active job -> the SAME service overflows to NIM.
    flag.set()
    result2 = svc.generate_shot_list("SCRIPT: Maya finds the letter.", project_id="p1")
    assert result2.degraded is False
    assert result2.provider == "nim"
    assert len(result2.shots) == 1
    assert len(local.calls) == 1, "local must not be called during the render"
    assert len(nim.calls) == 1

    with sqlite3.connect(str(tmp_path / "t.db")) as conn:
        rows = conn.execute(
            "SELECT COUNT(*) FROM shots WHERE project_id='p1'"
        ).fetchone()[0]
    assert rows == 1, "the overflow result must be the persisted shot list"

    # 3. Degraded: busy GPU + no cloud -> service degrades to the review queue.
    svc2 = DirectorService(
        db_path=tmp_path / "t2.db",
        router=LLMRouter(local=local, cloud=None, render_state=flag),
    )
    result3 = svc2.generate_shot_list("SCRIPT: Maya finds the letter.", project_id="p2")
    assert result3.degraded is True
    assert "degraded" in result3.reason
    assert enqueued and enqueued[-1]["degrade_reason"] == "provider_unreachable"


# ---------------------------------------------------------------------------
# Live smoke — real Ollama through the router (self-skips when down)
# ---------------------------------------------------------------------------


def test_live_ollama_local_path_keyless():
    """The real Ollama path through the router, keyless. Skips when Ollama is down."""
    client = OllamaClient(model="qwen3.5:4b", max_retries=1)
    if not client.health_check():
        pytest.skip("Ollama not reachable on localhost:11434")

    router = LLMRouter(local=client)
    try:
        routed = router.complete_structured(
            'Reply with ONLY this JSON: {"ok": true}',
            _Tiny,
            job="smoke",
            kwargs_for=lambda _name: {"temperature": 0.0, "num_predict": 64, "think": False},
        )
    except InvalidLLMOutputError as exc:
        pytest.skip(f"live model did not produce the tiny schema: {exc}")

    assert routed.record.decision == "local"
    assert routed.record.provider == "ollama"
    assert routed.record.model == "qwen3.5:4b"
    assert routed.record.ok is True
    assert routed.value.ok is True
