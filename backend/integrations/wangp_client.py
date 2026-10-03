"""Headless WanGP renderer client — MCP over streamable-http.

Talks to a WanGP instance started with::

    wgp.py --mcp --mcp-transport streamable-http --mcp-host <host> --mcp-port <port>

Both the v1 tool surface (``--mcp-api-version 1``: ``wangp_generate`` /
``wangp_get_job`` / ``wangp_cancel_job``) and the v2 default surface
(``wangp_generate(settings=...)`` / ``wangp_session`` job actions) are
supported; the surface is DISCOVERED at connect time from ``tools/list`` and
never assumed. The client was built against recorded traffic from the live
renderer (see ``tests/fixtures/wangp_mcp/``).

Guarantees:
- The template + six-override discipline is enforced HERE, at the transport
  boundary (:func:`enforce_bounded_settings`) before anything is submitted.
- Submit is never retried (a retried submit can double-render). Only
  idempotent calls (initialize, tools/list, job/status reads) use
  retry-with-backoff.
- Artifact paths are translated ``D:\\...`` -> ``/mnt/d/...`` at this boundary.
- This module never writes to or deletes the renderer install. It performs no
  filesystem writes at all.
"""
from __future__ import annotations

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from backend.integrations.paths import win_to_wsl_path
from backend.integrations.wangp_config import WangPMCPConfig, connection_help
from backend.integrations.wangp_settings import ResolvedSettings, enforce_bounded_settings

__all__ = [
    "ACTIVE_JOB_STATUSES",
    "MCP_PROTOCOL_VERSION",
    "TERMINAL_JOB_STATUSES",
    "JobStatus",
    "RenderJob",
    "RenderResult",
    "RenderStateSnapshot",
    "ServerCapabilities",
    "WangPClient",
    "WangPConnectionError",
    "WangPError",
    "WangPJobFailedError",
    "WangPProtocolError",
    "WangPRendererError",
    "WangPTimeoutError",
    "detect_capabilities",
    "is_in_flight_status",
    "parse_job_status",
]

MCP_PROTOCOL_VERSION = "2025-03-26"  # observed live (fixtures/wangp_mcp/01_initialize.json)


# --------------------------------------------------------------------------- render-state vocabulary


#: Statuses meaning an accepted render is not finished yet. ``JobStatus.status``
#: only ever emits ``running`` today (the renderer reports queued work as
#: ``done=false``), but a future snapshot that distinguishes the two still
#: classifies as in-flight.
ACTIVE_JOB_STATUSES = frozenset(
    {"queued", "pending", "accepted", "submitted", "starting", "running"}
)

#: Statuses that mean the render is over. Anything else counts as in-flight.
TERMINAL_JOB_STATUSES = frozenset(
    {"completed", "cancelled", "canceled", "failed", "error", "timeout"}
)


def is_in_flight_status(status: object) -> bool:
    """True when ``status`` means a render is queued or running.

    Fails safe: a missing or unrecognized status counts as in-flight, so the
    VRAM-overflow router sends the director job to the cloud instead of risking
    an OOM beside a render whose real state we cannot name. Only the terminal
    names clear the signal.
    """
    if status is None:
        return True
    return str(status).strip().lower() not in TERMINAL_JOB_STATUSES


# --------------------------------------------------------------------------- errors


class WangPError(RuntimeError):
    """Base class for renderer-client failures."""


class WangPConnectionError(WangPError):
    """The renderer could not be reached (refused/reset/DNS)."""


class WangPTimeoutError(WangPError):
    """No response within the client timeout, or a job exceeded its wait budget."""

    def __init__(self, message: str, job_id: str | None = None) -> None:
        super().__init__(message)
        self.job_id = job_id


class WangPProtocolError(WangPError):
    """The renderer (or a proxy) returned something that is not valid MCP."""


class WangPRendererError(WangPError):
    """The renderer answered with ``isError`` (validation, unknown model/job, ...)."""


