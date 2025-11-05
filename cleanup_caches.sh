#!/bin/bash
# Automated Cache Cleanup Script
# Prevents disk space emergencies by cleaning caches weekly

echo "🧹 AI File Organizer - Cache Cleanup Script"
echo "=========================================="
date

# Check available space before cleanup
BEFORE=$(df -h / | tail -1 | awk '{print $4}')
echo "📊 Disk space before cleanup: $BEFORE"

# Clean CloudKit cache (the big culprit - 36GB!)
echo "🔧 Cleaning CloudKit cache..."
rm -rf ~/Library/Caches/CloudKit/* 2>/dev/null
CLOUDKIT_CLEANED=$?

# Clean Google cache
echo "🔧 Cleaning Google cache..."
find ~/Library/Caches/Google -type f -atime +7 -delete 2>/dev/null

# Clean pip cache (can rebuild as needed)
echo "🔧 Cleaning pip cache..."
rm -rf ~/Library/Caches/pip/* 2>/dev/null

# Clean Playwright browsers (can reinstall)
echo "🔧 Cleaning Playwright cache..."
rm -rf ~/Library/Caches/ms-playwright/* 2>/dev/null

# Clean old logs
echo "🔧 Cleaning old log files..."
find ~/Library/Logs -name "*.log" -mtime +30 -delete 2>/dev/null

# Empty Trash if over 500MB
TRASH_SIZE=$(du -sm ~/.Trash 2>/dev/null | awk '{print $1}')
if [ "$TRASH_SIZE" -gt 500 ]; then
    echo "🗑️  Emptying Trash ($TRASH_SIZE MB)..."
    rm -rf ~/.Trash/* 2>/dev/null
fi

# Check space after cleanup
AFTER=$(df -h / | tail -1 | awk '{print $4}')
echo ""
echo "✅ Cleanup complete!"
echo "📊 Disk space after cleanup: $AFTER"
echo "=========================================="
