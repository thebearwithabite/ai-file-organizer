"""
Tiering policy for AI File Organizer V2.

Replaces all emergency-space scripts with a single, testable policy module.
Rules:
  - File unaccessed > N days AND classified stable -> migrate hot -> cold
  - Local free space < threshold -> migrate largest cold-candidates first
  - User requests cold file -> stream via signed URL or full get()

With GCS Autoclass, the organizer only decides local<->cloud.
Storage-class transitions within GCS are Google's problem.
"""
from __future__ import annotations

import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .provider import StorageProvider, StorageRef, LocalProvider, GCSProvider

logger = logging.getLogger(__name__)


@dataclass
class TieringConfig:
    """Configuration for the tiering policy."""
    # Days of inactivity before a file is eligible for cold migration
    stale_days: int = 30
    # Minimum free space (bytes) before tiering kicks in
    min_free_bytes: int = 5 * 1024 * 1024 * 1024  # 5 GB
    # Fraction of local disk that must be free (0.0-1.0)
    min_free_fraction: float = 0.05
    # Whether to enable automatic tiering
    auto_tier: bool = True


@dataclass
class TieringEvent:
    """Record of a tiering action (stored in operations_log)."""
    timestamp: float = field(default_factory=time.time)
    action: str = ""          # "migrate_cold" | "retrieve_hot" | "preview"
    file_key: str = ""
    source_tier: str = ""
    target_tier: str = ""
    size_bytes: int = 0
    reason: str = ""
    storage_ref: Optional[StorageRef] = None


class TieringPolicy:
    """
    Manages local<->cloud tier transitions.

    Usage:
        policy = TieringPolicy(
            local=LocalProvider(root=Path.home() / "Documents/AI-Organized"),
            cloud=GCSProvider(bucket_name="ai-file-organizer-cold"),
        )
        policy.check_and_tier()
    """

    def __init__(
        self,
        local: LocalProvider,
        cloud: GCSProvider,
        config: Optional[TieringConfig] = None,
    ):
        self.local = local
        self.cloud = cloud
        self.config = config or TieringConfig()
        self.events: list[TieringEvent] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_and_tier(self) -> list[TieringEvent]:
        """
        Run a full tiering check:
        1. Age-based: migrate stale files from local -> cloud
        2. Space-pressure: if disk is low, migrate largest files first
        Returns the list of events for logging.
        """
        if not self.config.auto_tier:
            return []

        self.events = []

        # 1. Age-based migration
        self._tier_stale_files()

        # 2. Space-pressure migration
        if self._free_space_low():
            self._tier_by_size()

        return self.events

    def retrieve(self, key: str, dest: Path) -> Path:
        """Retrieve a file from cold tier to local hot tier."""
        ref = StorageRef(tier="gcs", bucket_or_root=self.cloud.bucket_name, key=key)
        result = self.cloud.get(ref, dest)
        self._record(TieringEvent(
            action="retrieve_hot",
            file_key=key,
            source_tier="gcs",
            target_tier="local",
            size_bytes=dest.stat().st_size if dest.exists() else 0,
            reason="user_requested",
        ))
        return result

    def preview_url(self, key: str, ttl_s: int = 3600) -> str:
        """Get a signed URL for previewing a cold-tier file."""
        ref = StorageRef(tier="gcs", bucket_or_root=self.cloud.bucket_name, key=key)
        url = self.cloud.stream_url(ref, ttl_s)
        self._record(TieringEvent(
            action="preview",
            file_key=key,
            source_tier="gcs",
            target_tier="gcs",
            reason="preview_url",
        ))
        return url

    # ------------------------------------------------------------------
    # Internal tiering logic
    # ------------------------------------------------------------------

    def _tier_stale_files(self) -> None:
        """Migrate files not accessed in > stale_days to cold tier."""
        cutoff = time.time() - (self.config.stale_days * 86400)
        candidates = []

        for entry in self.local.root.rglob("*"):
            if not entry.is_file():
                continue
            st = entry.stat()
            if st.st_atime < cutoff:
                candidates.append((st.st_atime, st.st_size, entry))

        candidates.sort()  # oldest first

        for atime, size, path in candidates[:100]:  # cap at 100 per run
            key = path.relative_to(self.local.root).as_posix()
            try:
                ref = self.cloud.put(path, key)
                # Only delete local if upload succeeded
                path.unlink()
                self._record(TieringEvent(
                    action="migrate_cold",
                    file_key=key,
                    source_tier="local",
                    target_tier="gcs",
                    size_bytes=size,
                    reason=f"stale_{self.config.stale_days}d",
                    storage_ref=ref,
                ))
                logger.info(f"Tiered (age): {path.name} -> gs://{self.cloud.bucket_name}/{key}")
            except Exception as e:
                logger.error(f"Tiering failed for {path}: {e}")

    def _tier_by_size(self) -> None:
        """Migrate largest files to cold tier until free space is above threshold."""
        candidates = []
        for entry in self.local.root.rglob("*"):
            if not entry.is_file():
                continue
            st = entry.stat()
            candidates.append((st.st_size, entry))

        candidates.sort(reverse=True)  # largest first

        for size, path in candidates:
            if not self._free_space_low():
                break
            key = path.relative_to(self.local.root).as_posix()
            try:
                ref = self.cloud.put(path, key)
                path.unlink()
                self._record(TieringEvent(
                    action="migrate_cold",
                    file_key=key,
                    source_tier="local",
                    target_tier="gcs",
                    size_bytes=size,
                    reason="space_pressure",
                    storage_ref=ref,
                ))
                logger.info(f"Tiered (space): {path.name} ({size} bytes) -> gs://{self.cloud.bucket_name}/{key}")
            except Exception as e:
                logger.error(f"Tiering failed for {path}: {e}")

    def _free_space_low(self) -> bool:
        """Check if local disk free space is below threshold."""
        try:
            stat = shutil.disk_usage(self.local.root)
            free = stat.free
            fraction = free / stat.total if stat.total > 0 else 0
            return free < self.config.min_free_bytes or fraction < self.config.min_free_fraction
        except Exception:
            return False

    def _record(self, event: TieringEvent) -> None:
        """Record a tiering event (for operations_log)."""
        self.events.append(event)

    # ------------------------------------------------------------------
    # Simulation / testing
    # ------------------------------------------------------------------

    def simulate_pressure(self, fill_to_bytes: int, test_dir: Path) -> list[TieringEvent]:
        """
        Fill a test directory to simulate disk pressure, then run tiering.
        Used for testing (Phase 1.2 success criteria).
        """
        # Create dummy files until we hit the target
        created = 0
        while True:
            usage = sum(f.stat().st_size for f in test_dir.rglob("*") if f.is_file())
            if usage >= fill_to_bytes:
                break
            dummy = test_dir / f"dummy_{created}.bin"
            dummy.write_bytes(b"\0" * min(10 * 1024 * 1024, fill_to_bytes - usage))
            created += 1
            if created > 1000:
                break

        # Swap the local provider's root temporarily
        original_root = self.local.root
        self.local.root = test_dir
        try:
            return self.check_and_tier()
        finally:
            self.local.root = original_root
