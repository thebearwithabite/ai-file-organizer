#!/bin/bash
# Migrate metadata system from iCloud-synced Documents to local-only home root
# Fixes "disk I/O error" caused by iCloud locking SQLite databases.

OLD_PATH="$HOME/Documents/AI_METADATA_SYSTEM"
NEW_PATH="$HOME/AI_METADATA_SYSTEM"

echo "🚀 Starting Metadata Migration..."
echo "================================="

if [ ! -d "$OLD_PATH" ]; then
    echo "❌ Source path not found: $OLD_PATH"
    exit 1
fi

if [ -d "$NEW_PATH" ]; then
    echo "⚠️  Destination already exists: $NEW_PATH"
    echo "   Moving existing destination to backup..."
    mv "$NEW_PATH" "${NEW_PATH}_backup_$(date +%Y%m%d_%H%M%S)"
fi

echo "📦 Moving metadata files..."
cp -a "$OLD_PATH" "$NEW_PATH"

echo "✅ Files copied to $NEW_PATH"
echo "🛠️  Verifying destination..."

if [ -f "$NEW_PATH/databases/metadata.db" ]; then
    echo "✅ Database verified at new location."
else
    echo "⚠️  Warning: metadata.db not found in new location!"
fi

echo "🧹 Renaming old location to prevent accidental use..."
mv "$OLD_PATH" "${OLD_PATH}_MIGRATED"

echo ""
echo "🎉 Migration Complete!"
echo "   New Path: $NEW_PATH"
echo "   iCloud Sync Risk: ELIMINATED"
echo "================================="
