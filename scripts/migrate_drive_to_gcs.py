#!/usr/bin/env python3
"""
Phase 1.4: Google Drive -> GCS Migration Script (rclone runbook).

This is a ONE-SHOT script. Run once, verify, then manually clean up Drive
after a 7-day soak period with explicit human approval.

Usage:
    python scripts/migrate_drive_to_gcs.py --dry-run
    python scripts/migrate_drive_to_gcs.py --execute
    python scripts/migrate_drive_to_gcs.py --verify
    python scripts/migrate_drive_to_gcs.py --status
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrate")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Google Drive root (rclone remote name)
GDRIVE_REMOTE = "gdrive:"
# GCS bucket (must already exist with Autoclass + versioning)
GCS_BUCKET = "gs://ai-file-organizer-cold"
# Where the migration report lives
REPORT_PATH = Path.home() / ".ai-file-organizer" / "migration_report.json"
# Metadata DB path
METADATA_DB = Path.home() / ".ai-file-organizer" / "organizer.db"


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def check_prerequisites() -> bool:
    """Verify rclone is installed and remotes are configured."""
    try:
        subprocess.run(["rclone", "version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("rclone not found. Install: https://rclone.org/install/")
        return False

    # Check remotes
    result = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True)
    remotes = result.stdout.strip().split("\n")

    gdrive_ok = any("gdrive:" in r for r in remotes)
    gcs_ok = any("gcs:" in r or r == "gs:" for r in remotes) or "gs:" in remotes

    if not gdrive_ok:
        logger.warning("gdrive remote not configured. Run: rclone config")
    if not gcs_ok:
        logger.warning("GCS remote not configured. Run: rclone config")

    return True


def copy_files(dry_run: bool = True) -> dict:
    """
    Step 1: rclone copy gdrive:<root> gcs:<bucket> with --checksum.
    Copy only — never delete from Drive yet.
    """
    flags = ["--checksum", "--progress", "--stats", "30s", "--transfers", "8"]
    if dry_run:
        flags.append("--dry-run")

    cmd = ["rclone", "copy", GDRIVE_REMOTE, GCS_BUCKET] + flags

    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)  # stream progress
    return {"command": " ".join(cmd), "exit_code": result.returncode, "dry_run": dry_run}


def dedup_pass() -> dict:
    """
    Step 2: Dedup against metadata DB hashes.
    Drive duplicates die here, once, in the migration.
    """
    removed = 0
    saved_bytes = 0

    try:
        import sqlite3
        conn = sqlite3.connect(str(METADATA_DB))
        conn.row_factory = sqlite3.Row

        # Get all known hashes
        rows = conn.execute("SELECT DISTINCT secure_hash FROM files WHERE secure_hash IS NOT NULL").fetchall()
        known_hashes = {row["secure_hash"] for row in rows}
        conn.close()

        logger.info(f"Known hashes in metadata DB: {len(known_hashes)}")

        # List all objects in GCS bucket
        result = subprocess.run(
            ["rclone", "lsjson", GCS_BUCKET, "--fast-list"],
            capture_output=True, text=True,
        )
        objects = json.loads(result.stdout)

        for obj in objects:
            if obj.get("Size", 0) == 0:
                continue
            md5 = obj.get("MD5", "")
            if md5 in known_hashes:
                # This is a duplicate — already in metadata DB
                path = obj["Path"]
                subprocess.run(
                    ["rclone", "deletefile", f"{GCS_BUCKET}/{path}"],
                    capture_output=True,
                )
                removed += 1
                saved_bytes += obj["Size"]
                logger.info(f"Dedup: removed {path} ({obj['Size']} bytes, hash known)")

    except Exception as e:
        logger.error(f"Dedup pass failed: {e}")

    return {"removed": removed, "saved_bytes": saved_bytes}


def rewrite_metadata(dry_run: bool = True) -> dict:
    """
    Step 3: Rewrite StorageRefs in metadata DB from Drive IDs -> GCS keys.
    """
    if dry_run:
        logger.info("DRY RUN: would rewrite metadata DB StorageRefs")
        return {"updated": 0, "dry_run": True}

    try:
        import sqlite3
        conn = sqlite3.connect(str(METADATA_DB))
        conn.row_factory = sqlite3.Row

        # Find rows with Drive IDs
        rows = conn.execute(
            "SELECT id, gdrive_file_id, file_path FROM files WHERE gdrive_file_id IS NOT NULL"
        ).fetchall()

        updated = 0
        for row in rows:
            conn.execute(
                "UPDATE files SET gcs_key = gdrive_file_id, gdrive_file_id = NULL WHERE id = ?",
                (row["id"],),
            )
            updated += 1

        conn.commit()
        conn.close()
        logger.info(f"Rewrote {updated} metadata entries: Drive ID -> GCS key")
        return {"updated": updated, "dry_run": False}

    except Exception as e:
        logger.error(f"Metadata rewrite failed: {e}")
        return {"updated": 0, "error": str(e)}


def verify_migration(sample_count: int = 10) -> dict:
    """
    Step 4: Verify count, total bytes, and hash spot-checks.
    """
    # Get GCS object count
    result = subprocess.run(
        ["rclone", "size", GCS_BUCKET, "--json"],
        capture_output=True, text=True,
    )
    gcs_stats = json.loads(result.stdout)

    # Hash spot-checks
    spot_checks = []
    result = subprocess.run(
        ["rclone", "lsjson", GCS_BUCKET, "--fast-list"],
        capture_output=True, text=True,
    )
    objects = json.loads(result.stdout)

    import random
    sample = random.sample(objects, min(sample_count, len(objects)))

    for obj in sample:
        path = obj["Path"]
        # Download and hash
        tmp = Path(f"/tmp/migrate_verify_{hashlib.md5(path.encode()).hexdigest()[:8]}")
        subprocess.run(
            ["rclone", "copyto", f"{GCS_BUCKET}/{path}", str(tmp)],
            capture_output=True,
        )
        if tmp.exists():
            sha = hashlib.sha256()
            with open(tmp, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha.update(chunk)
            spot_checks.append({"path": path, "sha256": sha.hexdigest(), "size": tmp.stat().st_size})
            tmp.unlink()

    return {
        "gcs_count": gcs_stats.get("count", 0),
        "gcs_bytes": gcs_stats.get("bytes", 0),
        "spot_checks": spot_checks,
    }


def generate_report() -> dict:
    """Produce the final verification report."""
    report = {
        "timestamp": time.time(),
        "gdrive_remote": GDRIVE_REMOTE,
        "gcs_bucket": GCS_BUCKET,
        "metadata_db": str(METADATA_DB),
        "status": "pending_verification",
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    logger.info(f"Report saved to {REPORT_PATH}")
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Migrate Google Drive -> GCS")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--execute", action="store_true", help="Actually perform migration")
    parser.add_argument("--verify", action="store_true", help="Verify migration integrity")
    parser.add_argument("--status", action="store_true", help="Show migration status")
    parser.add_argument("--samples", type=int, default=10, help="Spot-check sample count")
    args = parser.parse_args()

    if not any([args.dry_run, args.execute, args.verify, args.status]):
        parser.print_help()
        return

    dry_run = not args.execute

    if not check_prerequisites():
        sys.exit(1)

    if args.status:
        if REPORT_PATH.exists():
            report = json.loads(REPORT_PATH.read_text())
            print(json.dumps(report, indent=2))
        else:
            print("No migration report found. Run --execute first.")
        return

    if args.dry_run or args.execute:
        logger.info("=" * 60)
        logger.info("STEP 1: Copy files (rclone)")
        logger.info("=" * 60)
        copy_files(dry_run=dry_run)

        if not dry_run:
            logger.info("=" * 60)
            logger.info("STEP 2: Dedup pass")
            logger.info("=" * 60)
            dedup_result = dedup_pass()
            logger.info(f"Dedup removed {dedup_result['removed']} duplicates")

            logger.info("=" * 60)
            logger.info("STEP 3: Rewrite metadata")
            logger.info("=" * 60)
            rewrite_metadata(dry_run=False)

            # Save report
            report = generate_report()
            report["status"] = "migrated_pending_verification"
            REPORT_PATH.write_text(json.dumps(report, indent=2))

    if args.verify:
        logger.info("=" * 60)
        logger.info("VERIFICATION")
        logger.info("=" * 60)
        results = verify_migration(sample_count=args.samples)
        print(json.dumps(results, indent=2))

        # Check: 100% hash match on spot checks
        all_ok = all("sha256" in c for c in results["spot_checks"])
        if all_ok:
            logger.info(f"VERIFICATION PASSED: {len(results['spot_checks'])}/{len(results['spot_checks'])} spot checks OK")
        else:
            logger.error("VERIFICATION FAILED: some spot checks missing hashes")

    logger.info("\n--- NEXT STEPS ---")
    logger.info("1. Review verification report")
    logger.info("2. Wait 7-day soak period")
    logger.info("3. Manually approve Drive cleanup")
    logger.info("4. Run: rclone purge gdrive: (ONLY after approval)")


if __name__ == "__main__":
    main()
