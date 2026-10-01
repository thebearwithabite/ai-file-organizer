"""Deletion guard for cleanup scripts — Windows/WSL path equality.

Contract
--------
Every script in this repo that removes a file or directory MUST call
:func:`assert_deletable` on the target path BEFORE handing it to
``rm``/``shutil.rmtree``/``unlink`` etc.  :func:`is_protected` is the
non-raising predicate for callers that want to filter lists.

Why
---
The WanGP renderer runs on native Windows while the orchestrator runs in
WSL2.  ``D:\\Wan2GP`` and ``/mnt/d/wan2gp`` are the **same directory** —
Windows filesystems are case-insensitive — so a cleanup script that thinks
in lower-case WSL spelling can silently destroy the model/output stores of
the working install (see ``docs/host-topology.md``).

Comparison happens on a canonical key (see :func:`canonicalize_path`) that
is case-folded, slash-agnostic and drive-letter-aware, so the Windows and
WSL spellings of one directory compare equal::

    D:\\Wan2GP  ==  /mnt/d/wan2gp  ==  d:/wan2gp/  ==  D:\\WAN2GP

Shell callers can use the module CLI instead of importing::

    python -m core.path_guard "$path" && rm -rf -- "$path"

It exits non-zero for protected paths.

Deliberate limitation: case-folding may treat two genuinely distinct
case-sensitive Linux paths as equal.  For a deletion guard that is the
*fail-closed* direction — it can never turn a "no" into a "yes" — and it is
the whole point (Windows ignores case).  UNC paths are not translated;
pass native or ``/mnt`` spellings.

Pure string logic: no filesystem access, safe to call on paths that do not
exist, cheap to unit-test.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional, Union

__all__ = [
    "ProtectedPathError",
    "DEFAULT_PROTECTED_PATHS",
    "canonicalize_path",
    "is_protected",
    "assert_deletable",
]


class ProtectedPathError(RuntimeError):
    """Raised when a cleanup operation targets a protected path."""


#: Paths that repo scripts must never delete, in any spelling.
#:
#: ``D:\\Wan2GP`` and ``/mnt/d/wan2gp`` are one directory (the model and
#: output stores of the launcher-managed WanGP install, plus the retired
#: Sparge fork); both spellings are listed for documentation value.  The
#: last entry is the launcher-managed live install.  See
#: ``docs/host-topology.md``.
DEFAULT_PROTECTED_PATHS: tuple[str, ...] = (
    r"D:\Wan2GP",  # == /mnt/d/wan2gp — model/output stores + retired fork
    "/mnt/d/wan2gp",  # same directory, WSL spelling
    r"C:\Users\thebe\AppData\Roaming\wan2gp-desktop",  # launcher-managed install
)

_DRIVE_PREFIX_RE = re.compile(r"^([a-z]):")
_ExampleProject_DRIVE_RE = re.compile(r"^/mnt/([a-z])(?:/(.*))?$")


def _collapse(parts: Iterable[str], absolute: bool) -> list[str]:
    """Lexically resolve ``.``/``..`` segments.

    ``..`` clamps at the root for absolute paths (POSIX ``/.. == /`` and
    Windows ``D:\\.. == D:\\``); for relative paths it accumulates.
    """
    out: list[str] = []
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            if out and out[-1] != "..":
                out.pop()
            elif not absolute:
                out.append("..")
            # absolute: ".." at the root is a no-op
        else:
            out.append(part)
    return out


def canonicalize_path(path: Union[str, "os.PathLike[str]"]) -> str:
    """Return the canonical comparison key for *path* (no filesystem access).

    - backslashes become slashes; the whole string is case-folded
    - ``/mnt/<letter>/...`` becomes ``<letter>:/...``  (``/mnt/d/x`` == ``D:/x``)
    - ``.``/``..`` are collapsed lexically, duplicate slashes collapsed,
      trailing slash dropped
    """
    raw = str(path).strip().replace("\\", "/").lower()

    drive = ""
    match = _DRIVE_PREFIX_RE.match(raw)
    if match:
        drive = match.group(1)
        raw = raw[2:]

    absolute = bool(drive) or raw.startswith("/")
    joined = "/".join(_collapse(raw.split("/"), absolute=absolute))

    if drive:
        canonical = drive + ":/" + joined
    elif raw.startswith("/"):
        canonical = "/" + joined
    else:
        canonical = joined or "."

    mount = _ExampleProject_DRIVE_RE.match(canonical)
    if mount:
        canonical = mount.group(1) + ":/" + (mount.group(2) or "")
    return canonical


def is_protected(
    path: Union[str, "os.PathLike[str]"],
    protected: Optional[Iterable[str]] = None,
) -> bool:
    """True if *path* is (or lives under) a protected root."""
    key = canonicalize_path(path)
    roots = DEFAULT_PROTECTED_PATHS if protected is None else protected
    for root in roots:
        root_key = canonicalize_path(root).rstrip("/") or "/"
        if key == root_key or key.startswith(root_key + "/"):
            return True
    return False


def assert_deletable(
    path: Union[str, "os.PathLike[str]"],
    protected: Optional[Iterable[str]] = None,
) -> str:
    """Guard a deletion: raise unless *path* is safe to remove.

    Returns the original path (as ``str``) so callers can chain::

        remove(assert_deletable(path))

    Raises :class:`ProtectedPathError` for protected roots, ``ValueError``
    for an empty path.
    """
    if path is None or not str(path).strip():
        raise ValueError("refusing to delete an empty path")
    key = canonicalize_path(path)
    if is_protected(path, protected):
        raise ProtectedPathError(
            f"Refusing to delete protected path: {str(path)!r} "
            f"(canonical: {key!r}). "
            r"D:\Wan2GP" " and /mnt/d/wan2gp are the SAME directory "
            "(Windows is case-insensitive) and hold the WanGP model/output "
            "stores; the live install is managed by the wan2gp-desktop "
            "launcher. See docs/host-topology.md."
        )
    return str(path)


def _main(argv: Optional[list[str]] = None) -> int:
    import sys

    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m core.path_guard <path>", file=sys.stderr)
        return 2
    try:
        assert_deletable(args[0])
    except (ProtectedPathError, ValueError) as exc:
        print(f"PROTECTED: {exc}", file=sys.stderr)
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
