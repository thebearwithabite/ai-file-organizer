"""The documented integration run, exercised against a mocked renderer.

The acceptance criterion is "a documented integration run produces actual
video files from a sample script against a live WanGP instance". This module
proves the documented run *path* works end to end and that its artifact
verification is real, without needing the GPU: it drives
``scripts/pipeline_live_run.py`` against the recorded MCP fixtures, with real
files written to a temp directory so the "does the artifact exist?" check has
something true to find.

What it does NOT do is claim a live render happened. The GPU-side procedure is
in ``docs/script-to-video-pipeline.md`` and is an operator action; the tests
here cover everything around it.
"""
from __future__ import annotations

import ast
import json
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "wangp_mcp"
LIVE_SCRIPT = REPO_ROOT / "scripts" / "pipeline_live_run.py"
SAMPLE_SCRIPT = REPO_ROOT / "examples" / "scripts" / "sample_dawn.md"
SAMPLE_SHOTS = REPO_ROOT / "examples" / "shotspec_pipeline.json"


def _fixture_result(name: str) -> Dict[str, Any]:
    """The JSON-RPC ``result`` object from a recorded fixture.

    Not the whole file: handing the envelope back makes the client look for
    ``tools`` one level too deep and it reports a protocol error.
    """
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["result"]


class ArtifactRenderer:
    """Mocked WanGP that writes a real file for every render it reports.

    The point is that the live script's artifact check has something genuine
    to verify. A mock that returned paths without writing them would make the
    check look like it works while proving nothing.
    """

    def __init__(self, out_dir: Path, *, size_bytes: int = 4096) -> None:
        self.out_dir = out_dir
        self.size_bytes = size_bytes
        self.written: List[Path] = []
        self.render_count = 0
        self.initialize = _fixture_result("01_initialize.json")
        self.tools = _fixture_result("02_tools_list.json")
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.port = 0

    def start(self) -> int:
        renderer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
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
                payload = renderer._respond(request)
                body = b"" if payload is None else json.dumps(payload).encode("utf-8")
                self.send_response(202 if payload is None else 200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if body:
                    self.wfile.write(body)

        self.out_dir.mkdir(parents=True, exist_ok=True)
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

    def _write_artifact(self, job_id: str) -> str:
        """Write a real file and return its path, as the renderer would."""
        self.render_count += 1
        target = self.out_dir / f"{job_id}_shot{self.render_count}.mp4"
        target.write_bytes(b"\x00" * self.size_bytes)
        self.written.append(target)
        return str(target)

    def _respond(self, request: Mapping[str, Any]) -> Any:
        method = request.get("method")
        rid = request.get("id")
        if method is None:  # a notification; 202 with no body
            return None
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": rid, "result": self.initialize}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": rid, "result": self.tools}
        if method == "tools/call":
            name = request.get("params", {}).get("name", "")
            if "generate" in name:
                job_id = f"job{self.render_count + 1:04d}"
                submitted = json.loads(json.dumps(_fixture_result("gguf_q4_generate.json")))
                return {"jsonrpc": "2.0", "id": rid, "result": _restamp(submitted, job_id)}
            job_id = request.get("params", {}).get("arguments", {}).get("job_id", "job0001")
            artifact = self._write_artifact(job_id)
            final = json.loads(json.dumps(_fixture_result("gguf_q4_job_final.json")))
            return {"jsonrpc": "2.0", "id": rid, "result": _restamp(final, job_id, artifact)}
        return {"jsonrpc": "2.0", "id": rid, "result": {}}


def _restamp(
    envelope: Dict[str, Any], job_id: str, artifact: Optional[str] = None
) -> Dict[str, Any]:
    structured = envelope.get("structuredContent")
    if not isinstance(structured, dict):
        return envelope
    structured["job_id"] = job_id
    if artifact is not None:
        structured["done"] = True
        structured["result"] = {
            "success": True,
            "cancelled": False,
            "generated_files": [artifact],
            "errors": [],
            "artifacts": [],
        }
        for event in structured.get("events") or []:
            if isinstance(event, dict) and event.get("kind") == "completed":
                event["data"] = dict(structured["result"])
    envelope["content"] = [{"type": "text", "text": json.dumps(structured, indent=2)}]
    return envelope


@pytest.fixture
def artifact_renderer(tmp_path):
    renderer = ArtifactRenderer(tmp_path / "outputs")
    renderer.start()
    try:
        yield renderer
    finally:
        renderer.stop()


def _dead_port() -> int:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


