#!/bin/bash

# AI File Organizer - Powerhouse Startup Script
# This script launches both the Backend (FastAPI) and Frontend (React/Vite)

# Configuration
PROJECT_ROOT="/Users/ryanthomson/Github/ai-file-organizer"
LOG_DIR="$PROJECT_ROOT/logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Timestamp for the log
echo "--- Starting Powerhouse at $(date) ---" >> "$LOG_DIR/startup.log"

# 1. Start Backend
echo "🚀 Starting Backend (FastAPI)..." >> "$LOG_DIR/startup.log"
cd "$PROJECT_ROOT"
source venv/bin/activate
# Run in background, redirect logs
nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "   Backend started with PID: $BACKEND_PID" >> "$LOG_DIR/startup.log"

# 2. Start Frontend
echo "🚀 Starting Frontend (Vite)..." >> "$LOG_DIR/startup.log"
cd "$PROJECT_ROOT/frontend_v2"
# Run in background, redirect logs
nohup npm run dev -- --host > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "   Frontend started with PID: $FRONTEND_PID" >> "$LOG_DIR/startup.log"

# 3. Save PIDs for cleaner shutdown if needed
echo "$BACKEND_PID" > "$LOG_DIR/backend.pid"
echo "$FRONTEND_PID" > "$LOG_DIR/frontend.pid"

echo "✅ Powerhouse is running!" >> "$LOG_DIR/startup.log"
echo "   Backend: http://localhost:8000" >> "$LOG_DIR/startup.log"
echo "   Frontend: http://localhost:5173" >> "$LOG_DIR/startup.log"