class WangPJobFailedError(WangPError):
    """A job finished with ``success=false``."""

    def __init__(self, message: str, job_id: str | None = None, errors: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.job_id = job_id
        self.errors = errors


# --------------------------------------------------------------------------- transport


class _Transport:
    """Minimal JSON-RPC 2.0 / streamable-http transport (stdlib only)."""

    def __init__(self, config: WangPMCPConfig) -> None:
        self.config = config
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def post(
        self,
        method: str,
        params: Mapping[str, Any] | None,
        *,
        timeout: float,
        retry: bool = True,
    ) -> Any:
        attempts = max(1, int(self.config.retry_attempts)) if retry else 1
        delay = float(self.config.retry_backoff_s)
        last_error: WangPError | None = None
        for attempt in range(1, attempts + 1):
            try:
                return self._post_once(method, params, timeout)
            except (WangPConnectionError, WangPProtocolError) as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                time.sleep(min(delay, float(self.config.retry_backoff_max_s)))
                delay *= 2
        assert last_error is not None
        raise last_error

    def notify(self, method: str, params: Mapping[str, Any] | None = None) -> None:
        try:
            self._post_once(method, params, self.config.request_timeout_s, notification=True)
        except WangPError:
            pass  # best effort; servers may not require the initialized notification

    def _post_once(
        self,
        method: str,
        params: Mapping[str, Any] | None,
        timeout: float,
        notification: bool = False,
    ) -> Any:
        request: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            request["params"] = dict(params)
        if not notification:
            request["id"] = self._next_id()
        body = json.dumps(request).encode("utf-8")
        http_request = urllib.request.Request(
            self.config.base_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        try:
            with urllib.request.urlopen(http_request, timeout=timeout) as response:
                raw = response.read()
                content_type = response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            snippet = ""
            try:
                snippet = exc.read().decode("utf-8", "replace")[:300]
            except Exception:  # pragma: no cover - best effort snippet
                pass
            if exc.code in (404, 405):
                raise WangPProtocolError(
                    f"renderer returned HTTP {exc.code} for {method} at {self.config.base_url}; "
                    "check the endpoint path (/mcp/) and that the server was started with "
                    "--mcp --mcp-transport streamable-http"
                ) from exc
            raise WangPProtocolError(
                f"renderer returned HTTP {exc.code} for {method}: {snippet!r}"
            ) from exc
        except TimeoutError as exc:
            raise WangPTimeoutError(
                f"no response from {self.config.base_url} within {timeout:.0f}s for {method}"
            ) from exc
        except (urllib.error.URLError, ConnectionError) as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError):
                raise WangPTimeoutError(
                    f"timed out talking to {self.config.base_url}: {reason}"
                ) from exc
            raise WangPConnectionError(connection_help(self.config, reason=str(reason))) from exc

        payload = _decode_body(raw, content_type)
        if payload is None:
            return None  # notification ack (202, empty body)
        if not isinstance(payload, Mapping):
            raise WangPProtocolError(
                f"malformed JSON-RPC response for {method}: expected object, "
                f"got {type(payload).__name__}"
            )
        error = payload.get("error")
        if isinstance(error, Mapping):
            raise WangPProtocolError(
                f"JSON-RPC error {error.get('code')}: {error.get('message')}"
            )
        return payload.get("result")


def _decode_body(raw: bytes, content_type: str) -> Any:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    if "text/event-stream" in (content_type or "").lower():
        chunks = [
            line[5:].strip()
            for line in text.splitlines()
            if line.startswith("data:")
        ]
        text = next((chunk for chunk in reversed(chunks) if chunk and chunk != "[DONE]"), "")
        if not text:
            raise WangPProtocolError("SSE response contained no data payload")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise WangPProtocolError(
            f"malformed JSON-RPC body: {exc}; response starts with {text[:200]!r}"
        ) from exc


def _unwrap_tool_result(result: Any, tool_name: str = "<tool>") -> Any:
    """Extract a tool payload from an MCP ``tools/call`` result envelope."""
    if not isinstance(result, Mapping):
        raise WangPProtocolError(
            f"malformed tool result from {tool_name}: expected object, "
            f"got {type(result).__name__}"
        )
    if result.get("isError"):
        raise WangPRendererError(f"{tool_name}: {_first_text(result) or 'unspecified renderer error'}")
    structured = result.get("structuredContent")
    if structured is not None:
        return structured
    content = result.get("content")
    if isinstance(content, list):
        parts: list[Any] = []
        for item in content:
            if isinstance(item, Mapping) and item.get("type") == "text":
                text = item.get("text", "")
                try:
                    parts.append(json.loads(text))
                except (json.JSONDecodeError, TypeError):
                    parts.append(text)
        if len(parts) == 1:
            return parts[0]
        if parts:
            return parts
    raise WangPProtocolError(
        f"tool result from {tool_name} had neither structuredContent nor text content"
    )


def _first_text(result: Mapping[str, Any]) -> str:
    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, Mapping) and item.get("type") == "text":
                return str(item.get("text", ""))
    return ""


