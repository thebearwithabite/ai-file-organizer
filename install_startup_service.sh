#!/bin/bash
# Install Adaptive Background Monitor as a LaunchAgent
# This will make it start automatically at login and restart if it crashes

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.aifileorganizer.adaptivemonitor.plist"
PLIST_SOURCE="$SCRIPT_DIR/$PLIST_NAME"
LAUNCHAGENT_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="$LAUNCHAGENT_DIR/$PLIST_NAME"

echo "🚀 Installing AI File Organizer Adaptive Monitor Startup Service"
echo "================================================================"
echo ""

# Create LaunchAgents directory if it doesn't exist
if [ ! -d "$LAUNCHAGENT_DIR" ]; then
    echo "📁 Creating LaunchAgents directory..."
    mkdir -p "$LAUNCHAGENT_DIR"
fi

# Stop and unload existing service if running
if launchctl list | grep -q "$PLIST_NAME"; then
    echo "⏸️  Stopping existing service..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Copy plist file to LaunchAgents directory
echo "📋 Installing LaunchAgent..."
cp "$PLIST_SOURCE" "$PLIST_DEST"

# Load and start the service
echo "▶️  Starting service..."
launchctl load "$PLIST_DEST"

# Verify service is running
sleep 2
if launchctl list | grep -q "com.aifileorganizer.adaptivemonitor"; then
    echo ""
    echo "✅ SUCCESS! Adaptive Monitor is now running as a startup service"
    echo ""
    echo "📊 Service Details:"
    echo "   • Starts automatically at login"
    echo "   • Restarts automatically if it crashes"
    echo "   • Logs: ~/Library/Logs/ai-organizer-monitor*.log"
    echo ""
    echo "🛠️  Management Commands:"
    echo "   • Check status:  launchctl list | grep adaptivemonitor"
    echo "   • Stop service:  launchctl unload ~/Library/LaunchAgents/$PLIST_NAME"
    echo "   • Start service: launchctl load ~/Library/LaunchAgents/$PLIST_NAME"
    echo "   • Uninstall:     rm ~/Library/LaunchAgents/$PLIST_NAME"
    echo ""
else
    echo ""
    echo "⚠️  Service installed but may not be running. Check logs at:"
    echo "   ~/Library/Logs/ai-organizer-monitor*.log"
    echo ""
fi
