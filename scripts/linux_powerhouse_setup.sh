#!/bin/bash
# AI File Organizer: Linux Powerhouse Setup Script (Ubuntu/WSL)
# This script prepares your Ubuntu/WSL instance to act as a worker for the AI File Organizer.

set -e

echo "🚀 Starting AI File Organizer: Linux Powerhouse Setup"

# 1. Update and install basic dependencies
echo "📦 Updating system and installing dependencies..."
sudo apt-get update
sudo apt-get install -y git curl python3 python3-pip python3-venv

# 2. Check for Tailscale (assuming it's on Windows, but WSL might need it)
if ! command -v tailscale &> /dev/null; then
    echo "⚠️ Tailscale command not found in WSL. Ensure Tailscale is running on your Windows host."
    echo "If you have Mirrored networking enabled, WSL will share the host's Tailscale connection."
else
    TS_IP=$(tailscale ip -4)
    echo "✅ Tailscale is active. Your IP is: $TS_IP"
fi

# 3. Install Ollama (Linux version)
if ! command -v ollama &> /dev/null; then
    echo "🧠 Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "✅ Ollama is already installed."
fi

# Ensure the vision model is pulled
echo "🤖 Pulling vision model (qwen2.5vl:7b)..."
ollama pull qwen2.5vl:7b

# 4. Setup MCP Bridge for Resolve
echo "🏗️ Setting up Resolve MCP Bridge..."
BRIDGE_DIR="$HOME/AI_Organizer_Bridge"
mkdir -p "$BRIDGE_DIR"

if [ ! -d "$BRIDGE_DIR/davinci-resolve-mcp" ]; then
    cd "$BRIDGE_DIR"
    git clone https://github.com/samuelgursky/davinci-resolve-mcp.git
else
    echo "✅ Resolve MCP repository already exists."
fi

# 5. Instructions
echo ""
echo "🎯 FINAL STEPS:"
echo "1. On Windows: Open DaVinci Resolve."
echo "2. On Windows: Go to Preferences -> System -> General -> External Scripting -> Set to 'Local'."
echo "3. In this Ubuntu terminal, start the MCP server:"
echo "   python3 $BRIDGE_DIR/davinci-resolve-mcp/src/resolve_mcp_server.py --transport sse"
echo ""
echo "✅ SETUP COMPLETE. Your WSL IP is: $(hostname -I | awk '{print $1}')"
echo "Ensure this IP matches what the Mac (Antigravity) is looking for."
