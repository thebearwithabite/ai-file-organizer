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

## 2024-05-30 - Widespread Argument Injection Vulnerability in File Operations

**Vulnerability:** Several modules (`system_storage_cleanup.py`, `dev-archive/emergency_bulk_staging.py`, `dev-archive/repair_mislabeled_jsons.py`) passed unvalidated `pathlib.Path` strings directly to `subprocess.run` calls (e.g., for `du`, `rm`, `file`). If an attacker controlled the filename, they could name a file starting with `-` (e.g., `-rf`), leading to argument injection.

**Learning:** The argument injection vulnerability found in `vision_content_extractor.py` and `main.py` is a widespread pattern in this codebase. Any invocation of external command-line tools using `subprocess.run` with user-controlled file paths must use absolute paths to prevent the tool from interpreting the filename as an option.

**Prevention:** Always convert `pathlib.Path` objects to absolute strings using `str(path.absolute())` before passing them as arguments to `subprocess.run`.

## 2024-05-30 - SQL Injection via unvalidated dynamic column names

**Vulnerability:** The `_migrate_database_schema` function in `metadata_generator.py` uses an f-string to construct an `ALTER TABLE` query. The variables are hardcoded keys in a dictionary, however if the keys in the dictionary are user-controlled in the future, it is an avenue for SQL injection.

**Learning:** When dynamically generating SQL `ALTER TABLE` statements to add columns, standard `?` parameterization does not protect column keys. You must validate the column name to prevent SQL injection.

**Prevention:** Use Python's `str.isidentifier()` to validate column names and prevent SQL injection.
