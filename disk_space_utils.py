"""
Accurate disk space reporting for macOS APFS volumes.

shutil.disk_usage() and os.statvfs() report raw APFS partition stats
that don't account for purgeable space (caches, snapshots, etc).
This causes false emergencies: Python sees 0.5GB free while macOS
Finder correctly shows 56GB available.

This module uses `diskutil info -plist /` on macOS to get the real
"available" space that matches what Finder reports. Falls back to
shutil.disk_usage() on non-macOS systems.

Created: 2026-02-23
Reason: Emergency disk space system was overriding all files to
ALWAYS confidence mode due to APFS false positives.
"""

import platform
import shutil
import subprocess
import plistlib
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def get_real_disk_space(path: str = "/") -> Tuple[float, float, float]:
    """
    Get accurate disk space on macOS APFS.
    
    Returns:
        (total_gb, free_gb, usage_percent)
        
    On macOS: uses diskutil to get real available space including purgeable.
    On other OS: falls back to shutil.disk_usage().
    """
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["diskutil", "info", "-plist", "/"],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                info = plistlib.loads(result.stdout)
                
                # APFSContainerFree includes purgeable space
                # This matches what Finder reports as "available"
                total = info.get("TotalSize", 0)
                free = info.get("APFSContainerFree", 0) or info.get("FreeSpace", 0)
                
                if total > 0:
                    total_gb = total / (1024 ** 3)
                    free_gb = free / (1024 ** 3)
                    usage_percent = ((total - free) / total) * 100
                    
                    logger.debug(
                        f"APFS real space: {total_gb:.1f}GB total, "
                        f"{free_gb:.1f}GB free, {usage_percent:.1f}% used"
                    )
                    return total_gb, free_gb, usage_percent
                    
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.warning(f"diskutil failed, falling back to shutil: {e}")
    
    # Fallback for non-macOS or if diskutil fails
    total, used, free = shutil.disk_usage(path)
    total_gb = total / (1024 ** 3)
    free_gb = free / (1024 ** 3)
    usage_percent = (used / total) * 100
    return total_gb, free_gb, usage_percent


def get_real_disk_usage(path: str = "/") -> float:
    """
    Get disk usage as a ratio (0.0 to 1.0) using real available space.
    
    This is what confidence_system.py needs for its threshold check.
    """
    total_gb, free_gb, usage_percent = get_real_disk_space(path)
    return usage_percent / 100.0
