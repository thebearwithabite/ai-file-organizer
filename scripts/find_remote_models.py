#!/usr/bin/env python3
import json
import requests
from pathlib import Path

def get_metadata_root():
    return Path("/Users/user/Documents/AI_METADATA_SYSTEM")

def find_models():
    config_path = get_metadata_root() / "config" / "hybrid_config.json"
    if not config_path.exists():
        print("❌ hybrid_config.json not found.")
        return

    with open(config_path, "r") as f:
        config = json.load(f)
        remote = config.get("remote_powerhouse", {})
    
    if not remote.get("enabled"):
        print("❌ Remote powerhouse is disabled.")
        return

    services = remote.get("services", {})
    main_ip = remote.get("ip", "")

    # Endpoints to check
    endpoints = []
    
    # 1. WSL endpoint (where we expect models)
    ollama_cfg = services.get("ollama", {})
    wsl_ip = ollama_cfg.get("ip") or main_ip
    if wsl_ip:
        endpoints.append(("WSL/Linux", wsl_ip, ollama_cfg.get("port", 11434)))
    
    # 2. Windows host endpoint (as fallback)
    win_ip = services.get("resolve_mcp", {}).get("ip") or main_ip
    if win_ip and win_ip != wsl_ip:
        endpoints.append(("Windows Host", win_ip, 11434))

    print("🔍 Scanning Remote Powerhouse for AI Models...")
    print("-" * 50)

    for name, ip, port in endpoints:
        print(f"📡 Checking {name} at {ip}:{port}...")
        try:
            url = f"http://{ip}:{port}/api/tags"
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                if models:
                    print(f"✅ Found {len(models)} models:")
                    for m in models:
                        size_gb = m.get('size', 0) / (1024**3)
                        print(f"   - {m['name']} ({size_gb:.2f} GB)")
                else:
                    print(f"⚠️  Online, but no models found.")
            else:
                print(f"❌ Error: Received status {resp.status_code}")
        except Exception as e:
            print(f"❌ Could not connect: {e}")
        print("")

if __name__ == "__main__":
    find_models()
