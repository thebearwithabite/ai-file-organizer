"""Guardrails: the renderer boundary is read-only by construction.

Task acceptance (t_274f6b7c): no code path ever writes to or deletes
``/mnt/d/wan2gp`` / ``D:\\Wan2GP`` (the same directory), and the docs state
that the install is managed by the wan2gp-desktop launcher.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from backend.integrations.paths import same_location

REPO_ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS = REPO_ROOT / "backend" / "integrations"
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "wangp_live_smoke.py"
DOC = REPO_ROOT / "docs" / "wangp-client.md"

#: method names that are write/delete operations and have no legitimate use in
#: the boundary modules (they only read templates and speak HTTP).
_STRICT_WRITE_METHODS = {
    "unlink",
    "rmdir",
    "removedirs",
    "rmtree",
    "makedirs",
    "mkdir",
    "write_text",
    "write_bytes",
    "truncate",
    "touch",
    "rename",
}
_OS_MUTATORS = {"remove", "unlink", "rmdir", "removedirs", "rename", "replace", "makedirs", "system", "popen"}
_SHUTIL_MUTATORS = {"rmtree", "move", "copy", "copy2", "copyfile", "copytree"}
_FORBIDDEN_IMPORTS = {"subprocess"}

INTEGRATION_MODULES = sorted(INTEGRATIONS.glob("*.py"))


def _full_name(node: ast.AST) -> str | None:
    """Dotted name for ``os.remove`` / ``f.write_text`` style call targets."""
    parts: list[str] = []
    current: ast.AST | None = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def _integration_violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "open":
                violations.append(f"{path.name}:{node.lineno} open(...) is not read-only by shape")
                continue
            dotted = _full_name(func)
            if dotted is None:
                continue
            attr = dotted.rsplit(".", 1)[-1]
            root = dotted.split(".", 1)[0] if "." in dotted else None
            if isinstance(func, ast.Attribute) and attr in _STRICT_WRITE_METHODS:
                violations.append(f"{path.name}:{node.lineno} {dotted}()")
                continue
            if root == "os" and attr in _OS_MUTATORS:
                violations.append(f"{path.name}:{node.lineno} {dotted}()")
            elif root == "shutil" and attr in _SHUTIL_MUTATORS:
                violations.append(f"{path.name}:{node.lineno} {dotted}()")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _FORBIDDEN_IMPORTS:
                    violations.append(f"{path.name}:{node.lineno} imports {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in _FORBIDDEN_IMPORTS:
                violations.append(f"{path.name}:{node.lineno} imports from {node.module}")
    return violations


@pytest.mark.parametrize("module", INTEGRATION_MODULES, ids=lambda p: p.name)
def test_integration_module_is_read_only(module):
    """No module in backend/integrations/ may write, delete, or shell out."""
    assert _integration_violations(module) == []


def test_integration_modules_are_present():
    names = {module.name for module in INTEGRATION_MODULES}
    assert {"__init__.py", "paths.py", "wangp_client.py", "wangp_config.py", "wangp_settings.py"} <= names


_WRITE_ATTRS = {
    "write_text",
    "write_bytes",
    "mkdir",
    "makedirs",
    "unlink",
    "rmdir",
    "rmtree",
    "rename",
    "touch",
    "open",
}


def _smoke_write_calls(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _WRITE_ATTRS:
            found.append(ast.unparse(node))
        elif isinstance(func, ast.Name) and func.id == "open":
            found.append(ast.unparse(node))
    return found


def test_smoke_script_writes_only_to_its_capture_dir():
    """The live smoke script may write JSON captures, but only under --capture-dir."""
    calls = _smoke_write_calls(SMOKE_SCRIPT)
    assert calls, "expected the smoke script to write its capture files somewhere"
    for expression in calls:
        assert "capture_dir" in expression, f"write outside capture_dir: {expression}"


def test_smoke_script_does_not_shell_out():
    tree = ast.parse(SMOKE_SCRIPT.read_text(encoding="utf-8"), filename=str(SMOKE_SCRIPT))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not ({"subprocess", "os", "shutil"} & imported)


def test_renderer_dirs_are_one_location():
    """D:\\Wan2GP and /mnt/d/wan2gp must be treated as the same directory."""
    assert same_location("D:\\Wan2GP", "/mnt/d/wan2gp")
    assert same_location("D:\\Wan2GP\\outputs", "/mnt/d/wan2gp/OUTPUTS")


def test_docs_cover_launch_networking_and_launcher_ownership():
    text = DOC.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "--mcp-transport streamable-http" in text
    assert "--mcp-host" in text and "--mcp-port" in text
    assert "same directory" in text
    assert "launcher" in lowered
    assert "wan2gp-desktop" in lowered
    assert "firewall" in lowered or "netsh" in lowered
    assert "/mnt/d/wan2gp" in lowered
