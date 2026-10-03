#!/usr/bin/env python3
"""Live smoke render against a real WanGP MCP renderer.

Integration script for the renderer client (Prompt Machine Phase 3). It:
1. checks reachability (TCP + MCP initialize) and SKIPs cleanly when no
   renderer is running (CI-safe; exit 0 unless --require is passed);
2. fetches the renderer's OWN pristine defaults for the model as the template;
3. submits a tiny render through the six-override discipline
   (width/height/frames/fps/steps/loras only);
4. polls to completion and prints the artifact paths (native + WSL form).

Usage::

    python scripts/wangp_live_smoke.py [--host H] [--port P] [--require]
        [--model-type ltx2_22B_distilled_gguf_q4_k_m] [--timeout 1800]
        [--out smoke_result.json] [--capture-dir DIR]

The renderer must have been started on the Windows side per
docs/wangp-client.md. This script never writes to the renderer install; the
renderer itself writes its artifacts under its configured outputs directory.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.integrations.wangp_client import (  # noqa: E402
    JobStatus,
    WangPClient,
    WangPConnectionError,
    WangPError,
    WangPTimeoutError,
)
from backend.integrations.wangp_config import (  # noqa: E402
    WangPMCPConfig,
    connection_help,
    launch_command,
)
from backend.integrations.wangp_settings import ResolvedSettings  # noqa: E402

SMOKE_PROMPT = "A red apple on a wooden table, soft daylight, static camera."
SMOKE_OVERRIDES = {"width": 512, "height": 320, "frames": 9, "steps": 8}


def tcp_reachable(host: str, port: int, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, ""
    except OSError as exc:
        return False, str(exc)


def _progress(status: JobStatus) -> None:
    step = status.progress or {}
    if step:
        print(
            f"  ... {step.get('phase', 'render')} "
            f"{step.get('current_step', '?')}/{step.get('total_steps', '?')}",
            flush=True,
        )


def run_smoke(config: WangPMCPConfig, model_type: str, timeout: float, capture_dir: Path | None) -> int:
    client = WangPClient(config)
    capabilities = client.connect()
    print(f"reachable: {config.base_url}")
    print(f"server: {capabilities.server_name} {capabilities.server_version} | "
          f"api={capabilities.api_flavor} wait_style={capabilities.wait_style}")
    print(f"tools: {', '.join(capabilities.tool_names)}")

    template = client.get_default_settings(model_type)
    template["model_type"] = model_type
    resolved = ResolvedSettings.from_template(template, SMOKE_OVERRIDES, template_path="<renderer defaults>")
    payload = resolved.build_payload({"prompt": SMOKE_PROMPT})
    print(f"template: renderer defaults for {model_type}")
    print(f"overrides: {SMOKE_OVERRIDES}")

    if capture_dir is not None:
        capture_dir.mkdir(parents=True, exist_ok=True)
        (capture_dir / "smoke_payload.json").write_text(
            json.dumps({"payload": payload, "capabilities": capabilities.as_manifest()}, indent=2),
            encoding="utf-8",
        )

    job = client.submit_render(payload, resolved)
    print(f"submitted: job_id={job.job_id} status={job.status}")
    result = client.wait_for_job(job, timeout=timeout, on_poll=_progress)
    for path in result.artifacts:
        print(f"artifact: {path}")
        print(f"artifact(native): {result.artifacts_native[result.artifacts.index(path)]}")
    if capture_dir is not None:
        (capture_dir / "smoke_result.json").write_text(
            json.dumps(result.as_manifest(), indent=2), encoding="utf-8"
        )
    return 0 if result.ok and result.artifacts else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live smoke render against a WanGP MCP renderer.")
    parser.add_argument("--host", default=None, help="renderer MCP host (default: env WANGP_MCP_HOST or 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="renderer MCP port (default: env or 8899)")
    parser.add_argument("--model-type", default="ltx2_22B_distilled_gguf_q4_k_m")
    parser.add_argument("--timeout", type=float, default=1800.0, help="seconds to wait for the render")
    parser.add_argument("--out", default=None, help="write the result manifest JSON here")
    parser.add_argument("--capture-dir", default=None, help="write payload/result fixtures here")
    parser.add_argument("--require", action="store_true", help="exit 2 instead of 0 when no renderer is reachable")
    args = parser.parse_args(argv)

    config = WangPMCPConfig.from_env()
    if args.host or args.port:
        config = WangPMCPConfig(
            **{**config.__dict__, "host": args.host or config.host, "port": args.port or config.port}
        )

    reachable, reason = tcp_reachable(config.host, config.port)
    if not reachable:
        print(f"SKIP: no WanGP MCP renderer at {config.host}:{config.port} ({reason})")
        print("Start it on the Windows side with:")
        print(launch_command(config))
        return 2 if args.require else 0

    try:
        exit_code = run_smoke(
            config, args.model_type, args.timeout,
            Path(args.capture_dir) if args.capture_dir else None,
        )
    except WangPTimeoutError as exc:
        print(f"TIMEOUT: {exc}")
        return 1
    except WangPConnectionError as exc:
        print(f"UNREACHABLE: {exc}")
        return 2 if args.require else 0
    except WangPError as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")
        return 1
    if args.out:
        print(f"(manifest: run with --capture-dir to collect JSON; --out reserved)")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