def _as_list(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, Mapping):
        inner = payload.get("result")
        if isinstance(inner, list):
            return inner
        return [payload]
    raise WangPProtocolError(f"expected a list payload, got {type(payload).__name__}")


# --------------------------------------------------------------------------- capabilities


@dataclass(frozen=True)
class ServerCapabilities:
    """What the connected renderer exposes, discovered from ``tools/list``."""

    protocol_version: str
    server_name: str
    server_version: str
    tool_names: tuple[str, ...]
    generate_tool: str | None
    settings_arg: str | None  # "source" (v1) | "settings" (v2) | None
    wait_style: str  # "optional" | "forced" | "absent" | "unknown"
    job_get: tuple[str, str] | None  # ("tool", name) | ("session", tool_name)
    job_cancel: tuple[str, str] | None
    default_settings_style: str | None  # "tool" | "model_action"
    models_style: str | None  # "list" | "search"
    template_style: str | None  # "tool" | "v2"
    tools: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)

    @property
    def api_flavor(self) -> str:
        if self.settings_arg == "source":
            return "v1"
        if self.settings_arg == "settings":
            return "v2"
        return "unknown"

    def as_manifest(self) -> dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "server": f"{self.server_name} {self.server_version}",
            "api_flavor": self.api_flavor,
            "generate_tool": self.generate_tool,
            "settings_arg": self.settings_arg,
            "wait_style": self.wait_style,
            "job_get": list(self.job_get) if self.job_get else None,
            "tool_count": len(self.tool_names),
        }


def detect_capabilities(
    tools: list[Mapping[str, Any]],
    *,
    protocol_version: str = MCP_PROTOCOL_VERSION,
    server_info: Mapping[str, Any] | None = None,
) -> ServerCapabilities:
    """Derive the renderer's callable surface from a ``tools/list`` result."""
    by_name: dict[str, Mapping[str, Any]] = {}
    for tool in tools:
        if isinstance(tool, Mapping) and tool.get("name"):
            by_name[str(tool["name"])] = tool
    names = set(by_name)

    generate_tool = "wangp_generate" if "wangp_generate" in names else None
    settings_arg: str | None = None
    wait_style = "unknown"
    if generate_tool:
        schema = by_name[generate_tool].get("inputSchema") or {}
        props = schema.get("properties") if isinstance(schema, Mapping) else None
        props = props if isinstance(props, Mapping) else {}
        if "settings" in props:
            settings_arg = "settings"
        elif "source" in props:
            settings_arg = "source"
        wait = props.get("wait")
        if not isinstance(wait, Mapping):
            wait_style = "absent"
        elif wait.get("const") is True:
            wait_style = "forced"
        else:
            wait_style = "optional"

    if "wangp_get_job" in names:
        job_get: tuple[str, str] | None = ("tool", "wangp_get_job")
    elif "wangp_session" in names:
        # v2: jobs move under the wangp_session tool; the action ("get_job")
        # is chosen at the call site.
        job_get = ("session", "wangp_session")
    else:
        job_get = None

    if "wangp_cancel_job" in names:
        job_cancel: tuple[str, str] | None = ("tool", "wangp_cancel_job")
    elif "wangp_session" in names:
        job_cancel = ("session", "wangp_session")
    else:
        job_cancel = None

    default_settings_style = None
    if "wangp_get_default_settings" in names:
        default_settings_style = "tool"
    elif "wangp_model" in names:
        default_settings_style = "model_action"

    models_style = None
    if "wangp_list_models" in names:
        models_style = "list"
    elif "wangp_models" in names:
        models_style = "search"

    template_style = None
    if "wangp_get_deepy_template_settings" in names:
        template_style = "tool"
    elif "wangp_deepy_templates" in names:
        template_style = "v2"

    server_info = server_info or {}
    return ServerCapabilities(
        protocol_version=protocol_version,
        server_name=str(server_info.get("name", "WanGP")),
        server_version=str(server_info.get("version", "")),
        tool_names=tuple(sorted(names)),
        generate_tool=generate_tool,
        settings_arg=settings_arg,
        wait_style=wait_style,
        job_get=job_get,
        job_cancel=job_cancel,
        default_settings_style=default_settings_style,
        models_style=models_style,
        template_style=template_style,
        tools=by_name,
    )


