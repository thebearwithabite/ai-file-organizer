#!/usr/bin/env python3
r"""Integration run: script -> video files, against a LIVE WanGP renderer.

This is the manual path the card asks for. The test suite proves the pipeline
wires up correctly against a mocked MCP transport; this script proves it
produces actual video files from an actual script on an actual renderer.

Usage (from the WSL repo root)::

    # 0. On the WINDOWS side, start the renderer (see docs/wangp-client.md):
    #    cd C:\Users\thebe\AppData\Roaming\wan2gp-desktop\Wan2GP\Wan2GP
    #    .\env_uv\Scripts\python.exe .\wgp.py --mcp --mcp-api-version 1 \
    #        --mcp-transport streamable-http --mcp-host 127.0.0.1 --mcp-port 8899
    #
    # 1. From WSL:
    python scripts/pipeline_live_run.py --script examples/scripts/sample_dawn.md

    # 2. Or drive it from a fixed shot list (skips the director LLM entirely):
    python scripts/pipeline_live_run.py --script examples/scripts/sample_dawn.md \
        --shots examples/shotspec_pipeline.json

Exit codes
----------
0  every shot passed review and artifacts exist (or SKIP, without --require)
1  the run finished but at least one shot needs an operator, or an artifact
   the renderer claimed does not exist on disk
2  the run could not start (no renderer, bad script, bad shot list)

What it does differently from the CLI
-------------------------------------
* ``--require`` makes an unreachable renderer a hard failure instead of a skip,
  because a "successful" integration run that silently skipped is worse than
  no run at all.
* it verifies each artifact actually exists on disk before reporting success.
  A renderer that returns a path it never wrote is the single most common way
  a pipeline like this reports a false win.
* it prints the run manifest and the review verdicts so a human can see what
  the critic objected to.

It never writes to the renderer install. ``D:\Wan2GP`` and ``/mnt/d/wan2gp``
are the same directory and are guarded by ``core.path_guard``; the only file
this script writes is the run manifest under ``--out``.
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

from backend.integrations.wangp_client import WangPClient, WangPError  # noqa: E402
from backend.integrations.wangp_config import WangPMCPConfig, connection_help  # noqa: E402
from backend.services.pipeline import (  # noqa: E402
    PipelineConfig,
    PipelineError,
    ScriptToVideoPipeline,
)
from backend.services.reviewers import ArtifactProbeReviewer  # noqa: E402
from backend.services.run_manifest import manifest_fingerprint  # noqa: E402


def _reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/pipeline_live_run.py",
        description="live script-to-video integration run against a WanGP renderer",
    )
    parser.add_argument("--script", required=True, help="path to the script file")
    parser.add_argument("--shots", default=None,
                        help="ShotSpec[] JSON; skips the director pass")
    parser.add_argument("--project-id", default="")
    parser.add_argument("--out", default="runs/", help="directory for the manifest")
    parser.add_argument("--host", default=None, help="renderer host (default from env)")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--template", default=None, help="force a template_id")
    parser.add_argument("--aspect", default="16:9")
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=3600.0,
                        help="per-render poll timeout in seconds")
    parser.add_argument("--allow-cloud-script", action="store_true")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when the renderer is unreachable")
    args = parser.parse_args(argv)

    script_path = Path(args.script)
    if not script_path.is_file():
        print(f"error: no such script: {script_path}", file=sys.stderr)
        return 2
    script = script_path.read_text(encoding="utf-8")

    overrides = {}
    if args.host:
        overrides["host"] = args.host
    if args.port:
        overrides["port"] = args.port
    config = WangPMCPConfig(**{**WangPMCPConfig.from_env().__dict__, **overrides})

    # Validate the shot list BEFORE reaching for the renderer. Discovering a
    # malformed shot after a twenty-minute render is the worst possible order,
    # and it is free to check first.
    shots = None
    if args.shots:
        from backend.services.shot_spec import validate_shot_specs

        try:
            raw = json.loads(Path(args.shots).read_text(encoding="utf-8"))
            entries = raw.get("shots", raw) if isinstance(raw, dict) else raw
            shots = validate_shot_specs(list(entries), source=str(args.shots))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read --shots: {exc}", file=sys.stderr)
            return 2
        except Exception as exc:
            print(f"error: invalid ShotSpec in --shots: {exc}", file=sys.stderr)
            return 2

    print(f"renderer: {config.base_url}")
    if not _reachable(config.host, config.port):
        message = connection_help(config, "TCP connect failed")
        if args.require:
            print("error: renderer unreachable and --require was passed", file=sys.stderr)
            print(message, file=sys.stderr)
            return 2
        print("SKIP: no renderer is listening.", file=sys.stderr)
        print(message, file=sys.stderr)
        print("\nStart it on the Windows side, then re-run this script.", file=sys.stderr)
        return 0

    client = WangPClient(config)
    try:
        capabilities = client.connect()
    except WangPError as exc:
        print(f"error: MCP initialize failed: {exc}", file=sys.stderr)
        print(connection_help(config, str(exc)), file=sys.stderr)
        return 2

    print(f"  api flavor : {capabilities.api_flavor}")
    print(f"  generate   : {capabilities.generate_tool}")
    print(f"  job get    : {capabilities.job_get}")

    pipeline = ScriptToVideoPipeline(
        client=client,
        reviewer=ArtifactProbeReviewer(),
        config=PipelineConfig(
            template_id=args.template,
            aspect=args.aspect,
            max_retries=args.max_retries,
            poll_timeout_s=args.timeout,
            allow_cloud_script=args.allow_cloud_script,
        ),
    )

    try:
        if shots is not None:
            print(f"loaded {len(shots)} shots from {args.shots} (director pass skipped)")
            manifest = pipeline.run_shots(
                shots,
                project_id=args.project_id,
                script_path=str(script_path),
                script_text=script,
            )
        else:
            print("running the director pass (needs a local LLM; no cloud key needed)...")
            manifest = pipeline.run(
                script,
                project_id=args.project_id,
                script_path=str(script_path),
            )
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except WangPError as exc:
        print(f"error: renderer failed: {exc}", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    manifest_path = manifest.save(out_dir / f"{manifest.run_id}.json")

    print()
    print(f"run {manifest.run_id}: {manifest.status}")
    print(f"  fingerprint : {manifest_fingerprint(manifest)[:16]}")
    print(f"  manifest    : {manifest_path}")
    print()

    missing: list[str] = []
    for shot in manifest.shots:
        verdict = "PASS" if shot.final_status == "passed" else "HOLD"
        artifact = shot.last_artifact
        note = ""
        if artifact:
            resolved = _resolve(artifact)
            if resolved is None:
                missing.append(artifact)
                note = "  <-- ARTIFACT NOT ON DISK"
            else:
                note = f"  ({resolved.stat().st_size / 1e6:.1f} MB)"
        print(f"[{verdict}] {shot.shot_id}  {shot.attempts_used} attempt(s)")
        print(f"        {artifact or shot.error}{note}")
        for attempt in shot.attempts:
            for n in attempt.review_notes:
                print(f"          - {n}")

    if missing:
        print()
        print(f"error: {len(missing)} artifact(s) reported by the renderer are not on disk:")
        for path in missing:
            print(f"  {path}")
        print("The renderer returned paths it did not write; treat this run as failed.")
        return 1

    print()
    if manifest.status == "completed":
        print(f"OK: {len(manifest.passed_shots)}/{manifest.shot_count} shots passed review.")
        return 0
    print(f"needs an operator: {', '.join(manifest.operator_shots)}")
    return 1


def _resolve(path: str) -> Path | None:
    """Find the artifact on disk from either spelling.

    The renderer emits Windows paths and the client translates them to WSL
    form; this accepts both and also checks the translated twin, because a
    mirrored-network box can hand back either depending on the transport.
    """
    from backend.integrations.paths import win_to_wsl_path, wsl_to_win_path

    candidates: list[Path] = [Path(path)]
    for twin in (win_to_wsl_path(path), wsl_to_win_path(path)):
        candidate = Path(twin)
        if candidate not in candidates:
            candidates.append(candidate)
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


if __name__ == "__main__":
    raise SystemExit(main())