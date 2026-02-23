# Sentinel's Journal

## 2025-01-22 - Path Traversal in File API
**Vulnerability:** The `get_file_content`, `get_file_preview_text`, and `open_file` endpoints in `main.py` allowed reading or opening arbitrary files by supplying an absolute path, only checking for hidden files (starting with `.`) but not enforcing directory containment.
**Learning:** The assumption that monitoring paths via `watchdog` implies API security was flawed. API endpoints need explicit path validation against allowed roots, regardless of background monitoring logic.
**Prevention:** Implemented `validate_path_is_safe` in `security_utils.py` that checks against a strict allowlist of roots (Documents, Downloads, Desktop, Metadata Root, Organizer Base) and enforces it in all file-accessing endpoints.
