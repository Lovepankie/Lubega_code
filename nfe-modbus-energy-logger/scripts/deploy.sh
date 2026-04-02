#!/bin/bash

# NFE Logger Production Deployment Script
# Syncs tested code from staging to production

set -e  # Exit on error

# Use current user's home directory (works for any user)
USER_HOME="$HOME"
STAGING_DIR="$USER_HOME/nfe-modbus-energy-logger"
PROD_DIR="$USER_HOME/nfe-modbus-energy-logger-prod"
BACKUP_DIR="$USER_HOME/nfe-backups"
SERVICE_NAME="meter.service"

echo "=================================================="
echo "NFE Logger Production Deployment"
echo "=================================================="
echo ""

# 1. Check if staging directory exists
if [ ! -d "$STAGING_DIR" ]; then
    echo "❌ Staging directory not found: $STAGING_DIR"
    exit 1
fi

# Check if this is first-time deployment
FIRST_DEPLOYMENT=false
if [ ! -d "$PROD_DIR" ]; then
    FIRST_DEPLOYMENT=true
    echo "🎉 First-time deployment detected!"
    echo ""
fi

# First-time setup checks
if [ "$FIRST_DEPLOYMENT" = true ]; then
    echo "🔍 Running first-time setup checks..."
    echo ""

    # Check if Python packages are installed
    echo "📦 Checking Python dependencies..."
    if ! python3 -c "import pymodbus, yaml" 2>/dev/null; then
        echo "⚠️  Python dependencies not installed!"
        echo ""
        echo "Installing dependencies from requirements.txt..."
        pip3 install -r "$STAGING_DIR/requirements.txt" --break-system-packages
        echo "✅ Dependencies installed"
    else
        echo "✅ Python dependencies already installed"
    fi
    echo ""

    # Check if config.prod.yaml exists
    if [ ! -f "$STAGING_DIR/config/config.prod.yaml" ]; then
        echo "⚠️  config.prod.yaml not found!"
        echo ""
        echo "Creating config.prod.yaml from template..."
        cp "$STAGING_DIR/config/config.yaml.example" "$STAGING_DIR/config/config.prod.yaml"
        echo "✅ Created config/config.prod.yaml"
        echo ""
        echo "⚠️  IMPORTANT: Edit config/config.prod.yaml with your meter settings before continuing!"
        echo "   Press Ctrl+C to cancel, or Enter to continue anyway..."
        read -r
    else
        echo "✅ config.prod.yaml exists"
    fi
    echo ""

    echo "✅ First-time setup complete!"
    echo ""
fi

# Check if systemd service is installed (independent of first deployment)
echo "🔍 Checking systemd services..."
CURRENT_USER=$(whoami)

# Install meter service
if [ ! -f "/etc/systemd/system/$SERVICE_NAME" ]; then
    echo "⚠️  Meter service not installed!"
    echo ""
    echo "Installing meter service..."

    sed "s|User=nfetestpi2|User=$CURRENT_USER|g; s|/home/nfetestpi2|$USER_HOME|g" \
        "$STAGING_DIR/systemd/$SERVICE_NAME" | sudo tee /etc/systemd/system/$SERVICE_NAME > /dev/null

    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    echo "✅ Meter service installed and enabled"
else
    echo "✅ Meter service already installed"
fi

# Install backup service and timer
if [ ! -f "/etc/systemd/system/backup.service" ]; then
    echo "⚠️  Backup service not installed!"
    echo ""
    echo "Installing backup service and timer..."

    sed "s|User=nfetestpi2|User=$CURRENT_USER|g; s|/home/nfetestpi2|$USER_HOME|g" \
        "$STAGING_DIR/systemd/backup.service" | sudo tee /etc/systemd/system/backup.service > /dev/null

    sudo cp "$STAGING_DIR/systemd/backup.timer" /etc/systemd/system/

    sudo systemctl daemon-reload
    sudo systemctl enable backup.timer
    echo "✅ Backup service and timer installed and enabled"
else
    echo "✅ Backup service already installed"
fi

echo ""

# Check timezone (on every deployment - critical for billing)
echo "🌍 Checking system timezone..."
CURRENT_TZ=$(timedatectl show --property=Timezone --value)
echo "   Current timezone: $CURRENT_TZ"

# Warn if timezone looks incorrect
if [ "$CURRENT_TZ" = "Etc/UTC" ] || [ "$CURRENT_TZ" = "UTC" ]; then
    echo ""
    echo "⚠️  WARNING: Timezone is set to UTC!"
    echo "   This will cause incorrect billing timestamps."
    echo ""
    echo "   Recommended timezones:"
    echo "   - Kenya deployment: Africa/Nairobi (EAT/UTC+3)"
    echo "   - India testing: Asia/Kolkata (IST/UTC+5:30)"
    echo ""
    echo "   Set timezone with:"
    echo "   sudo timedatectl set-timezone Africa/Nairobi"
    echo ""
    echo "   Press Ctrl+C to cancel and fix timezone, or Enter to continue anyway..."
    read -r
else
    echo "✅ Timezone configured: $CURRENT_TZ"
fi
echo ""

