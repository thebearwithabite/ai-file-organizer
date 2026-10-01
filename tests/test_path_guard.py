"""Tests for ``core.path_guard`` — the deletion guard for Windows/WSL path equality.

Required negative behaviour: deleting either spelling of the WanGP store
(``D:\\Wan2GP`` or ``/mnt/d/wan2gp``) must be refused, in every practical
spelling (case, slashes, trailing slash, ``..`` traversal).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from core.path_guard import (
    DEFAULT_PROTECTED_PATHS,
    ProtectedPathError,
    assert_deletable,
    canonicalize_path,
    is_protected,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

WANGP_WIN = "D:\\Wan2GP"
WANGP_WSL = "/mnt/d/wan2gp"
LAUNCHER_WIN = "C:\\Users\\thebe\\AppData\\Roaming\\wan2gp-desktop"


class TestCanonicalize:
    @pytest.mark.parametrize(
        "variant",
        [
            WANGP_WIN,
            "D:/Wan2GP",
            "d:\\wan2gp",
            "D:\\WAN2GP\\",
            "d:/wan2gp/",
            WANGP_WSL,
            "/MNT/D/WAN2GP",
            "/mnt/d/./wan2gp",
            "/mnt/d/foo/../wan2gp",
            "D:\\foo\\..\\Wan2GP",
        ],
    )
    def test_all_spellings_collapse_to_one_key(self, variant):
        assert canonicalize_path(variant) == "d:/wan2gp"

    def test_child_paths_keep_prefix(self):
        assert canonicalize_path("D:\\Wan2GP\\ckpts\\model.gguf") == "d:/wan2gp/ckpts/model.gguf"
        assert canonicalize_path("/mnt/d/Wan2GP/outputs/clip.mp4") == "d:/wan2gp/outputs/clip.mp4"

    def test_posix_paths_are_lowercased_fail_closed(self):
        # Case-folding is deliberate (Windows ignores case); document it.
        assert canonicalize_path("/home/bear/Projects/ai-file-organizer") == (
            "/home/bear/projects/ai-file-organizer"
        )

    def test_similar_names_do_not_collide(self):
        assert canonicalize_path("D:\\Wan2GP-backups") == "d:/wan2gp-backups"


class TestIsProtected:
    @pytest.mark.parametrize(
        "path",
        [
            WANGP_WIN,  # required: uppercase Windows spelling
            WANGP_WSL,  # required: lowercase WSL spelling
            "d:\\wan2gp",
            "D:/Wan2GP/",
            "D:\\Wan2GP\\ckpts\\model.gguf",
            "/mnt/d/Wan2GP/outputs/clip.mp4",
            "D:\\Wan2GP\\models\\..\\outputs",
            LAUNCHER_WIN,
            "C:\\Users\\thebe\\AppData\\Roaming\\wan2gp-desktop\\Wan2GP\\Wan2GP\\wgp.py",
            "/mnt/c/Users/thebe/AppData/Roaming/wan2gp-desktop",
        ],
    )
    def test_protected(self, path):
        assert is_protected(path) is True

    @pytest.mark.parametrize(
        "path",
        [
            "D:\\Wan2GP-backups",  # prefix must not leak past a path boundary
            "/mnt/d/wan2gp-backups",
            "D:\\Other\\Wan2GP",
            "/home/bear/Projects/ai-file-organizer",
            "/mnt/c/Users/thebe/Desktop/render.mp4",
        ],
    )
    def test_not_protected(self, path):
        assert is_protected(path) is False

    def test_default_list_covers_both_spellings(self):
        keys = {canonicalize_path(p) for p in DEFAULT_PROTECTED_PATHS}
        assert "d:/wan2gp" in keys


class TestAssertDeletable:
    @pytest.mark.parametrize("path", [WANGP_WIN, WANGP_WSL])
    def test_negative_deletion_of_either_spelling_raises(self, path):
        with pytest.raises(ProtectedPathError):
            assert_deletable(path)

    def test_negative_case_and_traversal_variants_also_raise(self):
        for path in (
            "d:\\wan2gp",
            "/mnt/d/WAN2GP/",
            "D:\\Wan2GP\\outputs",
            "/mnt/d/foo/../wan2gp",
        ):
            with pytest.raises(ProtectedPathError):
                assert_deletable(path)

    def test_safe_path_passes_through_unchanged(self):
        safe = "/home/bear/Projects/ai-file-organizer/tmp/render.mp4"
        assert assert_deletable(safe) == safe

    def test_custom_protected_list(self):
        assert_deletable("/data/anything")  # not protected by default
        with pytest.raises(ProtectedPathError):
            assert_deletable("/data/anything", protected=["/data/anything"])

    @pytest.mark.parametrize("path", ["", "   ", None])
    def test_empty_paths_are_rejected(self, path):
        with pytest.raises(ValueError):
            assert_deletable(path)


class TestCli:
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "core.path_guard", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

    def test_cli_refuses_protected(self):
        result = self._run(WANGP_WSL)
        assert result.returncode == 1
        assert "PROTECTED" in result.stderr

    def test_cli_allows_safe(self):
        result = self._run("/home/bear/Projects/ai-file-organizer/tmp/x")
        assert result.returncode == 0
