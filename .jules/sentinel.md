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

## 2024-05-30 - SQL Injection via Dictionary Keys in Dynamic Queries

**Vulnerability:** The `save_file_metadata` function in `metadata_generator.py` accepted an untrusted dictionary of metadata and dynamically constructed an `INSERT` statement using the dictionary's keys as column names (`column_names = ', '.join(columns)`). This allowed SQL injection if an attacker supplied a malformed key (e.g., `invalid_column) VALUES (?); DROP TABLE files; --`).

**Learning:** While parameterization (`?`) protects against SQL injection in values, it does not protect against injection in table or column names. When dynamically building queries where column names are derived from user input or external dictionaries, the keys must be strictly validated against an explicit schema allowlist. Additionally, even valid column names should be quoted (double-quoted in SQLite) to guard against reserved words and future schema changes. Using `INSERT ... ON CONFLICT DO UPDATE SET` (UPSERT) rather than `INSERT OR REPLACE` also preserves existing column values when only a subset of columns is supplied.

**Prevention:**
1. Never use untrusted input directly as column names or table names in SQL queries.
2. Fetch valid columns dynamically using `PRAGMA table_info(table_name)` in SQLite (or hardcode an allowlist).
3. Pre-filter dictionaries to only include keys that match the explicitly validated schema allowlist before building dynamic queries.
4. Always double-quote SQL identifiers (e.g., `"column_name"`) and escape embedded double-quotes to handle reserved words and special characters.
5. Cache the schema allowlist on the instance rather than re-querying it on every call to avoid unnecessary overhead in batch scenarios.
