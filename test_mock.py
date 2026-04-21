import sqlite3

def run_test():
    with sqlite3.connect('/tmp/metadata.db') as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        print(cursor.fetchall())
run_test()
