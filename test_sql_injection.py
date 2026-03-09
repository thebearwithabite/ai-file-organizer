import os
import sqlite3
from metadata_generator import MetadataGenerator

def test_metadata_generator_sql_injection():
    print("🧪 Testing Metadata Generator SQL Injection")
    # Initialize the generator which creates the DB
    gen = MetadataGenerator()

    # Let's try to inject a malicious column
    malicious_payload = {
        "file_path": "/fake/path/test.txt",
        "file_name": "test.txt",
        "file_size": 1024,
        "valid_column, injected_column INT); DROP TABLE file_metadata; --": "malicious value"
    }

    print("Testing malicious payload...")
    success = gen.save_file_metadata(malicious_payload)
    print(f"Save operation result: {success}")

    # Check if DB is still intact
    print("Checking if database still exists and table is intact...")
    try:
        with sqlite3.connect(gen.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM file_metadata")
            count = cursor.fetchone()[0]
            print(f"✅ Table file_metadata is intact. Count: {count}")
    except sqlite3.OperationalError as e:
        print(f"❌ SQL Injection was successful: {e}")
        assert False, "SQL injection failed"

    print("SQL Injection test passed!")

if __name__ == "__main__":
    test_metadata_generator_sql_injection()
