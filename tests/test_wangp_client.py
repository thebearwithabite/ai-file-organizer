"""WanGP renderer client tests against a local mocked MCP server.

The mock speaks JSON-RPC 2.0 over POST /mcp/ like the real renderer
(``--mcp --mcp-transport streamable-http``) and replays recorded live
responses from ``tests/fixtures/wangp_mcp/``. Loopback only; no real network.
"""
from __future__ import annotations

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping

import pytest

from backend.integrations.paths import win_to_wsl_path
from backend.integrations.wangp_client import (
    WangPClient,
    WangPConnectionError,
    WangPJobFailedError,
    WangPProtocolError,
    WangPRendererError,
    WangPTimeoutError,
)
from backend.integrations.wangp_config import WangPMCPConfig, launch_command
from backend.integrations.wangp_settings import (
    ResolvedSettings,
    SettingsDisciplineError,
    TemplateDeviationError,
)

FIXTURES = Path(__file__).parent / "fixtures" / "wangp_mcp"

MINI_TEMPLATE = {
    "model_type": "ltx2_22B_distilled_gguf_q4_k_m",
    "resolution": "1280x720",
    "video_length": 97,
    "num_inference_steps": 8,
    "guidance_phases": 2,
}
MINI_OVERRIDES = {"width": 512, "height": 320}

ALL_OVERRIDES = {
    "width": 512,
    "height": 320,
    "frames": 9,
    "fps": 24,
    "steps": 12,
    "loras": ["Ltx2.3-Licon-VBVR-I2V-96000-R32.safetensors"],
}


def load_fixture_result(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["result"]


def replay(name: str, *, job_id: str | None = None) -> dict[str, Any]:
    """Deep copy of a recorded tool result; optionally re-stamp its job id."""
    envelope = json.loads(json.dumps(load_fixture_result(name)))
    if job_id is not None and isinstance(envelope.get("structuredContent"), Mapping):
        envelope["structuredContent"]["job_id"] = job_id
        envelope["content"] = [
            {"type": "text", "text": json.dumps(envelope["structuredContent"], indent=2)}
        ]
    return envelope


def _result(rid: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _free_port() -> int:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


class FakeRenderer:
    """Scripted behavior for the mocked renderer endpoint."""

    def __init__(self) -> None:
        self.initialize_result: dict[str, Any] = load_fixture_result("01_initialize.json")
        self.tools_list_result: dict[str, Any] = load_fixture_result("02_tools_list.json")
        self.generate_queue: list[Any] = []
        self.get_job_queue: list[Any] = []
        self.persistent_get_job: Any = None
        self.extra_tool_results: dict[str, Any] = {}
        self.initialize_failures = 0
        self.generate_failures = 0
        self.garbage_methods: set[str] = set()
        self.sleep_before: dict[str, float] = {}

    def generate(self, *results: Any) -> None:
        self.generate_queue.extend(results)

    def jobs(self, *results: Any) -> None:
        self.get_job_queue.extend(results)

    def respond(self, request: Mapping[str, Any]) -> tuple[int, Any, str | None]:
        method = request.get("method")
        rid = request.get("id")
        if method is None:
            return 202, b"", "text/plain"
        if method in self.garbage_methods:
            return 200, b"<html>this is not a JSON-RPC body</html>", "text/html"
        if method == "initialize":
            time.sleep(self.sleep_before.get("initialize", 0.0))
            if self.initialize_failures > 0:
                self.initialize_failures -= 1
                return 500, {"error": "simulated initialize failure"}, None
            return 200, _result(rid, self.initialize_result), None
        if method == "tools/list":
            return 200, _result(rid, self.tools_list_result), None
        if method.startswith("notifications/"):
            return 202, b"", "text/plain"
        if method == "tools/call":
            params = request.get("params") or {}
            name = str(params.get("name", ""))
            time.sleep(self.sleep_before.get(name, 0.0))
            if name == "wangp_generate":
                if self.generate_failures > 0:
                    self.generate_failures -= 1
                    return 500, {"error": "simulated generate failure"}, None
                if self.generate_queue:
                    payload = self.generate_queue.pop(0)
                else:
                    payload = {
                        "isError": True,
                        "content": [{"type": "text", "text": "no scripted generate response"}],
                    }
                return 200, _result(rid, payload), None
            if name == "wangp_get_job" or (
                name == "wangp_session"
                and (params.get("arguments") or {}).get("action") == "get_job"
            ):
                if self.get_job_queue:
                    payload = self.get_job_queue.pop(0)
                elif self.persistent_get_job is not None:
                    payload = self.persistent_get_job
                else:
                    payload = {
                        "isError": True,
                        "content": [{"type": "text", "text": "no scripted job response"}],
                    }
                return 200, _result(rid, payload), None
            if name in self.extra_tool_results:
                return 200, _result(rid, self.extra_tool_results[name]), None
        return 404, {"error": f"unhandled method {method!r}"}, None


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *args: Any) -> None:  # keep pytest output clean
        pass

    def do_POST(self) -> None:
        server: Any = self.server
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            request = json.loads(raw.decode("utf-8"))
        except Exception:
            request = None
        server.requests.append(
            {
                "path": self.path,
                "body": request if isinstance(request, dict) else None,
                "method": request.get("method") if isinstance(request, dict) else None,
                "tool": (request.get("params") or {}).get("name")
                if isinstance(request, dict)
                else None,
            }
        )
        if not isinstance(request, dict):
            self._emit(400, b"bad request body", "text/plain")
            return
        status, body, content_type = server.renderer.respond(request)
        if body is None:
            body = b""
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
            content_type = content_type or "application/json"
        self._emit(status, body, content_type or "application/octet-stream")

    def _emit(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)


class MockMCP:
    """A loopback HTTP server that behaves like the renderer's /mcp/ endpoint."""

    def __init__(self, renderer: FakeRenderer) -> None:
        self.renderer = renderer
        self.requests: list[dict[str, Any]] = []
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._httpd.renderer = renderer  # type: ignore[attr-defined]
        self._httpd.requests = self.requests  # type: ignore[attr-defined]
        self.host, self.port = self._httpd.server_address[:2]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def __enter__(self) -> "MockMCP":
        self._thread.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)

    def calls(self, method: str | None = None, tool: str | None = None) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for record in self.requests:
            if method is not None and record["method"] != method:
                continue
            if tool is not None and record["tool"] != tool:
                continue
            found.append(record)
        return found

    def config(self, **overrides: Any) -> WangPMCPConfig:
        base: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "retry_backoff_s": 0.01,
            "retry_backoff_max_s": 0.05,
        }
        base.update(overrides)
        return WangPMCPConfig(**base)


