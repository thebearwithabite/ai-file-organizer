#!/usr/bin/env python3
"""
AI File Organizer – Sanity Check Script (Max Version)

This script independently verifies:
  - Google Drive integration + organizer root
  - Backend API health + key endpoints
  - Adaptive learning DB + VEO prompts DB
  - Classification pipeline (confidence + category normalization)
  - Actual file movement from ~/Downloads → Google Drive root

It prints raw, unpolished results so you can see exactly what’s working
and what’s bullshit.

Run from repo root with the venv active:

  cd ~/Github/ai-file-organizer
  source venv/bin/activate
  python sanity_check.py
"""

import os
import sys
import json
import time
import sqlite3
import traceback
from pathlib import Path
from typing import Optional

# --- Try to import requests -------------------------------------------------

try:
    import requests
except ImportError:
    print("❌ ERROR: `requests` is not installed in this venv.")
    print("   Try: pip install requests")
    sys.exit(1)

# --- Local imports ----------------------------------------------------------

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import gdrive_integration
    from gdrive_integration import get_ai_organizer_root, GoogleDriveIntegration
except Exception as e:
    print("❌ ERROR: Could not import gdrive_integration / get_ai_organizer_root")
    traceback.print_exc()
    sys.exit(1)

# Some modules are optional – we won’t die if they’re missing
try:
    from universal_adaptive_learning import UniversalAdaptiveLearning  # type: ignore
except Exception:
    UniversalAdaptiveLearning = None


API_BASE = "http://localhost:8000"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def header(title: str):
    print("\n" + "=" * 80)
    print(f"🔍 {title}")
    print("=" * 80)


def sub(msg: str):
    print(f"  • {msg}")


def ok(msg: str):
    print(f"    ✅ {msg}")


def warn(msg: str):
    print(f"    ⚠️  {msg}")


def bad(msg: str):
    print(f"    ❌ {msg}")


def call_api(path: str, method: str = "GET", json_body: Optional[dict] = None, timeout: float = 5.0):
    url = f"{API_BASE}{path}"
    try:
        if method.upper() == "GET":
            r = requests.get(url, timeout=timeout)
        else:
            r = requests.post(url, json=json_body, timeout=timeout)
        return r
    except Exception as e:
        bad(f"Request to {url} failed: {e}")
        return None


# ---------------------------------------------------------------------------
# 1. Check Google Drive + Organizer Root
# ---------------------------------------------------------------------------

def check_gdrive_root():
    header("STEP 1 – Google Drive & Organizer Root")

    env_email = os.getenv("AI_ORGANIZER_GDRIVE_EMAIL", "(not set)")
    env_root = os.getenv("AI_ORGANIZER_GDRIVE_ROOT", "(not set)")

    sub("Environment variables:")
    print(f"    AI_ORGANIZER_GDRIVE_EMAIL = {env_email}")
    print(f"    AI_ORGANIZER_GDRIVE_ROOT  = {env_root}")

    try:
        gd = GoogleDriveIntegration()
        status = gd.get_status()
        root = gd.get_ai_organizer_root()
        direct_root = get_ai_organizer_root()

        sub("Detected Google Drive status:")
        ok(f"Mounted: {status.is_mounted}")
        ok(f"Online: {status.is_online}")
        ok(f"drive_root: {status.drive_path}")
        ok(f"emergency_staging: {status.emergency_staging_path}")
        ok(f"get_ai_organizer_root(): {direct_root}")

        if env_root != "(not set)":
            if Path(env_root).resolve() == direct_root.resolve():
                ok("AI_ORGANIZER_GDRIVE_ROOT matches get_ai_organizer_root()")
            else:
                warn("AI_ORGANIZER_GDRIVE_ROOT does NOT match get_ai_organizer_root()")

        if not status.is_mounted or not status.drive_path:
            warn("Google Drive not mounted – system will be in fallback mode.")
        else:
            if not str(status.drive_path).endswith("My Drive"):
                warn("drive_path does not end with 'My Drive' – double check the mount path.")

    except Exception as e:
        bad("Failed to check Google Drive integration:")
        traceback.print_exc()


# ---------------------------------------------------------------------------
# 2. Check Backend Endpoints
# ---------------------------------------------------------------------------

