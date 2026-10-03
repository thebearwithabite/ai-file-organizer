"""Configuration for the WanGP MCP renderer client.

Defaults target the sanctioned topology (PROMPT-MACHINE-DIRECTIVE v1.2):
renderer on native Windows, orchestrator in WSL2, MCP over streamable-http.
All values are overridable by environment variable (``WANGP_MCP_*``) so the
client never carries deployment-specific literals at call sites.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

__all__ = [
    "WangPMCPConfig",
    "DEFAULT_WANGP_LIVE_DIR",
    "launch_command",
    "connection_help",
]

#: Live, launcher-managed renderer source tree (windows side of this box).
#: NOTE: ``D:\\Wan2GP`` is the retired fork that holds the model stores; the
#: two paths are DIFFERENT directories. Never write to either from here.
DEFAULT_WANGP_LIVE_DIR = r"C:\Users\thebe\AppData\Roaming\wan2gp-desktop\Wan2GP\Wan2GP"


@dataclass(frozen=True)
class WangPMCPConfig:
    """Connection + behavior settings for :class:`WangPClient`."""

    host: str = "127.0.0.1"
    port: int = 8899
    transport: str = "streamable-http"
    endpoint_path: str = "/mcp/"

    connect_timeout_s: float = 10.0
    request_timeout_s: float = 60.0
    submit_timeout_s: float = 120.0
    poll_interval_s: float = 2.0
    poll_timeout_s: float = 3600.0
    #: ``timeout_s`` used when the server forbids ``wait=false`` (v2 without
    #: --mcp-async). 0.0 parks the submit and lets the client poll.
    park_timeout_s: float = 0.0

    retry_attempts: int = 3
    retry_backoff_s: float = 0.5
    retry_backoff_max_s: float = 8.0

    #: Renderer install directory, used only to compose help text.
    wangp_dir: str = DEFAULT_WANGP_LIVE_DIR
    client_name: str = "ai-file-organizer-wangp-client"
    client_version: str = "0.1.0"
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.transport != "streamable-http":
            raise ValueError(
                f"unsupported transport {self.transport!r}; the renderer is reached over "
                "'streamable-http' only"
            )
        if not (1 <= int(self.port) <= 65535):
            raise ValueError(f"port out of range: {self.port!r}")
        path = self.endpoint_path or "/mcp/"
        if not path.startswith("/"):
            path = "/" + path
        object.__setattr__(self, "endpoint_path", path)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}{self.endpoint_path}"

    @classmethod
    def from_env(cls, env: os._Environ | dict | None = None) -> "WangPMCPConfig":
        env = dict(os.environ if env is None else env)
        kwargs: dict = {}
        mapping = {
            "WANGP_MCP_HOST": ("host", str),
            "WANGP_MCP_PORT": ("port", int),
            "WANGP_MCP_TRANSPORT": ("transport", str),
            "WANGP_MCP_ENDPOINT": ("endpoint_path", str),
            "WANGP_MCP_CONNECT_TIMEOUT_S": ("connect_timeout_s", float),
            "WANGP_MCP_REQUEST_TIMEOUT_S": ("request_timeout_s", float),
            "WANGP_MCP_SUBMIT_TIMEOUT_S": ("submit_timeout_s", float),
            "WANGP_MCP_POLL_INTERVAL_S": ("poll_interval_s", float),
            "WANGP_MCP_POLL_TIMEOUT_S": ("poll_timeout_s", float),
            "WANGP_MCP_PARK_TIMEOUT_S": ("park_timeout_s", float),
            "WANGP_MCP_RETRY_ATTEMPTS": ("retry_attempts", int),
            "WANGP_MCP_RETRY_BACKOFF_S": ("retry_backoff_s", float),
            "WANGP_MCP_RETRY_BACKOFF_MAX_S": ("retry_backoff_max_s", float),
            "WANGP_MCP_DIR": ("wangp_dir", str),
        }
        for name, (attr, caster) in mapping.items():
            raw = env.get(name)
            if raw is None or str(raw).strip() == "":
                continue
            try:
                kwargs[attr] = caster(str(raw).strip())
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid {name}={raw!r}: {exc}") from exc
        return cls(**kwargs)


def launch_command(config: WangPMCPConfig | None = None) -> str:
    """The exact command the operator runs on the WINDOWS side to serve MCP.

    Loopback only (never ``0.0.0.0``). Reachability from WSL2 requires either
    mirrored networking or an explicit host bind — see docs/wangp-client.md.
    """
    config = config or WangPMCPConfig()
    return (
        f"cd {config.wangp_dir}\n"
        f".\\env_uv\\Scripts\\python.exe .\\wgp.py --mcp --mcp-api-version 1 "
        f"--mcp-transport streamable-http --mcp-host {config.host} --mcp-port {config.port}"
    )


def connection_help(config: WangPMCPConfig | None = None, reason: str = "") -> str:
    """Actionable text for connection-refused style failures."""
    config = config or WangPMCPConfig()
    lines = [
        f"WanGP MCP renderer unreachable at {config.base_url}"
        + (f" ({reason})" if reason else ""),
        "Start the renderer on the Windows side, then retry:",
        launch_command(config),
        "WSL2 networking: with mirrored networking enabled, 127.0.0.1 resolves "
        "identically from both hosts. Under NAT, bind the Windows side to the "
        "WSL vEthernet adapter IP and set WANGP_MCP_HOST to the default-gateway "
        "IP seen by WSL ('ip route | grep default'). Details: docs/wangp-client.md.",
    ]
    return "\n".join(lines)
