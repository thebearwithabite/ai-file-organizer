"""Mutation checks: the retry-ceiling tests must be able to fail.

A passing test proves nothing unless you have seen it fail for the right
reason. This module breaks the review loop on purpose, in a copy of the
source, and asserts that the acceptance test in ``test_pipeline.py`` catches
each break. It restores the original before returning, always.

Each mutation is run in a subprocess against the real repo tree so the
pipeline's own imports resolve exactly as they do in CI. The source file is
restored in a ``finally`` block, so a failing mutation cannot leave the repo in
a mutated state.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LOOP_SOURCE = REPO_ROOT / "backend" / "services" / "review_loop.py"

CEILING_TEST = (
    "tests/test_pipeline.py::TestRetryCeiling"
    "::test_always_failing_reviewer_stops_after_exactly_three_attempts"
)
CONSTANT_TEST = "tests/test_pipeline.py::TestRetryCeiling::test_max_retries_is_two"


def _apply(source: str, replacements: List[Tuple[str, str]]) -> str:
    mutated = source
    for old, new in replacements:
        assert old in mutated, f"mutation anchor not found: {old[:60]!r}"
        mutated = mutated.replace(old, new, 1)
    return mutated


def _run_test(test_id: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", test_id, "-q", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300,
    )


class _MutatedSource:
    """Context manager: patch LOOP_SOURCE, always restore it."""

    def __init__(self, replacements: List[Tuple[str, str]]) -> None:
        self.replacements = replacements
        self.original = LOOP_SOURCE.read_text(encoding="utf-8")

    def __enter__(self) -> str:
        self.mutated = _apply(self.original, self.replacements)
        LOOP_SOURCE.write_text(self.mutated, encoding="utf-8")
        return self.mutated

    def __exit__(self, *exc_info: object) -> None:
        LOOP_SOURCE.write_text(self.original, encoding="utf-8")


def test_source_is_restored_between_runs():
    """Guard for this module itself: the file must be back to normal now."""
    source = LOOP_SOURCE.read_text(encoding="utf-8")
    assert "for attempt_no in range(1, self.max_retries + 2):" in source
    assert "if attempt_no > self.max_retries:" in source


def test_unbounded_loop_is_caught():
    """Remove BOTH retry guards -> the ceiling test must go red.

    ReviewLoop.run carries two independent stops: the ``for`` range and an
    inner ``break``. Removing only the range leaves the loop terminating on
    the inner guard, so both are patched here. That redundancy is deliberate —
    it means a future refactor that drops one guard still respects the ceiling.
    """
    with _MutatedSource([
        ("for attempt_no in range(1, self.max_retries + 2):",
         "for attempt_no in range(1, 1000):"),
        ("            if attempt_no > self.max_retries:\n"
         "                break  # budget spent; fall through to surface",
         "            if False:\n"
         "                break"),
    ]):
        result = _run_test(CEILING_TEST)
    assert result.returncode != 0, (
        "the retry-ceiling test passed against an unbounded loop; it is not "
        f"actually testing the ceiling:\n{result.stdout[-2000:]}"
    )
    assert "999" in (result.stdout or ""), (
        "expected the mutated loop to run away; the mutation may not have "
        f"applied:\n{result.stdout[-2000:]}"
    )


def test_raised_max_retries_is_caught():
    """Raise the constant to 5 -> the constant assertion must go red."""
    with _MutatedSource([("MAX_RETRIES = 2", "MAX_RETRIES = 5")]):
        result = _run_test(CONSTANT_TEST)
    assert result.returncode != 0, (
        "MAX_RETRIES == 2 passed after it was changed to 5"
    )


def test_removed_constructor_ceiling_is_caught():
    """Drop the constructor's max_retries check -> the refusal test must go red."""
    with _MutatedSource([
        ("        if int(max_retries) > MAX_RETRIES:",
         "        if False:"),
    ]):
        result = _run_test(
            "tests/test_pipeline.py::TestRetryCeiling::test_caller_cannot_buy_more_retries"
        )
    assert result.returncode != 0, (
        "a caller could buy 3 retries and the refusal test still passed"
    )


def test_source_is_restored_after_mutations():
    """And the file is still pristine after all of the above has run."""
    source = LOOP_SOURCE.read_text(encoding="utf-8")
    assert "range(1, 1000)" not in source
    assert "MAX_RETRIES = 2" in source
    assert "if attempt_no > self.max_retries:" in source