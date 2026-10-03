"""Unit tests for Windows <-> WSL path translation (renderer boundary)."""
from __future__ import annotations

import pytest

from backend.integrations.paths import (
    normalize_for_compare,
    same_location,
    win_to_wsl_path,
    wsl_to_win_path,
)


class TestWinToWsl:
    def test_drive_path(self):
        assert win_to_wsl_path("D:\\Wan2GP\\outputs\\clip.mp4") == "/mnt/d/Wan2GP/outputs/clip.mp4"

    @pytest.mark.parametrize(
        ("windows", "expected"),
        [
            ("C:\\Users\\thebe\\x y.mp4", "/mnt/c/Users/thebe/x y.mp4"),
            ("c:\\lower\\Case", "/mnt/c/lower/Case"),
            ("E:\\", "/mnt/e/"),
            ("D:\\Wan2GP\\outputs\\a b\\c d.mp4", "/mnt/d/Wan2GP/outputs/a b/c d.mp4"),
        ],
    )
    def test_variants(self, windows, expected):
        assert win_to_wsl_path(windows) == expected

    def test_unc_wsl_localhost(self):
        assert (
            win_to_wsl_path("\\\\wsl.localhost\\Ubuntu\\home\\bear\\Projects")
            == "/home/bear/Projects"
        )

    def test_unc_wsl_dollar(self):
        assert win_to_wsl_path("\\\\wsl$\\Ubuntu\\home\\bear\\x") == "/home/bear/x"

    def test_other_unc_unchanged(self):
        assert win_to_wsl_path("\\\\nas\\share\\x") == "\\\\nas\\share\\x"

    def test_posix_unchanged(self):
        assert win_to_wsl_path("/home/bear/x") == "/home/bear/x"
        assert win_to_wsl_path("/mnt/d/wan2gp") == "/mnt/d/wan2gp"

    def test_non_str_rejected(self):
        with pytest.raises(TypeError):
            win_to_wsl_path(123)  # type: ignore[arg-type]


class TestWslToWin:
    def test_mnt_drive(self):
        assert wsl_to_win_path("/mnt/d/wangp/outputs/x.mp4") == "D:\\wangp\\outputs\\x.mp4"

    def test_mnt_c(self):
        assert wsl_to_win_path("/mnt/c/Users/thebe") == "C:\\Users\\thebe"

    def test_mnt_root(self):
        assert wsl_to_win_path("/mnt/d") == "D:\\"
        assert wsl_to_win_path("/mnt/d/") == "D:\\"

    def test_non_mnt_unchanged(self):
        assert wsl_to_win_path("/home/bear/x") == "/home/bear/x"
        assert wsl_to_win_path("\\\\nas\\share") == "\\\\nas\\share"

    def test_non_str_rejected(self):
        with pytest.raises(TypeError):
            wsl_to_win_path(None)  # type: ignore[arg-type]


class TestSameLocation:
    def test_renderer_dirs_are_the_same_directory(self):
        assert same_location("D:\\Wan2GP", "/mnt/d/wan2gp")
        assert same_location("/mnt/d/wan2gp", "D:\\Wan2GP")
        assert same_location("D:\\Wan2GP\\outputs\\a.mp4", "/mnt/d/wan2gp/outputs/a.mp4")

    def test_case_insensitive(self):
        assert same_location("D:\\Wan2GP", "d:\\wan2gp")
        assert same_location("/mnt/d/Wan2GP", "/mnt/d/wan2gp")

    def test_trailing_slash_ignored(self):
        assert same_location("/mnt/d/wan2gp/", "/mnt/d/wan2gp")
        assert same_location("D:\\Wan2GP\\", "D:\\Wan2GP")

    def test_different_locations(self):
        assert not same_location("D:\\Wan2GP", "/mnt/d/other")
        assert not same_location("/mnt/d/wan2gp", "/mnt/c/wan2gp")
        assert not same_location("D:\\Wan2GP", "D:\\Wan2GP2")

    def test_normalize_for_compare(self):
        assert normalize_for_compare("D:\\A\\B\\") == "d:/a/b"
        assert normalize_for_compare("/mnt/d/A/B/") == "/mnt/d/a/b"
        assert normalize_for_compare(win_to_wsl_path("D:\\A\\B")) == normalize_for_compare(
            "/mnt/d/a/b"
        )
