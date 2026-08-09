"""
Google Secret Manager integration for AI File Organizer.
Replaces .env files — all secrets live in Google Secret Manager.
Uses Application Default Credentials (ADC) for auth.
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Project where secrets live
GCP_PROJECT = "gen-lang-client-0717156022"

# Secret names in Google Secret Manager (prefix convention: ai-file-organizer/)
SECRET_KEYS = [
    # === API Keys ===
    "OPENAI_API_KEY",           # OpenAI API key for GPT-4o classification
    "GEMINI_API_KEY",           # Google Gemini API key (vision, analysis)
    "GOOGLE_API_KEY",           # Fallback Google API key (can be same as GEMINI)
    "KIE_API_KEY",              # KIE client API key

    # === Google Drive OAuth ===
    "GDRIVE_OAUTH_CREDENTIALS", # Full JSON of Google Drive OAuth client secrets

    # === Non-sensitive config (convenience — can also live in config.yaml) ===
    "AI_ORGANIZER_GDRIVE_ROOT",
    "AI_ORGANIZER_GDRIVE_EMAIL",
    "AI_ORGANIZER_ALLOW_LOCAL_FALLBACK",
    "AI_ORGANIZER_BASE",
    "AUTO_MONITOR_PATHS",
    "AUTO_MONITOR_INTERVAL",
    "DATABASE_PATH",
    "CONFIDENCE_MODE",
    "DEV_MODE",
]


def _get_secret_value(secret_id: str) -> Optional[str]:
    """Fetch a single secret version from Google Secret Manager."""
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.debug(f"Secret '{secret_id}' not found or inaccessible: {e}")
        return None


def load_secrets() -> dict[str, str]:
    """
    Load all configured secrets from Google Secret Manager into os.environ.
    Also handles GDrive OAuth JSON: writes it to disk and sets
    GOOGLE_APPLICATION_CREDENTIALS if applicable.

    Returns a dict of {key: 'found'|'missing'} for reporting.
    """
    status = {}

    for key in SECRET_KEYS:
        value = _get_secret_value(key)
        if value:
            os.environ[key] = value
            status[key] = "found"
            logger.info(f"Loaded secret: {key}")
        else:
            status[key] = "missing"
            logger.debug(f"Secret not set: {key}")

    # --- Handle GDrive OAuth JSON ---
    gdrive_json = os.environ.get("GDRIVE_OAUTH_CREDENTIALS")
    if gdrive_json:
        try:
            # Write to the standard location the GDrive module expects
            creds_dir = Path.home() / ".config" / "ai-file-organizer"
            creds_dir.mkdir(parents=True, exist_ok=True)
            creds_path = creds_dir / "gdrive_credentials.json"

            # Validate it's valid JSON before writing
            parsed = json.loads(gdrive_json)
            creds_path.write_text(json.dumps(parsed, indent=2))
            os.environ["GDRIVE_CREDENTIALS_PATH"] = str(creds_path)
            logger.info(f"GDrive OAuth credentials written to {creds_path}")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to process GDRIVE_OAUTH_CREDENTIALS: {e}")
            status["GDRIVE_OAUTH_CREDENTIALS"] = "invalid_json"

    # Report
    found = [k for k, v in status.items() if v == "found"]
    missing = [k for k, v in status.items() if v != "found"]

    if missing:
        logger.warning(f"Missing secrets: {', '.join(missing)}")
    logger.info(f"Loaded {len(found)}/{len(SECRET_KEYS)} secrets from Secret Manager")

    return status
