#!/usr/bin/env python3
import os
from pathlib import Path
import socket

def check_env():
    print("📋 Checking Environment...")
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file missing!")
        return False
    
    with open(env_path, 'r') as f:
        content = f.read()
        if "GEMINI_API_KEY" not in content:
            print("❌ GEMINI_API_KEY is missing from .env!")
            return False
        else:
            print("✅ GEMINI_API_KEY found.")
    return True

def check_lock():
    print("\n📋 Checking for stale processes...")
    lock_path = Path("server.lock")
    if lock_path.exists():
        print("⚠️ server.lock exists. This might prevent the server from starting.")
        print("   If you see 'Another instance is already running', delete this file.")
    else:
        print("✅ No lock file found.")

def check_port():
    print("\n📋 Checking if port 8000 is occupied...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 8000))
    if result == 0:
        print("⚠️ Port 8000 is busy. The backend is likely already running.")
    else:
        print("✅ Port 8000 is free.")
    sock.close()

if __name__ == "__main__":
    check_env()
    check_lock()
    check_port()
    print("\n💡 Recommendation: Stop any running python processes, delete server.lock, ensure GEMINI_API_KEY is in .env, then run main.py again.")
