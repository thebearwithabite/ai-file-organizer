"""LLMRouter — director-facing intelligence routing layer (PROMPT-MACHINE-DIRECTIVE v1.2).

Local-first by contract: ``OllamaClient`` (qwen3.5:4b) is PRIMARY; the cloud
client (``NIMClient`` when keyed) is FALLBACK and legitimate OVERFLOW. The order
is never inverted.

Decisions — one per request, structured log + metrics:

    local           — render state idle; the local provider served the job.
    overflow-cloud  — the renderer reports an ACTIVE render job: the VRAM is
                      reserved for the render, so director jobs route to the
                      cloud instead of blocking or OOM-ing the render.
    fallback-cloud  — the local provider failed in flight (process down,
                      context limit); the job retried once on the cloud.
    degraded        — no usable route: local busy/unreachable AND no cloud
                      key configured. Raises ``DegradedRoutingError`` that
                      explains both causes; fail fast, never a silent
                      pretend-fallback.

Render state comes from the renderer itself — a ``RenderStateProvider``, which
any renderer client satisfies structurally by exposing ``render_in_flight()``
(``WangPClient`` does; see ``docs/wangp-client.md``) — never from a VRAM guess.
A provider that is *not wired* means "unknown": the router says so in its reason
string and assumes idle so keyless local runs keep working. A provider that is
wired but *raises* is a different case, and fails safe to busy: an OOM beside a
live render is worse than one unnecessary cloud call.

Division of labour — this module routes, it does not validate:

* ``backend.llm.structured_output`` owns the structured-output contract (parse,
  validate against ShotSpec, exactly one repair retry, ``InvalidLLMOutputError``).
  The router composes ``enforce_structured`` and never re-implements a second,
  divergent copy of that contract.
* ``backend.llm.errors`` owns the two typed failures callers react to.

Transport exceptions are the router's alone: they are what switch to the cloud
once, and what degrade when no cloud key exists. A schema violation is NOT a
transport failure and never changes provider.

Telemetry: exactly one ``RouteRecord`` per request — decision, reason, selected
model, latency, and token counts summed across every real provider call
(including a repair), with missing/garbage usage coerced to zero rather than
crashing the request.

Secrets: cloud keys are read from the process environment only (``NIM_API_KEY``)
by :func:`build_cloud_client`, which never goes looking anywhere else. Keys are
never logged, never written to disk, never placed on a subprocess environment.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
)

from pydantic import BaseModel

from backend.llm.base import LLMProvider, TokenUsage
from backend.llm.errors import DegradedRoutingError, InvalidLLMOutputError
from backend.llm.nim_client import NIMClient
from backend.llm.ollama_client import OllamaClient
from backend.llm.structured_output import StructuredResult, enforce_structured

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

CLOUD_ENV_VARS = ("NIM_API_KEY",)
DEFAULT_CLOUD_NOTE = (
    "no fallback cloud key is configured (set NIM_API_KEY in the environment, "
    "or inject a cloud client)"
)
RENDER_BUSY_REASON = (
    "VRAM is occupied by an active render job — render in flight per renderer "
    "job state; local inference skipped to avoid blocking or OOM-ing the render"
)
RENDER_IDLE_REASON = "render state idle — local-first"
NOT_WIRED_NOTE = "render-state provider not wired; assumed idle"


class RouteDecision(str, Enum):
    local = "local"
    overflow_cloud = "overflow-cloud"
    fallback_cloud = "fallback-cloud"
    degraded = "degraded"


# ---------------------------------------------------------------------------
# Provider naming + cloud factory
# ---------------------------------------------------------------------------

_KNOWN_PROVIDER_NAMES: Tuple[Tuple[type, str], ...] = (
    (OllamaClient, "ollama"),
    (NIMClient, "nim"),
)


def provider_name(client: LLMProvider) -> str:
    """Stable provider label for logs/metrics (ollama | nim | class-derived)."""
    for cls, name in _KNOWN_PROVIDER_NAMES:
        if isinstance(client, cls):
            return name
    stem = type(client).__name__.lower()
    return stem[:-6] if stem.endswith("client") else stem


def build_cloud_client(
    env: Optional[Any] = None,
) -> Tuple[Optional[LLMProvider], str]:
    """Build the cloud fallback/overflow client from the environment.

    Returns ``(client, name)`` on success, ``(None, reason)`` otherwise. The key
    is read from ``env`` (default ``os.environ``) only — never from a repo file,
    never logged, never placed on a subprocess environment. Cloud credentials
    are the caller's to inject; this factory never goes looking for them.
    """
    env = os.environ if env is None else env
    # Strip before testing: a whitespace-only value is a misconfigured key, and
    # sending it as a bearer token produces a confusing 401 instead of the
    # actionable "no fallback cloud key" message.
    key = (env.get("NIM_API_KEY") or "").strip()
    if key:
        return NIMClient(api_key=key), "nim"
    return None, DEFAULT_CLOUD_NOTE


# ---------------------------------------------------------------------------
# Render state — the renderer's own job state, never a guess
# ---------------------------------------------------------------------------


class RenderStateProvider(Protocol):
    """Answers, from the RENDERER's own state: is a render in flight?

    Satisfied structurally by any object exposing ``render_in_flight()`` —
    ``WangPClient`` is the production implementation, so it can be handed to the
    router directly::

        router = LLMRouter(local=OllamaClient(model=...),
                           cloud=cloud, render_state=wangp_client)
    """

    def render_in_flight(self) -> bool:
        ...


class ExplicitRenderFlag:
    """Thread-safe flag the renderer client sets around its render calls.

    Renderer-side usage::

        flag = ExplicitRenderFlag()
        with flag.in_flight():
            client.render(payload, resolved)  # any director call inside this
                                              # window routes to the cloud
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = False

    def render_in_flight(self) -> bool:
        with self._lock:
            return self._active

    def set(self, active: bool = True) -> None:
        with self._lock:
            self._active = bool(active)

    def clear(self) -> None:
        self.set(False)

    @contextmanager
    def in_flight(self):
        self.set(True)
        try:
            yield self
        finally:
            self.set(False)


