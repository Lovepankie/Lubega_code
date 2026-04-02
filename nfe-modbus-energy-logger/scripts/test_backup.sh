#!/bin/bash

# Test backup configuration and connection
# Run this script after configuring rclone to verify backup is working

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=================================================="
echo "NFE Backup System Test"
echo "=================================================="
echo ""

# Check if rclone is installed
if ! command -v rclone &> /dev/null; then
    echo "❌ rclone is not installed"
    echo ""
    echo "Install with:"
    echo "  sudo apt install rclone"
    exit 1
fi

echo "✅ rclone is installed"
echo ""

# Check if rclone remote is configured
echo "🔍 Checking rclone configuration..."
if rclone listremotes | grep -q "nextcloud:"; then
    echo "✅ Nextcloud remote is configured"
else
    echo "⚠️  Nextcloud remote not found"
    echo ""
    echo "Configure with:"
    echo "  rclone config"
    echo ""
    echo "Available remotes:"
    rclone listremotes
    echo ""
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""

# Test manual backup execution
echo "🧪 Testing backup execution..."
echo ""

cd "$PROJECT_DIR"

if [ -f "config/config.prod.yaml" ]; then
    CONFIG_FILE="config/config.prod.yaml"
elif [ -f "config/config.dev.yaml" ]; then
    CONFIG_FILE="config/config.dev.yaml"
else
    echo "❌ No config file found"
    exit 1
fi

echo "Using config: $CONFIG_FILE"
echo ""

# Run backup
python3 -m src.backup.main "$CONFIG_FILE"

echo ""
echo "=================================================="
echo "✅ Backup test complete!"
echo "=================================================="
echo ""
echo "Check backup destination to verify files were uploaded."
echo ""
echo "To enable automatic backups:"
echo "  sudo systemctl start backup.timer"
echo "  sudo systemctl enable backup.timer"