# --------------------------------------------------------------------------- job state


@dataclass(frozen=True)
class JobStatus:
    """Parsed view of a WanGP job snapshot (works for v1 and v2 shapes)."""

    job_id: str
    done: bool
    cancel_requested: bool
    success: bool | None
    cancelled: bool
    errors: tuple[str, ...]
    artifacts: tuple[str, ...]  # WSL-translated
    artifacts_native: tuple[str, ...]  # as emitted by the renderer (Windows)
    progress: Mapping[str, Any] | None
    raw: Mapping[str, Any] = field(repr=False, default_factory=dict)

    @property
    def status(self) -> str:
        if not self.done:
            return "running"
        if self.cancelled:
            return "cancelled"
        if self.success is False:
            return "failed"
        if self.success is None and self.errors:
            return "failed"
        return "completed"
        return "completed"

    @property
    def in_flight(self) -> bool:
        """True while this job is queued or running.

        Derived from the renderer's own job state (the same
        :class:`JobStatus` the poll loop uses) — never from GPU utilization,
        VRAM readings, or process state.
        """
        return is_in_flight_status(self.status)

    def as_manifest(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "artifacts": list(self.artifacts_native),
            "errors": list(self.errors),
        }


def parse_job_status(snapshot: Any) -> JobStatus:
    """Parse a job snapshot as emitted by the live renderer (recorded shape)."""
    if not isinstance(snapshot, Mapping):
        raise WangPProtocolError(
            f"malformed job snapshot: expected object, got {type(snapshot).__name__}"
        )
    job_id = snapshot.get("job_id")
    if not job_id:
        raise WangPProtocolError("malformed job snapshot: missing job_id")
    done = bool(snapshot.get("done"))
    result = snapshot.get("result")
    result = dict(result) if isinstance(result, Mapping) else {}
    events = snapshot.get("events")
    events = events if isinstance(events, list) else []

    if not result:
        for event in reversed(events):
            if (
                isinstance(event, Mapping)
                and event.get("kind") == "completed"
                and isinstance(event.get("data"), Mapping)
            ):
                result = dict(event["data"])
                break

    progress = None
    for event in reversed(events):
        if (
            isinstance(event, Mapping)
            and event.get("kind") == "progress"
            and isinstance(event.get("data"), Mapping)
        ):
            progress = dict(event["data"])
            break

    native: list[str] = [str(path) for path in (result.get("generated_files") or []) if path]
    artifacts = result.get("artifacts")
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if isinstance(artifact, Mapping) and artifact.get("path"):
                native.append(str(artifact["path"]))
    native = list(dict.fromkeys(native))
    translated = [win_to_wsl_path(path) for path in native]

    errors = tuple(
        str(error.get("message") if isinstance(error, Mapping) else error)
        for error in (result.get("errors") or [])
    )
    success = result.get("success") if "success" in result else None
    return JobStatus(
        job_id=str(job_id),
        done=done,
        cancel_requested=bool(snapshot.get("cancel_requested", False)),
        success=success if isinstance(success, bool) else None,
        cancelled=bool(result.get("cancelled", False)),
        errors=errors,
        artifacts=tuple(translated),
        artifacts_native=tuple(native),
        progress=progress,
        raw=dict(snapshot),
    )