def check_backend_endpoints():
    header("STEP 2 – Backend API Health & Core Endpoints")

    # /health
    sub("Checking /health …")
    r = call_api("/health")
    if r is None:
        return
    try:
        data = r.json()
        ok(f"/health status: {data}")
    except Exception:
        bad("Invalid JSON from /health")
        print(r.text)

    # /api/system/status
    sub("Checking /api/system/status …")
    r = call_api("/api/system/status")
    if r is None:
        return
    try:
        data = r.json()
        print("    Raw system status JSON:")
        print(json.dumps(data, indent=2))
        disk = data.get("disk_space", {})
        ok(f"Disk space: free_gb={disk.get('free_gb')} total_gb={disk.get('total_gb')} status={disk.get('status')}")
    except Exception:
        bad("Invalid JSON from /api/system/status")
        print(r.text)

    # /api/system/space-protection
    sub("Checking /api/system/space-protection …")
    r = call_api("/api/system/space-protection")
    if r is None:
        return
    try:
        data = r.json()
        print("    Raw space-protection JSON:")
        print(json.dumps(data, indent=2))
        ok("space-protection endpoint responded successfully")
    except Exception:
        bad("Invalid JSON from /api/system/space-protection")
        print(r.text)

    # /api/system/monitor-status
    sub("Checking /api/system/monitor-status …")
    r = call_api("/api/system/monitor-status")
    if r is None:
        return
    try:
        data = r.json()
        print("    Raw monitor-status JSON:")
        print(json.dumps(data, indent=2))
        ok("monitor-status endpoint responded successfully")
    except Exception:
        bad("Invalid JSON from /api/system/monitor-status")
        print(r.text)

    # /api/settings/database-stats
    sub("Checking /api/settings/database-stats …")
    r = call_api("/api/settings/database-stats")
    if r is None:
        return
    try:
        data = r.json()
        print("    Raw database-stats JSON:")
        print(json.dumps(data, indent=2))
        ok("database-stats endpoint responded successfully")
    except Exception:
        bad("Invalid JSON from /api/settings/database-stats")
        print(r.text)


# ---------------------------------------------------------------------------
# 3. Check SQLite Databases (adaptive_learning + VEO prompts)
# ---------------------------------------------------------------------------

def check_databases():
    header("STEP 3 – SQLite Databases")

    home = Path.home()
    learning_db_path = home / ".ai_file_organizer" / "databases" / "adaptive_learning.db"
    metadata_db_path = home / ".ai_file_organizer" / "databases" / "metadata_tracking.db"

    # Adaptive learning DB
    sub(f"Checking adaptive learning DB: {learning_db_path}")
    if not learning_db_path.exists():
        warn("adaptive_learning.db does not exist – maybe learning hasn’t started yet?")
    else:
        try:
            conn = sqlite3.connect(str(learning_db_path))
            cur = conn.cursor()

            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cur.fetchall()]
            ok(f"Tables: {tables}")

            if "learning_events" in tables:
                cur.execute("SELECT COUNT(*) FROM learning_events;")
                count = cur.fetchone()[0]
                ok(f"learning_events rows: {count}")
            else:
                warn("No learning_events table found in adaptive_learning.db")

            conn.close()
        except Exception:
            bad("Error reading adaptive_learning.db:")
            traceback.print_exc()

    # Metadata / VEO prompts DB
    sub(f"Checking metadata / VEO prompts DB: {metadata_db_path}")
    if not metadata_db_path.exists():
        warn("metadata_tracking.db does not exist – VEO prompt integration may not be initialized.")
    else:
        try:
            conn = sqlite3.connect(str(metadata_db_path))
            cur = conn.cursor()

            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cur.fetchall()]
            ok(f"Tables: {tables}")

            if "veo_prompts" in tables:
                cur.execute("SELECT COUNT(*) FROM veo_prompts;")
                count = cur.fetchone()[0]
                ok(f"veo_prompts rows: {count}")
                cur.execute("SELECT file_path, shot_id, confidence_score FROM veo_prompts ORDER BY created_at DESC LIMIT 3;")
                rows = cur.fetchall()
                print("    Last 3 veo_prompts rows:")
                for row in rows:
                    print(f"      - file_path={row[0]} | shot_id={row[1]} | confidence={row[2]}")
            else:
                warn("No veo_prompts table found in metadata_tracking.db")

            conn.close()
        except Exception:
            bad("Error reading metadata_tracking.db:")
            traceback.print_exc()


# ---------------------------------------------------------------------------
# 4. End-to-End Classification & File Movement Test
# ---------------------------------------------------------------------------

