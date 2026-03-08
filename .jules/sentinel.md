## 2024-05-30 - Local File Inclusion and Argument Injection in File Reading API

**Vulnerability:** The API endpoints `/api/open-file`, `/api/files/content`, and `/api/files/preview-text` accepted unvalidated absolute file paths directly from API requests, allowing Local File Inclusion (LFI) via paths like `/etc/passwd`. Additionally, the `/api/open-file` endpoint passed raw strings to `subprocess.run(['open', path])`, enabling argument injection if a filename started with `-`.

**Learning:** When APIs expose raw file system operations (like reading or passing paths to system commands), depending on clients to send "valid" paths is insufficient. Python's `Path.resolve()` combined with `is_relative_to` provides a robust mechanism to evaluate the *final* destination of a path, neutralizing relative traversal (`../`). However, for endpoints supporting custom folders (like an organizer app), hardcoded whitelists can break functionality. Instead, limiting access to a broad safe boundary (like the user's home directory `Path.home()`) strikes a balance. Furthermore, treating strings as arguments requires strict validation; resolving local paths to absolute strings inherently prefixes them with root (`/`) or drive letters, naturally neutralizing argument injection (`-rf`).

**Prevention:**
1. Always resolve paths to absolute destinations using `.resolve()` before operating on them.
2. Verify path containment within allowed boundaries using `is_relative_to` (or `security_utils.validate_path_within_base`).
3. For endpoints invoking system commands with user-provided paths, ensure paths are absolute to prevent them from being parsed as options (flags starting with `-`), or explicitly block paths where `.name.startswith('-')`.
4. Special care must be given to URL support to prevent bypasses like `file:///etc/passwd` when filtering `http`/`https`.
## 2024-05-31 - SQL Injection via Unvalidated Column Names
**Vulnerability:** The `save_file_metadata` method in `metadata_generator.py` dynamically constructed SQL `INSERT` statements using raw dictionary keys from the `metadata` argument without validation, enabling severe SQL injection if user-provided data was used as keys.
**Learning:** Directly interpolating map/dictionary keys into dynamic SQL commands for column names bypasses standard parameterization protection. This is a critical risk when dynamically inserting structured or arbitrary JSON payload keys into databases.
**Prevention:** Always maintain a strict allowlist (schema definition) of valid column names and filter incoming data keys against this allowlist *before* constructing dynamic SQL statements, ensuring untrusted strings are never executed as database commands.
