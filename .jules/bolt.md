## 2024-05-23 - [Optimizing Hashing with Connection Reuse]
**Learning:** SQLite connection overhead is significant in tight loops (N+1 problem). Reusing a connection improved batch processing by ~36%. Increasing read buffer from 64KB to 1MB also helped I/O throughput.
**Action:** Look for other places where `sqlite3.connect` is called inside loops. Always check buffer sizes for file processing.

## 2025-05-26 - [Optimizing Adaptive Monitor Event Processing]
**Learning:** Reusing SQLite connections in `AdaptiveBackgroundMonitor._process_file_events` loop reduced database insert latency by ~97% (from ~2ms to ~0.05ms per record). N+1 connection creation was a major bottleneck during batch file operations.
**Action:** Always pass `db_connection` optional arguments to persistence methods called in loops.

## 2025-05-26 - [Reducing Stat Calls in File Scans]
**Learning:** `os.walk` + `Path.stat` is inefficient because it discards OS-provided metadata and forces re-statting. Switching to `os.scandir` and propagating cached `stat_result` (size, mtime) through the pipeline reduced `stat` syscalls by ~54% in the deduplication flow.
**Action:** When scanning directories, use `os.scandir` to capture metadata early and pass it down to consumers instead of re-fetching it.
