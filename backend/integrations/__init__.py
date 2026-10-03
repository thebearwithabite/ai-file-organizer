"""Renderer integrations for the Prompt Machine pipeline.

Boundary rule (PROMPT-MACHINE-DIRECTIVE v1.2): everything Windows-shaped lives
here and nowhere above. ``paths`` translates; ``wangp_settings`` enforces the
template + six-override discipline; ``wangp_client`` speaks MCP over
streamable-http to the headless WanGP renderer.

No module in this package ever writes to or deletes the renderer install
(``D:\\Wan2GP`` / ``/mnt/d/wan2gp`` — the same directory, case-insensitive).
Read-only by construction; guarded by ``tests/test_wangp_guardrails.py``.
"""
from backend.integrations.paths import (  # noqa: F401
    same_location,
    win_to_wsl_path,
    wsl_to_win_path,
)
from backend.integrations.wangp_config import WangPMCPConfig  # noqa: F401
from backend.integrations.wangp_settings import (  # noqa: F401
    ALLOWED_OVERRIDE_KEYS,
    ResolvedSettings,
    SettingsDisciplineError,
    apply_overrides,
    build_generation_settings,
    enforce_bounded_settings,
)
from backend.integrations.wangp_client import (  # noqa: F401
    ACTIVE_JOB_STATUSES,
    TERMINAL_JOB_STATUSES,
    JobStatus,
    RenderJob,
    RenderResult,
    RenderStateSnapshot,
    WangPClient,
    is_in_flight_status,
    WangPConnectionError,
    WangPError,
    WangPJobFailedError,
    WangPProtocolError,
    WangPRendererError,
    WangPTimeoutError,
)

__all__ = [
    "ACTIVE_JOB_STATUSES",
    "ALLOWED_OVERRIDE_KEYS",
    "JobStatus",
    "RenderJob",
    "RenderResult",
    "RenderStateSnapshot",
    "ResolvedSettings",
    "SettingsDisciplineError",
    "TERMINAL_JOB_STATUSES",
    "WangPClient",
    "WangPConnectionError",
    "WangPError",
    "WangPJobFailedError",
    "WangPMCPConfig",
    "WangPProtocolError",
    "WangPRendererError",
    "WangPTimeoutError",
    "apply_overrides",
    "build_generation_settings",
    "enforce_bounded_settings",
    "is_in_flight_status",
    "same_location",
    "win_to_wsl_path",
    "wsl_to_win_path",
]
