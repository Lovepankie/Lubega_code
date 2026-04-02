#!/bin/bash

# NFE Logger Rollback Script
# Restores production from a backup

set -e

# Use current user's home directory (works for any user)
USER_HOME="$HOME"
PROD_DIR="$USER_HOME/nfe-modbus-energy-logger-prod"
BACKUP_DIR="$USER_HOME/nfe-backups"
SERVICE_NAME="meter.service"

echo "=================================================="
echo "NFE Logger Production Rollback"
echo "=================================================="
echo ""

if [ -z "$1" ]; then
    echo "📋 Available backups:"
    echo ""
    ls -lht "$BACKUP_DIR" 2>/dev/null || echo "  (no backups found)"
    echo ""
    echo "Usage: $0 <backup-name>"
    echo "Example: $0 nfe-backup-20260319_140530"
    exit 1
fi

BACKUP_NAME="$1"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

if [ ! -d "$BACKUP_PATH" ]; then
    echo "❌ Backup not found: $BACKUP_PATH"
    echo ""
    echo "Available backups:"
    ls -lh "$BACKUP_DIR"
    exit 1
fi

echo "🔄 Rolling back to: $BACKUP_NAME"
echo "   From: $BACKUP_PATH"
echo "   To:   $PROD_DIR"
echo ""

read -p "Continue? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled"
    exit 0
fi

echo ""
echo "🛑 Stopping production service..."
sudo systemctl stop "$SERVICE_NAME"
sleep 2

echo "🔄 Restoring from backup..."
rsync -av --delete \
    --exclude 'data/' \
    "$BACKUP_PATH/" "$PROD_DIR/"

echo ""
echo "🚀 Starting production service..."
sudo systemctl start "$SERVICE_NAME"
sleep 3

if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    echo ""
    echo "=================================================="
    echo "✅ Rollback successful!"
    echo "=================================================="
    echo ""
    sudo systemctl status "$SERVICE_NAME" --no-pager -l | head -20
    echo ""
    echo "Monitor logs with:"
    echo "  sudo journalctl -u $SERVICE_NAME -f"
else
    echo ""
    echo "❌ Service failed to start after rollback"
    echo "Check logs:"
    echo "  sudo journalctl -u $SERVICE_NAME -n 100"
    exit 1
fi
