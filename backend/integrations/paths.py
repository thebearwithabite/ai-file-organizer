"""Windows <-> WSL path translation for the WanGP renderer boundary.

The renderer runs natively on Windows and emits artifact paths such as
``D:\\Wan2GP\\outputs\\clip.mp4``. The orchestrator runs in WSL2 and reads
``/mnt/d/Wan2GP/outputs/clip.mp4``. Translation happens HERE, at the client
boundary, and nowhere deeper (directive v1.2, "Path translation").

Windows paths are case-insensitive: ``D:\\Wan2GP`` and ``/mnt/d/wan2gp`` are
THE SAME DIRECTORY. The renderer install managed by the wan2gp-desktop
launcher must never be written to or deleted through either spelling.

These are pure string functions: they never touch the filesystem.
"""
from __future__ import annotations

import re

__all__ = [
    "win_to_wsl_path",
    "wsl_to_win_path",
    "same_location",
    "normalize_for_compare",
]

_DRIVE_RE = re.compile(r"^([A-Za-z]):[\\/](.*)$", re.DOTALL)
_WSL_UNC_RE = re.compile(r"^\\\\wsl(?:\.localhost|\$)\\([^\\]+)\\(.*)$")
_ExampleProject_RE = re.compile(r"^/mnt/([A-Za-z])(?:/(.*))?$", re.DOTALL)


def win_to_wsl_path(path: str) -> str:
    """Translate a Windows path to its WSL form.

    ``D:\\Wan2GP\\outputs\\a b.mp4`` -> ``/mnt/d/Wan2GP/outputs/a b.mp4``
    ``\\\\wsl.localhost\\Ubuntu\\home\\bear\\x`` -> ``/home/bear/x`` (same for ``\\\\wsl$\\...``)
    UNC paths that have no WSL equivalent (``\\\\nas\\share\\x``) and paths that
    are already POSIX are returned unchanged.
    """
    if not isinstance(path, str):
        raise TypeError(f"win_to_wsl_path expects str, got {type(path).__name__}")
    match = _WSL_UNC_RE.match(path)
    if match:
        return "/" + match.group(2).replace("\\", "/")
    match = _DRIVE_RE.match(path)
    if match:
        drive = match.group(1).lower()
        rest = match.group(2).replace("\\", "/")
        return f"/mnt/{drive}/{rest}"
    return path


def wsl_to_win_path(path: str) -> str:
    """Translate a WSL ``/mnt/<drive>/...`` path to its Windows form.

    ``/mnt/d/wangp/outputs/x.mp4`` -> ``D:\\wangp\\outputs\\x.mp4``
    Other POSIX paths (``/home/bear/x``) and UNC paths are returned unchanged:
    there is no faithful, side-effect-free mapping from arbitrary Linux paths
    to Windows ones, and guessing would break the read-only guarantee.
    """
    if not isinstance(path, str):
        raise TypeError(f"wsl_to_win_path expects str, got {type(path).__name__}")
    match = _ExampleProject_RE.match(path)
    if match:
        drive = match.group(1).upper()
        rest = (match.group(2) or "").replace("/", "\\")
        return f"{drive}:\\{rest}" if rest else f"{drive}:\\"
    return path


def normalize_for_compare(path: str) -> str:
    """Case-folded, slash-normalized form used only for equality checks."""
    text = str(path).replace("\\", "/")
    while "//" in text[1:]:
        text = text[:1] + text[1:].replace("//", "/")
    return text.rstrip("/").casefold()


def same_location(left: str, right: str) -> bool:
    """True when two paths denote the same location across Windows/WSL spellings.

    ``same_location("D:\\\\Wan2GP", "/mnt/d/wan2gp")`` -> ``True``
    Used by documentation tests and cleanup guards; performs no filesystem I/O.
    """
    a = normalize_for_compare(win_to_wsl_path(str(left)))
    b = normalize_for_compare(win_to_wsl_path(str(right)))
    return a == b
