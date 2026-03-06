import time
import os
import sqlite3
from pathlib import Path
from datetime import datetime
from tagging_system import ComprehensiveTaggingSystem, TaggedFile

def run_benchmark():
    system = ComprehensiveTaggingSystem("test_bench_base")

    # create fake tagged file
    tf = TaggedFile(
        file_path=Path("test_file.txt"),
        auto_tags=["tag1", "tag2", "tag3"],
        user_tags=["user1", "user2"],
        confidence_scores={"tag1": 0.9, "tag2": 0.8},
        tag_sources={"tag1": "auto"},
        last_tagged=datetime.now(),
        file_hash="fakehash"
    )

    start_time = time.time()
    for i in range(100):
        tf.file_path = Path(f"test_file_{i}.txt")
        system.save_tagged_file(tf)

    duration = time.time() - start_time
    print(f"Original Time for 100 saves: {duration:.4f} seconds")

if __name__ == "__main__":
    run_benchmark()
