1. **Analyze and create plan for performance improvement**
2. Replace N+1 queries with batched `executemany` during user decision recording in `interactive_batch_processor.py`. Specifically, inside `_record_user_decision`, the current implementation iterates over `group.file_previews` and executes an `INSERT` statement for each preview one by one. I will refactor this to accumulate the records and execute a single `conn.executemany` statement.
3. Replace N+1 queries with batched `executemany` in `_get_cached_preview` (if applicable) or any other tight loops with `execute` where possible.
4. Verify changes by running testing scripts or manual validation using a test SQLite database.
5. Execute pre-commit instructions.
6. Submit PR with '⚡ Bolt: [performance improvement]' prefix.
