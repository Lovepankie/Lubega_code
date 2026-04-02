#!/bin/bash

# NFE Logger Deployment Validation Script
# Run this on the Raspberry Pi AFTER deployment to verify everything is working

set -e

PROD_DIR="/home/nfetestpi2/nfe-modbus-energy-logger-prod"
SERVICE_NAME="meter.service"

echo "=================================================="
echo "NFE Logger Deployment Validation"
echo "=================================================="
echo ""

# Check 1: Production directory exists
echo "✓ Checking production directory..."
if [ -d "$PROD_DIR" ]; then
    echo "  ✅ Production directory exists: $PROD_DIR"
else
    echo "  ❌ Production directory NOT found: $PROD_DIR"
    exit 1
fi
echo ""

# Check 2: Required files exist
echo "✓ Checking required files..."
REQUIRED_FILES=(
    "$PROD_DIR/config/config.prod.yaml"
    "$PROD_DIR/src/main.py"
    "$PROD_DIR/src/meter_reader.py"
    "$PROD_DIR/src/aggregator.py"
    "$PROD_DIR/src/rotating_csv_logger.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ Found: $(basename $file)"
    else
        echo "  ❌ Missing: $file"
        exit 1
    fi
done
echo ""

# Check 3: Data directories exist
echo "✓ Checking data directories..."
if [ -d "$PROD_DIR/data" ]; then
    echo "  ✅ Data directory exists"
else
    echo "  ⚠️  Data directory not found (will be created on first run)"
fi

if [ -d "$PROD_DIR/data/state" ]; then
    echo "  ✅ State directory exists"
else
    echo "  ⚠️  State directory not found (will be created on first run)"
fi
echo ""

# Check 4: Service file installed
echo "✓ Checking systemd service..."
if [ -f "/etc/systemd/system/$SERVICE_NAME" ]; then
    echo "  ✅ Service file installed: $SERVICE_NAME"
else
    echo "  ❌ Service file NOT installed: /etc/systemd/system/$SERVICE_NAME"
    echo "  Run: sudo cp systemd/meter.service /etc/systemd/system/meter.service"
    exit 1
fi
echo ""

# Check 5: Service status
echo "✓ Checking service status..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "  ✅ Service is running"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l | head -10
else
    echo "  ❌ Service is NOT running"
    echo "  Check status: sudo systemctl status $SERVICE_NAME"
    echo "  View logs: sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi
echo ""

# Check 6: Service is enabled
echo "✓ Checking if service starts on boot..."
if systemctl is-enabled --quiet "$SERVICE_NAME"; then
    echo "  ✅ Service is enabled (will start on boot)"
else
    echo "  ⚠️  Service is NOT enabled"
    echo "  Enable with: sudo systemctl enable $SERVICE_NAME"
fi
echo ""

# Check 7: Python dependencies
echo "✓ Checking Python dependencies..."
if python3 -c "import pymodbus" 2>/dev/null; then
    echo "  ✅ pymodbus installed"
else
    echo "  ❌ pymodbus NOT installed"
    echo "  Install: pip3 install pymodbus"
    exit 1
fi

if python3 -c "import yaml" 2>/dev/null; then
    echo "  ✅ pyyaml installed"
else
    echo "  ❌ pyyaml NOT installed"
    echo "  Install: pip3 install pyyaml"
    exit 1
fi
echo ""

# Check 8: User permissions
echo "✓ Checking user permissions..."
if groups | grep -q dialout; then
    echo "  ✅ User is in dialout group (can access serial ports)"
else
    echo "  ❌ User is NOT in dialout group"
    echo "  Fix: sudo usermod -a -G dialout $(whoami)"
    echo "  Then reboot"
    exit 1
fi
echo ""

# Check 9: RS485 adapter
echo "✓ Checking RS485 adapter..."
if ls /dev/ttyUSB* 1>/dev/null 2>&1; then
    echo "  ✅ RS485 adapter found:"
    ls -l /dev/ttyUSB* | awk '{print "     " $0}'
else
    echo "  ⚠️  No /dev/ttyUSB* devices found"
    echo "  Check: ls /dev/tty*"
    echo "  Ensure RS485 adapter is connected"
fi
echo ""

# Check 10: Recent logs (last 10 lines)
echo "✓ Checking recent service logs..."
sudo journalctl -u "$SERVICE_NAME" -n 10 --no-pager
echo ""

# Check 11: Data files (if service has been running)
echo "✓ Checking for data files..."
if [ -d "$PROD_DIR/data" ]; then
    CSV_COUNT=$(find "$PROD_DIR/data" -name "*.csv" 2>/dev/null | wc -l)
    if [ "$CSV_COUNT" -gt 0 ]; then
        echo "  ✅ Found $CSV_COUNT CSV file(s):"
        find "$PROD_DIR/data" -name "*.csv" -exec ls -lh {} \; | awk '{print "     " $9 " (" $5 ")"}'
    else
        echo "  ⚠️  No CSV files yet (service may need to run for 15 minutes)"
    fi

    STATE_COUNT=$(find "$PROD_DIR/data/state" -name "*.json" 2>/dev/null | wc -l)
    if [ "$STATE_COUNT" -gt 0 ]; then
        echo "  ✅ Found $STATE_COUNT state file(s)"
    fi
else
    echo "  ⚠️  Data directory not found"
fi
echo ""

# Check 12: Backup directory
echo "✓ Checking backup directory..."
if [ -d "/home/nfetestpi2/nfe-backups" ]; then
    BACKUP_COUNT=$(ls -1 /home/nfetestpi2/nfe-backups 2>/dev/null | wc -l)
    echo "  ✅ Backup directory exists with $BACKUP_COUNT backup(s)"
else
    echo "  ⚠️  Backup directory not found (will be created on first deployment)"
fi
echo ""

# Check 13: Deployment scripts
echo "✓ Checking deployment scripts..."
if [ -f "/home/nfetestpi2/nfe-modbus-energy-logger/scripts/deploy.sh" ]; then
    echo "  ✅ deploy.sh found in staging directory"
else
    echo "  ⚠️  deploy.sh not found in staging directory"
    echo "  Scripts should be in ~/nfe-modbus-energy-logger/scripts/"
fi

if [ -f "/home/nfetestpi2/nfe-modbus-energy-logger/scripts/rollback.sh" ]; then
    echo "  ✅ rollback.sh found in staging directory"
else
    echo "  ⚠️  rollback.sh not found in staging directory"
    echo "  Scripts should be in ~/nfe-modbus-energy-logger/scripts/"
fi
echo ""

# Summary
echo "=================================================="
echo "✅ Validation Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Monitor logs: sudo journalctl -u $SERVICE_NAME -f"
echo "  2. Wait 15 minutes for first CSV log entry"
echo "  3. Check data: ls -lh $PROD_DIR/data/meter_*/"
echo ""
echo "Useful commands:"
echo "  Service status:  sudo systemctl status $SERVICE_NAME"
echo "  View logs:       sudo journalctl -u $SERVICE_NAME -f"
echo "  Restart service: sudo systemctl restart $SERVICE_NAME"
echo "  Check data:      tail -20 $PROD_DIR/data/meter_001/*.csv"
echo ""