def make_client(mock: MockMCP, **config_overrides: Any) -> WangPClient:
    return WangPClient(mock.config(**config_overrides))


def submit_payload() -> tuple[dict[str, Any], ResolvedSettings]:
    resolved = ResolvedSettings.from_template(MINI_TEMPLATE, MINI_OVERRIDES)
    return resolved.build_payload({"prompt": "A red apple on a wooden table."}), resolved


V2_TOOLS = [
    {
        "name": "wangp_generate",
        "description": "generate",
        "inputSchema": {
            "type": "object",
            "properties": {
                "settings": {
                    "anyOf": [
                        {"type": "object"},
                        {"type": "array", "items": {"type": "object"}, "minItems": 1},
                    ]
                },
                "wait": {"type": "boolean", "default": True, "const": True},
                "timeout_s": {"type": ["number", "null"], "minimum": 0, "default": None},
                "event_limit": {"type": "integer", "minimum": 0, "maximum": 500, "default": 0},
            },
            "required": ["settings"],
            "additionalProperties": False,
        },
    },
    {
        "name": "wangp_model",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model_type": {"type": "string"},
                "action": {"type": "string"},
                "arguments": {"type": "object"},
            },
        },
    },
    {
        "name": "wangp_session",
        "inputSchema": {
            "type": "object",
            "properties": {"action": {"type": "string"}, "arguments": {"type": "object"}},
        },
    },
    {"name": "wangp_postprocess", "inputSchema": {"type": "object", "properties": {"media": {"type": "string"}}}},
]