class CallableRenderState:
    """Adapter: render state from any zero-arg predicate (e.g. a client's job table)."""

    def __init__(self, predicate: Callable[[], Any]) -> None:
        self._predicate = predicate

    def render_in_flight(self) -> bool:
        return bool(self._predicate())


# ---------------------------------------------------------------------------
# Token accounting
# ---------------------------------------------------------------------------


def _as_count(value: Any) -> int:
    """Coerce provider-reported usage to a non-negative int.

    Providers legitimately report nothing (``None``), a float, or a numeric
    string. Telemetry must survive all of them: a missing count is zero, never a
    crash that takes the director pass down with it.
    """
    if isinstance(value, bool):
        return 0
    try:
        count = int(value)
    except (TypeError, ValueError):
        return 0
    return count if count > 0 else 0


@dataclass
class _UsageTally:
    """Sums token counts across every provider call made for one request.

    ``LLMProvider.last_usage`` only holds the MOST RECENT call, so a request
    that spent a repair retry would otherwise report half the tokens it actually
    spent. The routing record is per-request, so the tally is too.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0

    def absorb(self, client: Any) -> None:
        usage = getattr(client, "last_usage", None)
        if not isinstance(usage, TokenUsage):
            return
        self.prompt_tokens += _as_count(usage.prompt_tokens)
        self.completion_tokens += _as_count(usage.completion_tokens)
        self.calls += 1

    def as_usage(self) -> TokenUsage:
        return TokenUsage(
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
        )


# ---------------------------------------------------------------------------
# Records + metrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RouteRecord:
    """One routing decision, logged and metered per request."""

    job: str
    decision: str
    reason: str
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    attempts: int = 0
    attempt: str = ""  # primary | repair | "" (no provider call was made)
    ok: bool = True
    error: str = ""

    @property
    def total_tokens(self) -> int:
        return _as_count(self.prompt_tokens) + _as_count(self.completion_tokens)

    def as_log_line(self) -> str:
        return (
            f"decision={self.decision} job={self.job} provider={self.provider} "
            f"model={self.model} latency_ms={self.latency_ms:.1f} "
            f"prompt_tokens={self.prompt_tokens} completion_tokens={self.completion_tokens} "
            f"attempts={self.attempts} attempt={self.attempt} ok={self.ok} "
            f"reason={self.reason!r} error={self.error!r}"
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "job": self.job,
            "decision": self.decision,
            "reason": self.reason,
            "provider": self.provider,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "attempts": self.attempts,
            "attempt": self.attempt,
            "ok": self.ok,
            "error": self.error,
        }


class RouteMetrics:
    """Accumulates route records for dashboards and tests (thread-safe)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: List[RouteRecord] = []

    def record(self, record: RouteRecord) -> None:
        with self._lock:
            self._records.append(record)

    @property
    def requests(self) -> int:
        with self._lock:
            return len(self._records)

    @property
    def counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        with self._lock:
            for r in self._records:
                counts[r.decision] = counts.get(r.decision, 0) + 1
        return counts

    @property
    def last(self) -> Optional[RouteRecord]:
        with self._lock:
            return self._records[-1] if self._records else None

    def token_totals(self) -> Dict[str, int]:
        prompt = completion = 0
        with self._lock:
            for r in self._records:
                prompt += _as_count(r.prompt_tokens)
                completion += _as_count(r.completion_tokens)
        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
        }

    def snapshot(self) -> Dict[str, Any]:
        last = self.last
        return {
            "requests": self.requests,
            "counts": dict(self.counts),
            "tokens": self.token_totals(),
            "last": last.as_dict() if last else None,
        }