# 2. Create backup of current production
echo "💾 Backing up current production..."
BACKUP_NAME="nfe-backup-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -d "$PROD_DIR" ]; then
    echo "📂 Production directory exists, creating backup..."
    cp -r "$PROD_DIR" "$BACKUP_DIR/$BACKUP_NAME"
    echo "✅ Backup created: $BACKUP_DIR/$BACKUP_NAME"
else
    echo "ℹ️  No existing production directory to backup (first deployment)"
fi

# 3. Stop production service (to free serial port for staging test)
echo ""
echo "🛑 Stopping production service..."
set +e  # Temporarily allow errors
sudo systemctl stop "$SERVICE_NAME" 2>&1
STOP_EXIT_CODE=$?
set -e  # Re-enable exit on error

if [ $STOP_EXIT_CODE -eq 0 ]; then
    echo "✅ Service stopped successfully"
else
    echo "⚠️  Service not running (probably first deployment)"
fi
sleep 2

# 4. Run tests in staging (now that service is stopped and port is free)
echo ""
echo "🧪 Running tests in staging...."
cd "$STAGING_DIR"
timeout 30 python3 -m src.main config/config.prod.yaml 2>&1 | head -20 &
TEST_PID=$!
sleep 30
kill $TEST_PID 2>/dev/null || true
wait $TEST_PID 2>/dev/null || true

echo "✅ Staging syntax check passed"

# 5. Sync staging to production
echo ""
echo "🔄 Syncing staging → production..."
echo "   From: $STAGING_DIR"
echo "   To:   $PROD_DIR"

# Create prod directory if it doesn't exist
mkdir -p "$PROD_DIR"
echo "✅ Production directory ready"

# First-time config sync: Copy config.prod.yaml if it doesn't exist in production
if [ ! -f "$PROD_DIR/config/config.prod.yaml" ]; then
    echo ""
    echo "📝 First-time config setup: Copying config to production..."
    mkdir -p "$PROD_DIR/config"
    cp "$STAGING_DIR/config/config.prod.yaml" "$PROD_DIR/config/config.prod.yaml"
    echo "✅ Production config created"
    echo "   NOTE: Future config changes should be made in production directory"
fi

# Rsync with delete, but PRESERVE data directory and production config
# Only copy essential runtime files: src/ and config/ (except config.prod.yaml)
rsync -av --delete \
    --exclude 'data/' \
    --exclude 'config/config.prod.yaml' \
    --exclude '*.pyc' \
    --exclude '__pycache__/' \
    --exclude '.git/' \
    --exclude '.gitignore' \
    --exclude 'backup_*' \
    --exclude '*.pdf' \
    --exclude 'docs/' \
    --exclude 'scripts/' \
    --exclude 'systemd/' \
    --exclude 'README.md' \
    --exclude 'START_HERE.md' \
    --exclude 'requirements.txt' \
    --exclude 'config/config.dev.yaml' \
    --exclude 'config/config.yaml.example' \
    "$STAGING_DIR/" "$PROD_DIR/"

echo "✅ Code synced"

# 6. Ensure data directories exist
echo ""
echo "📁 Ensuring data directories..."
mkdir -p "$PROD_DIR/data/state"
echo "✅ Data directories ready"

# 7. Start production services
echo ""
echo "🚀 Starting production services..."
sudo systemctl start "$SERVICE_NAME"
sleep 3

# Start backup timer (if backup is enabled in config)
sudo systemctl start backup.timer 2>/dev/null || true

# 8. Check service status
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✅ Meter service started successfully"
    echo ""
    echo "📊 Meter service status:"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l | head -20

    # Check backup timer status
    if sudo systemctl is-active --quiet backup.timer; then
        echo ""
        echo "📊 Backup timer status:"
        sudo systemctl list-timers backup.timer --no-pager
    fi

    echo ""
    echo "=================================================="
    echo "✅ Deployment successful!"
    echo "=================================================="
    echo ""
    echo "Monitor logs with:"
    echo "  sudo journalctl -u $SERVICE_NAME -f          # Meter service"
    echo "  sudo journalctl -u backup.service -f         # Backup service"
    echo ""
    echo "Check backup timer:"
    echo "  systemctl list-timers backup.timer"
    echo ""
    echo "Rollback with:"
    echo "  $STAGING_DIR/scripts/rollback.sh $BACKUP_NAME"
else
    echo "❌ Service failed to start!"
    echo ""
    echo "Rolling back..."

    # Rollback
    rsync -av --delete \
        --exclude 'data/' \
        "$BACKUP_DIR/$BACKUP_NAME/" "$PROD_DIR/"

    sudo systemctl start "$SERVICE_NAME"

    echo "❌ Deployment failed - rolled back to previous version"
    echo ""
    echo "Check logs:"
    echo "  sudo journalctl -u $SERVICE_NAME -n 100"
    exit 1
fi

# 9. Cleanup old backups (keep last 5)
echo ""
echo "🧹 Cleaning old backups..."
cd "$BACKUP_DIR"
ls -t | tail -n +6 | xargs -r rm -rf
echo "✅ Cleanup complete (kept last 5 backups)"