class TestHappyPathV1:
    def test_submit_poll_returns_translated_artifacts(self):
        renderer = FakeRenderer()
        generate = replay("gguf_q4_generate.json")
        job_id = generate["structuredContent"]["job_id"]
        renderer.extra_tool_results["wangp_get_default_settings"] = replay(
            "05_get_default_settings_gguf_q4.json"
        )
        renderer.generate(generate)
        renderer.jobs(
            replay("int8_job_poll.json", job_id=job_id),
            replay("gguf_q4_job_final.json", job_id=job_id),
        )
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            capabilities = client.connect()
            assert capabilities.api_flavor == "v1"
            assert capabilities.settings_arg == "source"
            assert capabilities.wait_style == "optional"
            assert capabilities.job_get == ("tool", "wangp_get_job")
            assert len(capabilities.tool_names) == 11
            assert "wangp_generate" in capabilities.tool_names

            template = client.get_default_settings("ltx2_22B_distilled_gguf_q4_k_m")
            assert template["resolution"] == "1280x720"
            assert template["model_type"] == "ltx2_22B_distilled_gguf_q4_k_m"

            resolved = ResolvedSettings.from_template(template, ALL_OVERRIDES)
            payload = resolved.build_payload({"prompt": "A red apple on a wooden table."})
            polls: list[Any] = []
            result = client.render(
                payload, resolved, timeout=30, poll_interval=0.02, on_poll=polls.append
            )

            assert result.ok and result.status == "completed"
            native = load_fixture_result("gguf_q4_job_final.json")["structuredContent"][
                "result"
            ]["generated_files"]
            assert result.artifacts_native == tuple(native)
            assert result.artifacts == tuple(win_to_wsl_path(path) for path in native)
            assert result.artifacts[0].startswith("/mnt/d/Wan2GP/outputs/")

            generate_calls = mock.calls("tools/call", tool="wangp_generate")
            assert len(generate_calls) == 1
            sent = generate_calls[0]["body"]["params"]["arguments"]
            assert set(sent) == {"source", "wait", "event_limit"}
            assert sent["wait"] is False
            source = sent["source"]
            assert source["resolution"] == "512x320"
            assert source["video_length"] == 9
            assert source["force_fps"] == 24
            assert source["num_inference_steps"] == 12
            assert source["activated_loras"] == [
                "Ltx2.3-Licon-VBVR-I2V-96000-R32.safetensors"
            ]
            assert source["guidance_phases"] == template["guidance_phases"]  # untouched
            assert source["model_type"] == "ltx2_22B_distilled_gguf_q4_k_m"

            assert len(mock.calls("tools/call", tool="wangp_get_job")) == 2
            assert len(polls) == 2  # submit snapshot + first poll
            assert client.active_job_ids() == ()
            assert not client.is_busy()


class TestV2Surface:
    def test_detects_v2_and_parks_jobs_via_session(self):
        renderer = FakeRenderer()
        renderer.tools_list_result = {"tools": V2_TOOLS}
        generate = replay("gguf_q4_generate.json")
        job_id = generate["structuredContent"]["job_id"]
        renderer.generate(generate)
        renderer.jobs(replay("gguf_q4_job_final.json", job_id=job_id))
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            capabilities = client.connect()
            assert capabilities.api_flavor == "v2"
            assert capabilities.settings_arg == "settings"
            assert capabilities.wait_style == "forced"
            assert capabilities.job_get == ("session", "wangp_session")
            assert capabilities.job_cancel == ("session", "wangp_session")
            assert capabilities.default_settings_style == "model_action"

            resolved = ResolvedSettings.from_template(
                MINI_TEMPLATE, {"width": 512, "height": 320, "frames": 9, "steps": 8}
            )
            payload = resolved.build_payload({"prompt": "hello"})
            result = client.render(payload, resolved, timeout=30, poll_interval=0.02)

            sent = mock.calls("tools/call", tool="wangp_generate")[0]["body"]["params"][
                "arguments"
            ]
            assert set(sent) == {"settings", "wait", "timeout_s", "event_limit"}
            assert sent["wait"] is True
            assert sent["timeout_s"] == 0.0  # park: return the job, never cancel it
            assert sent["settings"]["model_type"] == "ltx2_22B_distilled_gguf_q4_k_m"
            assert sent["settings"]["video_length"] == 9

            session_calls = mock.calls("tools/call", tool="wangp_session")
            assert len(session_calls) == 1
            assert session_calls[0]["body"]["params"]["arguments"] == {
                "action": "get_job",
                "arguments": {"job_id": job_id},
            }
            assert result.ok
            native = load_fixture_result("gguf_q4_job_final.json")["structuredContent"][
                "result"
            ]["generated_files"]
            assert result.artifacts == tuple(win_to_wsl_path(path) for path in native)