def check_classification_and_movement():
    header("STEP 4 – Classification Pipeline & File Movement")

    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        bad(f"Downloads folder does not exist: {downloads}")
        return

    # Create a unique test file
    ts = int(time.time())
    test_filename = f"sanity_test_max_{ts}.txt"
    test_path = downloads / test_filename

    sub(f"Creating test file in Downloads: {test_path}")
    try:
        test_path.write_text("This is a sanity test file created by Max.\n", encoding="utf-8")
        ok("Test file created.")
    except Exception:
        bad("Failed to create test file in Downloads.")
        traceback.print_exc()
        return

    # Call /api/triage/classify
    sub("Calling /api/triage/classify on the test file …")
    payload = {
        "file_path": str(test_path),
        "confirmed_category": "research",  # should be a valid, boring category
        "project": None,
        "episode": None,
    }

    r = call_api("/api/triage/classify", method="POST", json_body=payload, timeout=30.0)
    if r is None:
        bad("Call to /api/triage/classify failed.")
        return

    print("    Raw /api/triage/classify response status:", r.status_code)
    try:
        data = r.json()
        print("    Raw JSON response:")
        print(json.dumps(data, indent=2))
    except Exception:
        bad("Invalid JSON from /api/triage/classify")
        print(r.text)
        return

    # Try to locate classification block & confidence
    sub("Checking classification confidence & category normalization …")
    classification = data.get("classification") or data.get("result") or data

    # Check confidence
    conf = None
    if isinstance(classification, dict):
        if "confidence" in classification:
            conf = classification["confidence"]
        elif "confidence_score" in classification:
            conf = classification["confidence_score"]

    if isinstance(conf, (int, float)):
        ok(f"Classification confidence present and numeric: {conf}")
    else:
        bad("Classification confidence is missing or not numeric.")

    # Check category string
    category = None
    if isinstance(classification, dict):
        category = classification.get("category") or classification.get("predicted_category")

    if isinstance(category, str):
        print(f"    Reported category: {category}")
        if "+" in category:
            bad("Category still contains '+', normalization FAILED.")
        else:
            ok("Category has no '+', normalization appears to be working.")
    else:
        warn("Could not find a clear category field in classification response.")

    # Check that file moved out of Downloads into organizer root
    sub("Verifying that the file moved into Google Drive organizer root …")
    moved_paths = []

    # Try common keys for destination path
    for key in ("target_path", "final_path", "destination_path", "organized_path"):
        if key in data:
            moved_paths.append((key, data[key]))

    # Some implementations might return an 'operations' or 'actions' list
    if "operations" in data and isinstance(data["operations"], list):
        for op in data["operations"]:
            if isinstance(op, dict):
                dest = op.get("target_path") or op.get("destination_path")
                if dest:
                    moved_paths.append(("operation", dest))

    if not moved_paths:
        warn("No obvious destination path found in API response. Check response above.")
    else:
        root = get_ai_organizer_root().resolve()
        print(f"    Organizer root (from get_ai_organizer_root): {root}")
        for label, p in moved_paths:
            p_obj = Path(p).resolve()
            print(f"    {label}: {p_obj}")
            if str(p_obj).startswith(str(root)):
                ok(f"File appears to have been moved into organizer root under: {p_obj}")
            else:
                warn(f"Destination path is NOT under organizer root. ({p_obj})")

    # Check that the original file is gone from Downloads
    if not test_path.exists():
        ok("Original test file no longer in Downloads (moved or deleted).")
    else:
        warn("Test file still in Downloads – move may have failed.")

    # Optional cleanup: we won’t delete anything in Google Drive, but we can remove
    # leftover file in Downloads if it’s still there.
    if test_path.exists():
        try:
            test_path.unlink()
            ok("Cleaned up leftover test file in Downloads.")
        except Exception:
            warn("Could not delete leftover test file in Downloads.")


# ---------------------------------------------------------------------------
# 5. Files for Review – Confidence sanity check
# ---------------------------------------------------------------------------

def check_files_for_review_confidence():
    header("STEP 5 – /api/triage/files_to_review Confidence Sanity Check")

    r = call_api("/api/triage/files_to_review")
    if r is None:
        return

    try:
        data = r.json()
        print("    Raw /api/triage/files_to_review JSON:")
        print(json.dumps(data, indent=2))
    except Exception:
        bad("Invalid JSON from /api/triage/files_to_review")
        print(r.text)
        return

    # Expect a list or an object with 'files'
    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if "files" in data and isinstance(data["files"], list):
            items = data["files"]

    if not items:
        warn("No files returned for review – nothing to check, but endpoint is responsive.")
        return

    # Check first few items for classification.confidence
    for i, item in enumerate(items[:5]):
        print(f"    Reviewing item #{i+1}:")
        print(json.dumps(item, indent=2))
        classification = item.get("classification") or item.get("result") or item
        conf = None
        if isinstance(classification, dict):
            if "confidence" in classification:
                conf = classification["confidence"]
            elif "confidence_score" in classification:
                conf = classification["confidence_score"]
        if isinstance(conf, (int, float)):
            ok(f"Item #{i+1} has numeric confidence: {conf}")
        else:
            bad(f"Item #{i+1} is missing numeric confidence field.")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("\n============================")
    print("🧪 AI FILE ORGANIZER – SANITY CHECK (MAX)")
    print("============================\n")

    check_gdrive_root()
    check_backend_endpoints()
    check_databases()
    check_classification_and_movement()
    check_files_for_review_confidence()

    print("\n============================")
    print("✅ Sanity check script finished. Review the output above for any ❌ or ⚠️.")
    print("============================\n")


if __name__ == "__main__":
    main()