@dataclass(frozen=True)
class RoutedResult(Generic[T]):
    """A validated structured value plus the route record that produced it."""

    value: T
    record: RouteRecord


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class LLMRouter:
    """Route director jobs: local first, cloud overflow/fallback, explicit degrade."""

    def __init__(
        self,
        local: LLMProvider,
        cloud: Optional[LLMProvider] = None,
        *,
        local_name: Optional[str] = None,
        cloud_name: Optional[str] = None,
        render_state: Optional[RenderStateProvider] = None,
        cloud_note: str = "",
        metrics: Optional[RouteMetrics] = None,
        clock: Callable[[], float] = time.perf_counter,
        max_repairs: int = 1,
    ) -> None:
        self.local = local
        self.cloud = cloud
        self.local_name = local_name or provider_name(local)
        self.cloud_name = (cloud_name or provider_name(cloud)) if cloud is not None else ""
        self.render_state = render_state
        self.cloud_note = cloud_note or DEFAULT_CLOUD_NOTE
        self.metrics = metrics if metrics is not None else RouteMetrics()
        self.max_repairs = max(0, int(max_repairs))
        self._clock = clock

    # -- factories -----------------------------------------------------------

    @classmethod
    def from_env(
        cls,
        *,
        local: Optional[LLMProvider] = None,
        local_model: Optional[str] = None,
        render_state: Optional[RenderStateProvider] = None,
        env: Optional[Any] = None,
        metrics: Optional[RouteMetrics] = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> "LLMRouter":
        """Keyless-safe factory: Ollama primary, cloud client only if a key exists."""
        if local is None:
            from backend.services.llm_resolver import DIRECTOR_LOCAL_FALLBACK_MODEL

            local = OllamaClient(model=local_model or DIRECTOR_LOCAL_FALLBACK_MODEL)
        cloud, note = build_cloud_client(env)
        return cls(
            local=local,
            cloud=cloud,
            render_state=render_state,
            cloud_note=note if cloud is None else "",
            metrics=metrics,
            clock=clock,
        )

    # -- public API ----------------------------------------------------------

    def director_shot_list(
        self,
        prompt: str,
        *,
        job: str = "director.shot_list",
        **kwargs: Any,
    ) -> RoutedResult:
        """Director pass: script -> ShotSpec list, validated against the live schema."""
        from backend.services.shot_spec import ShotListOutput

        return self.complete_structured(prompt, ShotListOutput, job=job, **kwargs)

    def complete_structured(
        self,
        prompt: str,
        schema: Type[T],
        *,
        job: str = "director",
        kwargs_for: Optional[Callable[[str], Dict[str, Any]]] = None,
    ) -> RoutedResult:
        """Route one structured-output job; return the validated model + route record.

        Raises ``DegradedRoutingError`` when no route exists (fail fast, both
        causes in the message) and ``InvalidLLMOutputError`` when the output
        fails the schema even after the single repair retry.
        """
        kwargs_for = kwargs_for or (lambda _name: {})
        started = self._clock()
        tally = _UsageTally()

        render_busy, render_note = self._render_state_now()
        if render_busy:
            # Say WHICH busy: a live render is expected, an unanswerable probe
            # is a fault someone has to fix. Same route, different urgency.
            busy_reason = f"{RENDER_BUSY_REASON} ({render_note})" if render_note else RENDER_BUSY_REASON
        else:
            busy_reason = ""

        if render_busy and self.cloud is None:
            # Fail fast: no blocking local call (the VRAM is the render's), and
            # no call to a cloud path that does not exist.
            raise self._degrade(
                job,
                started,
                local_reason=busy_reason,
                cloud_reason=self.cloud_note,
                tally=tally,
            )

        if render_busy:
            decision = RouteDecision.overflow_cloud
            client, cname = self.cloud, self.cloud_name
            reason = busy_reason
            # Local was never called and must never be blamed: on this route the
            # honest local reason is the occupancy that skipped it.
            local_reason = busy_reason
            cloud_role = "cloud overflow"
            switched = False
        else:
            decision = RouteDecision.local
            client, cname = self.local, self.local_name
            reason = RENDER_IDLE_REASON + (f" ({render_note})" if render_note else "")
            local_reason = ""
            cloud_role = "cloud fallback"
            switched = False

        while True:
            try:
                structured = self._enforce(client, cname, prompt, schema, job, kwargs_for, tally)
            except InvalidLLMOutputError:
                # A contract violation is not a transport failure: it never
                # changes provider. Record it against the route that served it.
                self._emit(
                    self._record(
                        job, decision, reason, cname, client, started,
                        ok=False, tally=tally, error="structured output rejected",
                    )
                )
                raise

            except Exception as exc:
                failure = getattr(client, "last_failure", "") or "provider_unreachable"
                detail = f"{failure}: {exc}"

                if not switched and client is self.local and self.cloud is not None:
                    # One transport-level switch to the cloud fallback. The
                    # fallback provider gets its own single-repair contract and
                    # its own token tally from here on.
                    local_reason = f"local provider failed ({detail})"
                    switched = True
                    decision = RouteDecision.fallback_cloud
                    client, cname = self.cloud, self.cloud_name
                    reason = f"{local_reason} — retried on {cloud_role}"
                    cloud_role = "cloud fallback"
                    continue

                if client is self.local:
                    local_reason = detail
                    cloud_reason = self.cloud_note
                else:
                    cloud_reason = f"{cloud_role} also failed ({detail})"
                raise self._degrade(
                    job, started,
                    local_reason=local_reason or detail,
                    cloud_reason=cloud_reason,
                    tally=tally,
                )

            record = self._record(
                job, decision, reason, cname, client, started,
                ok=True, tally=tally, structured=structured,
            )
            self._emit(record)
            return RoutedResult(value=structured.value, record=record)

    # -- internals -----------------------------------------------------------

    def _render_state_now(self) -> Tuple[bool, str]:
        """``(busy, note)`` for this request.

        Not wired  -> assumed idle, and the reason string says so, so keyless
                      local runs keep working without pretending to know the GPU.
        Wired      -> the renderer's own answer; no VRAM sampling, ever.
        Raises     -> fails SAFE to busy: a probe that cannot answer is not
                      evidence of an idle GPU, and an OOM beside a live render
                      costs far more than one unnecessary cloud call.
        """
        if self.render_state is None:
            return False, NOT_WIRED_NOTE
        try:
            busy = bool(self.render_state.render_in_flight())
        except Exception as exc:
            logger.warning("render-state probe failed; assuming BUSY: %s", exc)
            return True, f"render-state probe failed ({exc}); assumed busy"
        return busy, ""

    def _enforce(
        self,
        client: LLMProvider,
        cname: str,
        prompt: str,
        schema: Type[T],
        job: str,
        kwargs_for: Callable[[str], Dict[str, Any]],
        tally: _UsageTally,
    ) -> StructuredResult[T]:
        """Run the structured-output contract against one selected provider.

        Delegates to ``backend.llm.structured_output`` so there is exactly one
        implementation of parse/validate/repair and one set of actionable error
        paths. Transport exceptions propagate untouched — switching to the cloud
        and degrading are the router's decisions alone.

        The generate closure is where the token tally is fed: every real provider
        call, primary or repair, is counted.
        """
        call_kwargs = kwargs_for(cname)

        def generate(attempt_prompt: str) -> str:
            raw = client.generate(attempt_prompt, **call_kwargs)
            tally.absorb(client)
            return raw

        return enforce_structured(
            generate,
            prompt,
            schema,
            provider=cname,
            model=str(getattr(client, "model", "") or ""),
            job=job,
            max_repairs=self.max_repairs,
        )

    def _record(
        self,
        job: str,
        decision: RouteDecision,
        reason: str,
        cname: str,
        client: LLMProvider,
        started: float,
        *,
        ok: bool,
        tally: _UsageTally,
        structured: Optional[StructuredResult] = None,
        error: str = "",
    ) -> RouteRecord:
        elapsed_ms = max(0.0, self._clock() - started) * 1000.0
        attempts = tally.calls if structured is None else structured.attempt_count
        return RouteRecord(
            job=job,
            decision=decision.value,
            reason=reason,
            provider=cname,
            model=str(getattr(client, "model", "") or ""),
            latency_ms=round(elapsed_ms, 3),
            prompt_tokens=tally.prompt_tokens,
            completion_tokens=tally.completion_tokens,
            attempts=attempts,
            attempt="repair" if structured is not None and structured.repaired else "primary",
            ok=ok,
            error=error,
        )

    def _emit(self, record: RouteRecord) -> None:
        self.metrics.record(record)
        log = logger.info if record.ok else logger.warning
        log("llm.route %s", record.as_log_line())

    def _degrade(
        self,
        job: str,
        started: float,
        *,
        local_reason: str,
        cloud_reason: str,
        tally: Optional[_UsageTally] = None,
    ) -> DegradedRoutingError:
        tally = tally if tally is not None else _UsageTally()
        message = (
            f"LLM routing degraded for job {job!r}: local inference unavailable "
            f"({local_reason}); cloud fallback unavailable ({cloud_reason}). "
            "The request failed fast without calling any provider — finish or "
            "free the render, then retry; or set NIM_API_KEY in the environment."
        )
        record = RouteRecord(
            job=job,
            decision=RouteDecision.degraded.value,
            reason=f"local unavailable ({local_reason}); cloud unavailable ({cloud_reason})",
            provider="",
            model="",
            latency_ms=round(max(0.0, self._clock() - started) * 1000.0, 3),
            prompt_tokens=tally.prompt_tokens,
            completion_tokens=tally.completion_tokens,
            attempts=tally.calls,
            attempt="",
            ok=False,
            error=message,
        )
        self._emit(record)
        return DegradedRoutingError(
            message, job=job, local_reason=local_reason, cloud_reason=cloud_reason
        )