class TestFailures:
    def test_poll_timeout_raises_with_job_id(self):
        renderer = FakeRenderer()
        generate = replay("gguf_q4_generate.json")
        job_id = generate["structuredContent"]["job_id"]
        renderer.generate(generate)
        renderer.persistent_get_job = replay("int8_job_poll.json", job_id=job_id)
        with MockMCP(renderer) as mock:
            client = make_client(mock, poll_interval_s=0.05)
            payload, resolved = submit_payload()
            job = client.submit_render(payload, resolved)
            with pytest.raises(WangPTimeoutError) as excinfo:
                client.wait_for_job(job, timeout=0.3, poll_interval=0.05)
            assert excinfo.value.job_id == job_id
            assert len(mock.calls("tools/call", tool="wangp_get_job")) >= 2

    def test_request_timeout_is_not_retried(self):
        renderer = FakeRenderer()
        renderer.sleep_before["wangp_generate"] = 1.0
        with MockMCP(renderer) as mock:
            client = make_client(mock, submit_timeout_s=0.25)
            payload, resolved = submit_payload()
            with pytest.raises(WangPTimeoutError):
                client.submit_render(payload, resolved)
            assert len(mock.calls("tools/call", tool="wangp_generate")) == 1

    def test_connection_refused_reports_launch_command(self):
        port = _free_port()
        config = WangPMCPConfig(
            host="127.0.0.1",
            port=port,
            retry_attempts=2,
            retry_backoff_s=0.01,
            retry_backoff_max_s=0.02,
        )
        client = WangPClient(config)
        with pytest.raises(WangPConnectionError) as excinfo:
            client.connect()
        message = str(excinfo.value)
        assert f"127.0.0.1:{port}" in message
        for needle in (
            "--mcp",
            "--mcp-transport streamable-http",
            "--mcp-host",
            "--mcp-port",
        ):
            assert needle in message

    def test_malformed_json_body(self):
        renderer = FakeRenderer()
        renderer.garbage_methods.add("initialize")
        with MockMCP(renderer) as mock:
            client = make_client(mock, retry_attempts=1)
            with pytest.raises(WangPProtocolError, match="malformed JSON-RPC body"):
                client.connect()

    def test_tool_result_of_wrong_type(self):
        renderer = FakeRenderer()
        renderer.generate("definitely-not-an-object")
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            with pytest.raises(WangPProtocolError, match="malformed tool result"):
                client.submit_render(payload, resolved)

    def test_renderer_iserror_surfaces_as_wangp_error(self):
        renderer = FakeRenderer()
        renderer.generate(
            {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": "Error executing tool wangp_generate: unknown model_type",
                    }
                ],
            }
        )
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            with pytest.raises(WangPRendererError, match="unknown model_type"):
                client.submit_render(payload, resolved)

    def test_generate_response_without_job_id(self):
        renderer = FakeRenderer()
        renderer.generate({"structuredContent": {"done": False}, "isError": False})
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            with pytest.raises(WangPProtocolError, match="missing job_id"):
                client.submit_render(payload, resolved)

    def test_job_snapshot_without_job_id(self):
        renderer = FakeRenderer()
        renderer.generate(replay("gguf_q4_generate.json"))
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            job = client.submit_render(payload, resolved)
            renderer.jobs(
                {"isError": False, "structuredContent": {"done": True, "result": {"generated_files": []}}}
            )
            with pytest.raises(WangPProtocolError, match="missing job_id"):
                client.get_job(job.job_id)

    def test_failed_job_raises_with_errors_and_job_id(self):
        renderer = FakeRenderer()
        generate = replay("gguf_q4_generate.json")
        job_id = generate["structuredContent"]["job_id"]
        renderer.generate(generate)
        renderer.jobs(
            {
                "isError": False,
                "structuredContent": {
                    "job_id": job_id,
                    "done": True,
                    "cancel_requested": False,
                    "created_at": 0.0,
                    "updated_at": 1.0,
                    "events": [],
                    "result": {
                        "success": False,
                        "cancelled": False,
                        "errors": ["out of memory"],
                        "generated_files": [],
                        "artifacts": [],
                    },
                },
            }
        )
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            with pytest.raises(WangPJobFailedError) as excinfo:
                client.render(payload, resolved, timeout=10, poll_interval=0.02)
            assert excinfo.value.job_id == job_id
            assert "out of memory" in str(excinfo.value)


