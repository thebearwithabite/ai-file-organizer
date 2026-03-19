## 2024-05-30 - Local File Inclusion and Argument Injection in File Reading API

**Vulnerability:** The API endpoints `/api/open-file`, `/api/files/content`, and `/api/files/preview-text` accepted unvalidated absolute file paths directly from API requests, allowing Local File Inclusion (LFI) via paths like `/etc/passwd`. Additionally, the `/api/open-file` endpoint passed raw strings to `subprocess.run(['open', path])`, enabling argument injection if a filename started with `-`.

**Learning:** When APIs expose raw file system operations (like reading or passing paths to system commands), depending on clients to send "valid" paths is insufficient. Python's `Path.resolve()` combined with `is_relative_to` provides a robust mechanism to evaluate the *final* destination of a path, neutralizing relative traversal (`../`). However, for endpoints supporting custom folders (like an organizer app), hardcoded whitelists can break functionality. Instead, limiting access to a broad safe boundary (like the user's home directory `Path.home()`) strikes a balance. Furthermore, treating strings as arguments requires strict validation; resolving local paths to absolute strings inherently prefixes them with root (`/`) or drive letters, naturally neutralizing argument injection (`-rf`).

**Prevention:**
1. Always resolve paths to absolute destinations using `.resolve()` before operating on them.
2. Verify path containment within allowed boundaries using `is_relative_to` (or `security_utils.validate_path_within_base`).
3. For endpoints invoking system commands with user-provided paths, ensure paths are absolute to prevent them from being parsed as options (flags starting with `-`), or explicitly block paths where `.name.startswith('-')`.
4. Special care must be given to URL support to prevent bypasses like `file:///etc/passwd` when filtering `http`/`https`.

## 2024-05-30 - Argument Injection Vulnerability in Video Processing Tools

**Vulnerability:** The `vision_content_extractor.py` module passed unvalidated string file paths directly to `subprocess.run` calls for `ffprobe` and `ffmpeg` when preparing video samples. If an attacker controlled the filename, they could name a file starting with `-` (e.g., `-someflag`), leading to argument injection where the command-line tool interprets the filename as an option.

**Learning:** When invoking external command-line tools (like `ffmpeg` or `ffprobe`) using `subprocess.run` with user-controlled file paths, using `str(file_path)` is insufficient to prevent argument injection. If a path string happens to be a relative filename like `-v`, it can alter the tool's behavior, potentially leading to unauthorized operations or command execution depending on the tool's supported flags.

**Prevention:**
1. Always convert `pathlib.Path` objects to absolute strings using `str(path.absolute())` before passing them as arguments to `subprocess.run`.
2. Absolute paths always begin with a directory separator (`/` on Unix) or a drive letter (`C:\` on Windows), guaranteeing the command-line tool parses them as file paths rather than flags or options.
## 2024-05-30 - SQL Injection via Unvalidated Dictionary Keys in Dynamic Queries

**Vulnerability:** The `MetadataGenerator.save_file_metadata` method was vulnerable to SQL injection because it dynamically constructed an `INSERT OR REPLACE INTO file_metadata` query by directly using the dictionary keys and values provided by the caller without validating the keys against the actual database schema. Additionally, `_migrate_database_schema` directly interpolated column names into `ALTER TABLE` statements without verifying they were valid identifiers.

**Learning:** When constructing dynamic SQL queries (e.g., `INSERT` or `UPDATE` with dynamically generated column names), standard `?` parameterization does not protect column keys. You must use an explicit schema allowlist (e.g., fetching `PRAGMA table_info` from the database) to filter dictionary keys and prevent SQL injection. For DDL statements like `ALTER TABLE`, user input must be strictly validated as a valid SQL identifier (e.g., using `.isidentifier()`).

**Prevention:**
1. Dynamically fetch the allowed schema using `PRAGMA table_info(table_name)`.
2. Filter the incoming dictionary keys against the allowed schema to ensure only safe, existing columns are included in the query.
3. For dynamic column names in DDL statements, validate them using `col_name.isidentifier()` to ensure they contain only valid characters.