@dataclass(frozen=True)
class RenderJob:
    """A submitted render job (submit returned; completion may still be pending)."""

    job_id: str
    status: str
    snapshot: Mapping[str, Any] = field(repr=False, default_factory=dict)

    @property
    def in_flight(self) -> bool:
        """True while this job is queued or running (submit returned, not done)."""
        return is_in_flight_status(self.status)


@dataclass(frozen=True)
class RenderResult:
    """A finished render and its artifact paths (WSL form + native form)."""

    job_id: str
    status: str  # "completed" | "cancelled"
    artifacts: tuple[str, ...]
    artifacts_native: tuple[str, ...]
    errors: tuple[str, ...] = ()
    progress: Mapping[str, Any] | None = None

    @property
    def paths(self) -> tuple[str, ...]:
        return self.artifacts

    @property
    def ok(self) -> bool:
        return self.status == "completed"

    def as_manifest(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "artifacts": list(self.artifacts_native),
            "artifacts_wsl": list(self.artifacts),
            "errors": list(self.errors),
        }


# --------------------------------------------------------------------------- render in-flight state


@dataclass(frozen=True)
class RenderStateSnapshot:
    """A self-describing read of "is a render in flight?".

    ``in_flight`` is the signal the LLM router queries (the router's
    ``RenderStateProvider`` protocol asks for exactly ``render_in_flight()``).
    It is computed from the renderer's own job state — never from GPU
    utilization, VRAM free/total, or process liveness.
    """

    in_flight: bool
    jobs: Mapping[str, str] = field(default_factory=dict)
    probed: bool = False
    stale: bool = False
    probe_error: str | None = None

    @property
    def job_ids(self) -> tuple[str, ...]:
        return tuple(self.jobs)

    def as_manifest(self) -> dict[str, Any]:
        return {
            "in_flight": self.in_flight,
            "jobs": dict(self.jobs),
            "probed": self.probed,
            "stale": self.stale,
            "probe_error": self.probe_error,
        }


# --------------------------------------------------------------------------- client