class TestRetrySemantics:
    def test_idempotent_calls_retry_with_backoff(self):
        renderer = FakeRenderer()
        renderer.initialize_failures = 1
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            capabilities = client.connect()  # first initialize 500s, second succeeds
            assert capabilities.tool_names
            assert len(mock.calls("initialize")) == 2

    def test_submit_is_never_retried(self):
        renderer = FakeRenderer()
        renderer.generate_failures = 1
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            payload, resolved = submit_payload()
            with pytest.raises(WangPProtocolError):
                client.submit_render(payload, resolved)
            assert len(mock.calls("tools/call", tool="wangp_generate")) == 1


class TestDisciplineAtBoundary:
    def test_violations_never_reach_the_renderer(self):
        renderer = FakeRenderer()
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            resolved = ResolvedSettings.from_template(MINI_TEMPLATE, MINI_OVERRIDES)

            smuggled = resolved.build_payload({"prompt": "x"})
            smuggled["mystery_setting"] = 1
            with pytest.raises(SettingsDisciplineError):
                client.submit_render(smuggled, resolved)

            deviant = resolved.build_payload({"prompt": "x"})
            deviant["num_inference_steps"] = 99
            with pytest.raises(TemplateDeviationError):
                client.submit_render(deviant, resolved)

            offline = resolved.build_payload({"prompt": "x"})
            offline["resolution"] = "4096x4096"
            with pytest.raises(TemplateDeviationError):
                client.submit_render(offline, resolved)

            assert mock.requests == []  # rejected before any network I/O


class TestListModels:
    def test_uses_only_declared_parameters(self):
        renderer = FakeRenderer()
        renderer.extra_tool_results["wangp_list_models"] = {
            "isError": False,
            "structuredContent": {"result": [{"model_type": "ltx2_22B_distilled_gguf_q4_k_m"}]},
        }
        with MockMCP(renderer) as mock:
            client = make_client(mock)
            models = client.list_models(family="ltx2")
            assert models == [{"model_type": "ltx2_22B_distilled_gguf_q4_k_m"}]
            sent = mock.calls("tools/call", tool="wangp_list_models")[0]["body"]["params"][
                "arguments"
            ]
            assert sent == {"family": "ltx2"}  # limit/query not declared by the schema


class TestConfig:
    def test_from_env_parses_overrides(self):
        config = WangPMCPConfig.from_env(
            {
                "WANGP_MCP_HOST": "172.24.16.1",
                "WANGP_MCP_PORT": "8899",
                "WANGP_MCP_RETRY_ATTEMPTS": "5",
                "WANGP_MCP_POLL_TIMEOUT_S": "1800",
            }
        )
        assert (config.host, config.port, config.retry_attempts) == ("172.24.16.1", 8899, 5)
        assert config.poll_timeout_s == 1800.0
        assert config.base_url == "http://172.24.16.1:8899/mcp/"

    def test_from_env_invalid_values_rejected(self):
        with pytest.raises(ValueError):
            WangPMCPConfig.from_env({"WANGP_MCP_PORT": "abc"})

    def test_invalid_port_rejected(self):
        with pytest.raises(ValueError):
            WangPMCPConfig(port=99999)

    def test_non_streamable_transport_rejected(self):
        with pytest.raises(ValueError):
            WangPMCPConfig(transport="stdio")

    def test_launch_command_contains_required_flags(self):
        command = launch_command()
        for flag in ("--mcp", "--mcp-transport streamable-http", "--mcp-host", "--mcp-port"):
            assert flag in command
        assert "0.0.0.0" not in command  # loopback only