def _run_live(*args: str, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(LIVE_SCRIPT), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# The sample assets the documented run uses
# ---------------------------------------------------------------------------


def test_sample_assets_exist():
    assert LIVE_SCRIPT.is_file(), "the documented live-run script is missing"
    assert SAMPLE_SCRIPT.is_file(), "the sample script is missing"
    assert SAMPLE_SHOTS.is_file(), "the sample shot list is missing"


def test_sample_shots_validate_and_recur_one_character():
    from backend.services.shot_spec import validate_shot_specs

    raw = json.loads(SAMPLE_SHOTS.read_text(encoding="utf-8"))
    shots = validate_shot_specs(raw["shots"], source=str(SAMPLE_SHOTS))
    assert len(shots) == 2

    first = {e.entity_id: e.description for e in shots[0].entities}
    assert "char_maya" in first
    for shot in shots[1:]:
        for entity in shot.entities:
            if entity.entity_id == "char_maya":
                # Same id AND same description: that repetition IS the
                # consistency mechanism, so a divergence is a real defect.
                assert entity.description == first["char_maya"]
                assert entity.name == "Maya"


def test_sample_shots_are_engine_neutral():
    """No engine names leak into the fixture the pipeline feeds the compiler."""
    text = SAMPLE_SHOTS.read_text(encoding="utf-8")
    for banned in ("wan2gp", "ltx", "engine", "generation", "template_id"):
        assert banned not in text.lower(), f"sample shot list mentions {banned!r}"


# ---------------------------------------------------------------------------
# Preflight behaviour with no renderer
# ---------------------------------------------------------------------------


def test_live_run_skips_cleanly_with_no_renderer(tmp_path):
    """Without a renderer the live script SKIPs (exit 0) and prints the fix.

    A hard failure here would make the script useless as a preflight check,
    which is how it is most often used.
    """
    proc = _run_live(
        "--script", str(SAMPLE_SCRIPT),
        "--host", "127.0.0.1", "--port", str(_dead_port()),
        "--out", str(tmp_path / "runs"),
        timeout=180,
    )
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 0, combined[-2000:]
    assert "SKIP" in combined
    assert "--mcp-transport streamable-http" in combined, (
        "a skip must tell the operator exactly how to start the renderer"
    )


def test_live_run_fails_hard_with_require_and_no_renderer(tmp_path):
    """--require turns the skip into a failure, for CI that must not skip."""
    proc = _run_live(
        "--script", str(SAMPLE_SCRIPT),
        "--host", "127.0.0.1", "--port", str(_dead_port()),
        "--require", "--out", str(tmp_path / "runs"),
        timeout=180,
    )
    assert proc.returncode == 2
    assert "unreachable" in (proc.stdout + proc.stderr).lower()


def test_live_run_rejects_a_bad_shot_list_before_touching_the_renderer(tmp_path):
    """A malformed --shots file fails fast, naming the schema problem.

    Validation happens before any renderer contact: no point discovering a bad
    shot list after a twenty-minute render.
    """
    bad = tmp_path / "bad_shots.json"
    bad.write_text('{"shots": [{"shot_id": "nope"}]}', encoding="utf-8")

    proc = _run_live(
        "--script", str(SAMPLE_SCRIPT),
        "--shots", str(bad),
        "--host", "127.0.0.1", "--port", "1",
        "--out", str(tmp_path / "runs"), "--require",
        timeout=180,
    )
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 2, combined[-2000:]
    assert "invalid shotspec" in combined.lower()
    assert "renderer: http" not in combined.lower(), (
        "shot-list validation must run before the renderer is contacted"
    )


# ---------------------------------------------------------------------------
# The documented run, with a mocked renderer
# ---------------------------------------------------------------------------


def test_documented_run_produces_verified_artifacts(artifact_renderer, tmp_path):
    """The whole documented path, with real files for the check to find.

    sample script -> shot list -> compile -> render -> review -> manifest ->
    artifact existence check -> exit 0.
    """
    runs_dir = tmp_path / "runs"
    proc = _run_live(
        "--script", str(SAMPLE_SCRIPT),
        "--shots", str(SAMPLE_SHOTS),
        "--host", "127.0.0.1", "--port", str(artifact_renderer.port),
        "--out", str(runs_dir),
        "--require",
    )
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 0, combined[-4000:]

    # The renderer really wrote files, and the script really found them.
    assert artifact_renderer.written, "the mocked renderer wrote nothing"
    assert artifact_renderer.render_count == 2, (
        f"expected one render per shot, got {artifact_renderer.render_count}"
    )
    for path in artifact_renderer.written:
        assert path.is_file() and path.stat().st_size > 0
    assert "ARTIFACT NOT ON DISK" not in combined
    assert "OK:" in combined

    # A manifest was persisted carrying every required field.
    manifests = sorted(runs_dir.glob("*.json"))
    assert len(manifests) == 1, f"expected exactly one manifest, got {manifests}"
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))

    assert manifest["status"] == "completed"
    assert manifest["summary"]["shots"] == 2
    assert manifest["summary"]["passed"] == 2
    assert manifest["summary"]["total_attempts"] == 2
    assert manifest["script"]["sha256"]

    for shot in manifest["shots"]:
        assert shot["final_status"] == "passed"
        assert shot["shot_spec"]["shot_id"]                 # the ShotSpec
        assert shot["compile"]["template"]["template_id"]  # the template
        assert "overrides" in shot["compile"]               # the overrides
        assert isinstance(shot["compile"]["seed"], int)
        attempt = shot["attempts"][0]
        assert attempt["job_id"]                            # the render job id
        assert attempt["artifacts"], "artifact paths (WSL form)"
        assert attempt["artifacts_native"], "artifact paths (Windows form)"
        assert attempt["prompt_sha256_16"]
        assert attempt["review"]["reviewer"] == "artifact-probe"

    assert manifest["renderer"]["api_flavor"], "the renderer's surface is recorded"
    assert "router" in manifest, "routing decisions are recorded"


