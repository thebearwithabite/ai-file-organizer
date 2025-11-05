#!/bin/bash
# Adaptive Background Monitor Startup Script
# Ensures the monitor runs continuously and restarts if it fails

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Log file for debugging
LOG_FILE="$HOME/Library/Logs/ai-file-organizer-monitor.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "$(date): Starting Adaptive Background Monitor" >> "$LOG_FILE"

# Start the monitor
python adaptive_background_monitor.py start >> "$LOG_FILE" 2>&1

# Keep the script running (LaunchAgent will restart if this exits)
exit $?
