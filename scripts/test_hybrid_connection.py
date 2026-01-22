
import json
import requests
import asyncio
import sys
from pathlib import Path

def get_metadata_root():
    return Path("/Users/ryanthomson/Documents/AI_METADATA_SYSTEM")

async def test_ollama(ip, port):
    print(f"📡 Testing Ollama at {ip}:{port}...")
    try:
        url = f"http://{ip}:{port}/api/tags"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]
            print(f"✅ Ollama is online!")
            print(f"📊 Available Models: {', '.join(model_names)}")
            return True
        else:
            print(f"❌ Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to reach Ollama: {e}")
        return False

async def test_resolve_mcp(ip, port, endpoint):
    url = f"http://{ip}:{port}{endpoint}"
    print(f"📡 Testing Resolve MCP (SSE) at {url}...")
    try:
        # Just a simple GET to see if it responds (SSE usually accepts GET or is managed by client)
        # We'll just check if the port is open/responding
        response = requests.get(url, timeout=5)
        # SSE endpoints might return 404 or something else on a plain GET if not properly handled, 
        # but usually uvicorn/fastapi returns something.
        print(f"✅ Resolve MCP port is responding (Status: {response.status_code})")
        return True
    except Exception as e:
        print(f"⚠️ Resolve MCP not responding: {e} (Expected if the server isn't running yet)")
        return False

async def main():
    config_path = get_metadata_root() / "config" / "hybrid_config.json"
    if not config_path.exists():
        print(f"❌ Config file not found at {config_path}")
        return

    with open(config_path, "r") as f:
        config = json.load(f)
        remote = config.get("remote_powerhouse", {})
        
    if not remote.get("enabled"):
        print("❌ Remote powerhouse is disabled in config.")
        return

    ip = remote.get("ip")
    services = remote.get("services", {})
    
    ollama_config = services.get("ollama", {})
    resolve_config = services.get("resolve_mcp", {})

    print(f"🚀 Starting Hybrid Connectivity Test")
    print("-" * 50)
    
    ollama_ip = ollama_config.get("ip") or ip
    ollama_ok = await test_ollama(ollama_ip, ollama_config.get("port", 11434))
    
    resolve_ip = resolve_config.get("ip") or ip
    resolve_ok = await test_resolve_mcp(resolve_ip, resolve_config.get("port", 8000), resolve_config.get("endpoint", "/sse"))
    
    print("-" * 50)
    if ollama_ok:
        print("🎉 HYBRID VISION READY!")
    else:
        print("🛠️ VISION OFFLOADING PENDING (Check Ollama IP in config)")

if __name__ == "__main__":
    asyncio.run(main())