def test_manifest_from_the_documented_run_is_reproducible(artifact_renderer, tmp_path):
    """Two runs of the same inputs produce the same manifest fingerprint."""
    from backend.services.run_manifest import RunManifest, manifest_fingerprint

    fingerprints = []
    for i in range(2):
        runs_dir = tmp_path / f"runs{i}"
        proc = _run_live(
            "--script", str(SAMPLE_SCRIPT),
            "--shots", str(SAMPLE_SHOTS),
            "--host", "127.0.0.1", "--port", str(artifact_renderer.port),
            "--out", str(runs_dir),
            "--require",
        )
        assert proc.returncode == 0, (proc.stdout + proc.stderr)[-3000:]
        manifests = sorted(runs_dir.glob("*.json"))
        assert len(manifests) == 1
        fingerprints.append(manifest_fingerprint(RunManifest.load(manifests[0])))

    assert fingerprints[0] == fingerprints[1], (
        "two runs of identical inputs produced different fingerprints"
    )


def test_live_run_detects_a_phantom_artifact(tmp_path):
    """A renderer that reports a path it never wrote must fail the run.

    This check is what stops the pipeline reporting a false win, so it needs
    its own negative test rather than only riding along in the happy path.
    """

    class PhantomRenderer(ArtifactRenderer):
        def _write_artifact(self, job_id: str) -> str:
            self.render_count += 1
            # Report a path. Do not create it.
            return str(self.out_dir / f"never_written_{self.render_count}.mp4")

    renderer = PhantomRenderer(tmp_path / "outputs")
    renderer.start()
    try:
        proc = _run_live(
            "--script", str(SAMPLE_SCRIPT),
            "--shots", str(SAMPLE_SHOTS),
            "--host", "127.0.0.1", "--port", str(renderer.port),
            "--out", str(tmp_path / "runs"),
            "--require",
        )
    finally:
        renderer.stop()

    combined = proc.stdout + proc.stderr
    assert proc.returncode == 1, combined[-3000:]
    assert "not on disk" in combined.lower()


# ---------------------------------------------------------------------------
# Static guardrail on the live script itself
# ---------------------------------------------------------------------------


def _dotted_name(node: ast.AST) -> Optional[str]:
    parts: List[str] = []
    current: Optional[ast.AST] = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def test_live_script_never_writes_or_deletes_directly():
    """The only file the live script writes is its manifest, via save().

    It must not delete anything either: ``D:\\Wan2GP`` and ``/mnt/d/wan2gp``
    are the same directory and hold the renderer's model and output stores.
    """
    tree = ast.parse(LIVE_SCRIPT.read_text(encoding="utf-8"), filename=str(LIVE_SCRIPT))
    string_safe = {"replace", "split", "join", "strip", "format", "encode"}
    destructive = {
        "unlink", "rmtree", "rmdir", "rename", "remove", "replace", "touch",
        "write_text", "write_bytes", "truncate",
    }
    offenders: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        dotted = _dotted_name(node.func)
        if not dotted:
            continue
        attr = dotted.rsplit(".", 1)[-1]
        if attr not in destructive:
            continue
        receiver = dotted.rsplit(".", 1)[0] if "." in dotted else ""
        if receiver.rsplit(".", 1)[-1] in string_safe:
            continue
        offenders.append(f"{dotted}()")
    assert offenders == [], f"live script mutates the filesystem directly: {offenders}"