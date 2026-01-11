## 2024-05-23 - [Optimizing Hashing with Connection Reuse]
**Learning:** SQLite connection overhead is significant in tight loops (N+1 problem). Reusing a connection improved batch processing by ~36%. Increasing read buffer from 64KB to 1MB also helped I/O throughput.
**Action:** Look for other places where  is called inside loops. Always check buffer sizes for file processing.
## 2024-05-23 - [Optimizing Hashing with Connection Reuse]
**Learning:** SQLite connection overhead is significant in tight loops (N+1 problem). Reusing a connection improved batch processing by ~36%. Increasing read buffer from 64KB to 1MB also helped I/O throughput.
**Action:** Look for other places where `sqlite3.connect` is called inside loops. Always check buffer sizes for file processing.