class WangPClient:
    """Headless client for the native-Windows WanGP renderer (MCP/streamable-http)."""

    def __init__(self, config: WangPMCPConfig | None = None, *, transport: Any | None = None) -> None:
        self.config = config or WangPMCPConfig.from_env()
        self._transport = transport or _Transport(self.config)
        self._capabilities: ServerCapabilities | None = None
        self._active_jobs: dict[str, str] = {}
        self._active_lock = threading.Lock()

    # -- connection ---------------------------------------------------------

    def connect(self, force: bool = False) -> ServerCapabilities:
        """Initialize the MCP session and discover the live tool surface."""
        if self._capabilities is not None and not force:
            return self._capabilities
        init = self._transport.post(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": self.config.client_name, "version": self.config.client_version},
            },
            timeout=self.config.connect_timeout_s,
            retry=True,
        )
        if not isinstance(init, Mapping):
            raise WangPProtocolError("initialize returned no result object")
        self._transport.notify("notifications/initialized")
        listed = self._transport.post("tools/list", {}, timeout=self.config.connect_timeout_s, retry=True)
        tools = listed.get("tools") if isinstance(listed, Mapping) else None
        if not isinstance(tools, list):
            raise WangPProtocolError(
                f"tools/list returned no tools list: {str(listed)[:200]!r}"
            )
        self._capabilities = detect_capabilities(
            tools,
            protocol_version=str(init.get("protocolVersion", MCP_PROTOCOL_VERSION)),
            server_info=init.get("serverInfo") if isinstance(init.get("serverInfo"), Mapping) else None,
        )
        return self._capabilities

    @property
    def capabilities(self) -> ServerCapabilities:
        return self.connect()

    def close(self) -> None:  # stdlib transport holds no persistent connection
        pass

    def __enter__(self) -> "WangPClient":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    # -- discovery helpers ---------------------------------------------------

    def list_models(self, query: str = "", limit: int = 10, **filters: Any) -> list[dict[str, Any]]:
        capabilities = self.connect()
        if capabilities.models_style == "list":
            tool = capabilities.tools.get("wangp_list_models", {})
            schema = tool.get("inputSchema") if isinstance(tool, Mapping) else None
            declared: set[str] = set()
            if isinstance(schema, Mapping) and isinstance(schema.get("properties"), Mapping):
                declared = set(schema["properties"])
            arguments = {key: value for key, value in filters.items() if value is not None}
            arguments["limit"] = limit
            if query:
                arguments["query"] = query
            if declared:  # never send arguments the live schema does not declare
                arguments = {key: value for key, value in arguments.items() if key in declared}
            payload = self._call_tool("wangp_list_models", arguments, idempotent=True)
        elif capabilities.models_style == "search":
            payload = self._call_tool(
                "wangp_models",
                {"action": "search", "arguments": {"query": query, "limit": limit, "filters": dict(filters)}},
                idempotent=True,
            )
        else:
            raise WangPProtocolError("renderer exposes no model listing tool")
        return [dict(item) for item in _as_list(payload) if isinstance(item, Mapping)]

    def get_default_settings(self, model_type: str) -> dict[str, Any]:
        """Pristine renderer defaults for a model — the canonical template source."""
        capabilities = self.connect()
        if capabilities.default_settings_style == "tool":
            payload = self._call_tool(
                "wangp_get_default_settings", {"model_type": model_type}, idempotent=True
            )
        elif capabilities.default_settings_style == "model_action":
            payload = self._call_tool(
                "wangp_model",
                {"model_type": model_type, "action": "defaults", "arguments": {}},
                idempotent=True,
            )
        else:
            raise WangPProtocolError("renderer exposes no default-settings tool")
        if not isinstance(payload, Mapping):
            raise WangPProtocolError(
                f"default settings for {model_type!r} were not an object: {type(payload).__name__}"
            )
        return dict(payload)

    # -- rendering -----------------------------------------------------------

    def submit_render(self, payload: Mapping[str, Any], resolved: ResolvedSettings) -> RenderJob:
        """Submit a render built from a template + the six overrides.

        The template discipline is enforced HERE (before any network I/O).
        Submit is deliberately never retried — a retried submit can
        double-render.
        """
        enforce_bounded_settings(payload, resolved.template, resolved.overrides)
        capabilities = self.connect()
        if capabilities.generate_tool is None:
            raise WangPProtocolError("renderer exposes no wangp_generate tool")
        arguments = self._build_generate_arguments(capabilities, payload)
        timeout = self.config.submit_timeout_s
        if capabilities.wait_style == "absent":  # server blocks internally
            timeout = max(timeout, self.config.poll_timeout_s + 60.0)
        result = self._call_tool(capabilities.generate_tool, arguments, timeout=timeout, idempotent=False)
        snapshot = result if isinstance(result, Mapping) else None
        if snapshot is None or not snapshot.get("job_id"):
            raise WangPProtocolError(
                f"malformed generate response (missing job_id): {str(result)[:200]!r}"
            )
        status = parse_job_status(snapshot)
        self._track(status)
        return RenderJob(job_id=status.job_id, status=status.status, snapshot=dict(snapshot))

    def _build_generate_arguments(
        self, capabilities: ServerCapabilities, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        arguments: dict[str, Any] = {capabilities.settings_arg or "source": dict(payload)}
        properties = {}
        tool = capabilities.tools.get(capabilities.generate_tool or "", {})
        schema = tool.get("inputSchema") if isinstance(tool, Mapping) else None
        if isinstance(schema, Mapping) and isinstance(schema.get("properties"), Mapping):
            properties = schema["properties"]
        if capabilities.wait_style == "optional":
            arguments["wait"] = False  # true async: submit returns a job
        elif capabilities.wait_style == "forced":
            # Async is disabled on this server (v2 without --mcp-async).
            # Park with timeout_s: per docs this returns the job WITHOUT
            # cancelling it, so the client can poll.
            arguments["wait"] = True
            arguments["timeout_s"] = self.config.park_timeout_s
        if "event_limit" in properties:
            arguments["event_limit"] = 0
        return arguments

    def get_job(self, job_id: str) -> JobStatus:
        """Poll a job. Works against both v1 (tool) and v2 (session action) servers."""
        capabilities = self.connect()
        if capabilities.job_get is None:
            raise WangPProtocolError("renderer exposes no job-status tool")
        kind, name = capabilities.job_get
        if kind == "tool":
            payload = self._call_tool(
                name, {"job_id": job_id, "event_limit": 20}, idempotent=True
            )
        else:
            payload = self._call_tool(
                name, {"action": "get_job", "arguments": {"job_id": job_id}}, idempotent=True
            )
        status = parse_job_status(payload)
        self._track(status)
        return status

    def wait_for_job(
        self,
        job: RenderJob | str,
        *,
        timeout: float | None = None,
        poll_interval: float | None = None,
        on_poll: Callable[[JobStatus], None] | None = None,
    ) -> RenderResult:
        """Poll until the job finishes. Raises WangPTimeoutError / WangPJobFailedError."""
        job_id = job.job_id if isinstance(job, RenderJob) else str(job)
        timeout = self.config.poll_timeout_s if timeout is None else float(timeout)
        interval = self.config.poll_interval_s if poll_interval is None else float(poll_interval)
        deadline = time.monotonic() + timeout
        snapshot: Mapping[str, Any] | None = job.snapshot if isinstance(job, RenderJob) else None
        while True:
            status = parse_job_status(snapshot) if snapshot is not None else self.get_job(job_id)
            snapshot = None
            if status.done:
                if status.status == "failed":
                    detail = "; ".join(status.errors) or "renderer reported failure"
                    raise WangPJobFailedError(
                        f"render job {job_id} failed: {detail}", job_id=job_id, errors=status.errors
                    )
                return RenderResult(
                    job_id=status.job_id,
                    status=status.status,
                    artifacts=status.artifacts,
                    artifacts_native=status.artifacts_native,
                    errors=status.errors,
                    progress=status.progress,
                )
            if on_poll is not None:
                on_poll(status)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise WangPTimeoutError(
                    f"render job {job_id} still running after {timeout:.0f}s", job_id=job_id
                )
            time.sleep(min(interval, remaining))

    def render(
        self,
        payload: Mapping[str, Any],
        resolved: ResolvedSettings,
        *,
        timeout: float | None = None,
        poll_interval: float | None = None,
        on_poll: Callable[[JobStatus], None] | None = None,
    ) -> RenderResult:
        """Submit + wait: the common path for one shot."""
        job = self.submit_render(payload, resolved)
        if job.status in ("completed", "cancelled") and job.snapshot:
            status = parse_job_status(job.snapshot)
            if status.status == "failed":
                detail = "; ".join(status.errors) or "renderer reported failure"
                raise WangPJobFailedError(
                    f"render job {job.job_id} failed: {detail}", job_id=job.job_id, errors=status.errors
                )
            return RenderResult(
                job_id=status.job_id,
                status=status.status,
                artifacts=status.artifacts,
                artifacts_native=status.artifacts_native,
                errors=status.errors,
                progress=status.progress,
            )
        return self.wait_for_job(job, timeout=timeout, poll_interval=poll_interval, on_poll=on_poll)

    def cancel_job(self, job_id: str) -> JobStatus:
        capabilities = self.connect()
        if capabilities.job_cancel is None:
            raise WangPProtocolError("renderer exposes no job-cancellation tool")
        kind, name = capabilities.job_cancel
        if kind == "tool":
            payload = self._call_tool(name, {"job_id": job_id}, idempotent=False)
        else:
            payload = self._call_tool(
                name, {"action": "cancel_job", "arguments": {"job_id": job_id}}, idempotent=False
            )
        status = parse_job_status(payload)
        self._track(status)  # a cancelled job is no longer in flight
        return status

    # -- render in-flight state (the VRAM overflow signal) --------------------

    def render_in_flight(self) -> bool:
        """Explicit in-flight signal: True while an accepted job is queued or running.

        False once that job is completed, failed, or cancelled. This is the
        method the LLM router's ``RenderStateProvider`` protocol asks for, so a
        client can be handed to the router directly as its ``render_state``.

        Client-local job state only: no network call, no GPU/VRAM sampling, no
        process inspection. Renders submitted outside this client are invisible
        to it (the renderer exposes job state by id only, and inferring activity
        from VRAM is forbidden) — see ``docs/wangp-client.md``.
        """
        with self._active_lock:
            return any(is_in_flight_status(status) for status in self._active_jobs.values())

    def render_state(self) -> RenderStateSnapshot:
        """The state behind :meth:`render_in_flight`, shaped for logs/metrics."""
        with self._active_lock:
            jobs = {
                job_id: status
                for job_id, status in self._active_jobs.items()
                if is_in_flight_status(status)
            }
        return RenderStateSnapshot(in_flight=bool(jobs), jobs=jobs, probed=False)

    def refresh_render_state(
        self, *, job_ids: Sequence[str] | None = None
    ) -> RenderStateSnapshot:
        """Re-poll tracked jobs and reconcile the table; return the fresh state.

        Optional — :meth:`render_in_flight` never needs it. Use it to clear
        entries for jobs that finished while nobody was polling them. A probe
        that cannot reach the renderer does NOT clear the signal: unknown counts
        as busy (``stale=True`` + ``probe_error``) until a probe succeeds or
        :meth:`forget_job` is called.
        """
        with self._active_lock:
            tracked = tuple(self._active_jobs) if job_ids is None else tuple(job_ids)
        probed = False
        error: str | None = None
        for job_id in tracked:
            try:
                self.get_job(job_id)  # reconciles the job table as a side effect
                probed = True
            except WangPError as exc:
                error = f"{type(exc).__name__}: {exc}"
        snapshot = self.render_state()
        return RenderStateSnapshot(
            in_flight=snapshot.in_flight,
            jobs=snapshot.jobs,
            probed=probed,
            stale=error is not None,
            probe_error=error,
        )

    def active_job_ids(self) -> tuple[str, ...]:
        """Ids of jobs this client submitted that have not reached a terminal state."""
        with self._active_lock:
            return tuple(self._active_jobs)

    def is_busy(self) -> bool:
        """Back-compat alias for :meth:`render_in_flight`."""
        return self.render_in_flight()

    def forget_job(self, job_id: str) -> bool:
        """Stop tracking a job (escape hatch after an out-of-band renderer kill)."""
        with self._active_lock:
            return self._active_jobs.pop(job_id, None) is not None

    def _track(self, status: JobStatus) -> None:
        """Reconcile the job table from a status the renderer just reported."""
        with self._active_lock:
            if is_in_flight_status(status.status):
                self._active_jobs[status.job_id] = status.status
            else:
                self._active_jobs.pop(status.job_id, None)

    # -- plumbing ------------------------------------------------------------

    def _call_tool(self, name: str, arguments: Mapping[str, Any], *, idempotent: bool,
                   timeout: float | None = None) -> Any:
        result = self._transport.post(
            "tools/call",
            {"name": name, "arguments": dict(arguments)},
            timeout=self.config.request_timeout_s if timeout is None else timeout,
            retry=idempotent,
        )
        return _unwrap_tool_result(result, name)
