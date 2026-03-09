## 2026-03-09 - Fixed SQL Injection Vulnerability in Metadata Generator

**Vulnerability:** The `save_file_metadata` function in `metadata_generator.py` directly interpolated dictionary keys provided by user inputs (`metadata.keys()`) into a dynamic `INSERT OR REPLACE INTO file_metadata` query using string formatting (`', '.join(columns)`). This permitted SQL injection if a user constructed malicious metadata keys, bypassing parameterization which only protected the values.

**Learning:** Dynamic column names in SQL statements cannot be parameterized using standard `?` placeholders. While dictionary values were correctly parameterized, the keys were assumed to be safe, which is a common oversight when dealing with arbitrary JSON/dictionary inputs in Python SQLite interfaces.

**Prevention:** To safely construct SQL queries with dynamic columns, always fetch the allowed column names from the database schema (e.g., using `PRAGMA table_info(table_name)`) to create a strict allowlist. Filter any incoming dictionary keys against this allowlist before building the SQL query string.
