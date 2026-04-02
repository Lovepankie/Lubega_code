# NFE Modbus Energy Logger - Deployment & Operations Guide

## Table of Contents
1. [Initial Deployment to Raspberry Pi](#initial-deployment)
2. [Production Updates (Staging → Production)](#production-updates)
3. [Log Upload Automation](#log-upload-automation)
4. [Troubleshooting](#troubleshooting)

---

## Directory Structure Philosophy

This project uses a **staging/production separation** strategy:

```
/home/nfetestpi2/
├── nfe-modbus-energy-logger/          # STAGING (git repo, testing)
├── nfe-modbus-energy-logger-prod/     # PRODUCTION (active service)
└── nfe-backups/                       # Rollback backups
```

**Why?**
- ✅ Test changes in staging before deploying
- ✅ Fast rollback from backups
- ✅ Production data never mixed with code changes
- ✅ Zero git conflicts in production

---

## Initial Deployment

### Prerequisites on Raspberry Pi
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3 and pip
sudo apt install python3 python3-pip git -y

# Install required Python packages
# Note: On newer Raspberry Pi OS, add --break-system-packages flag
sudo pip3 install pymodbus pyyaml --break-system-packages

# Install mbpoll (if using mbpoll backend)
sudo apt install mbpoll -y
```

### Step 1: Clone Repository to Pi (Staging)
```bash
# SSH into your Pi
ssh nfetestpi2@<your-pi-ip>

# Navigate to home directory
cd /home/nfetestpi2

# Clone the repository as STAGING
git clone <your-git-repo-url> nfe-modbus-energy-logger

# Navigate to staging
cd nfe-modbus-energy-logger
```

### Step 2: Initial Configuration
```bash
# Copy production config as starting point
cp config/config.prod.yaml config/config.prod.yaml.backup

# Edit production config with your settings
nano config/config.prod.yaml
```

**Important Settings to Verify:**
- `port`: Ensure `/dev/ttyUSB0` matches your RS485 adapter (check with `ls /dev/tty*`)
- `meters`: Update meter IDs and names to match your installation
- `poll_interval`: 10 seconds recommended
- `log_interval`: 900 seconds (15 minutes)

### Step 3: Test Run in Staging
```bash
# Create necessary directories
mkdir -p data/state

# Test run in foreground
python3 -m src.main config/config.prod.yaml
```

**What to Look For:**
- ✅ "Initialized meter X" messages for each enabled meter
- ✅ "Starting multi-meter logger" message
- ✅ No errors reading from meters
- ✅ After 15 minutes, you should see "📊 Meter X: Logged 15-min aggregation"

**Stop Test:** Press `Ctrl+C`

### Step 3.5: Setup Deployment Scripts
```bash
# Make deployment scripts executable
chmod +x scripts/deploy.sh
chmod +x scripts/rollback.sh
```

### Step 4: Deploy to Production (First Time)
```bash
# Run deployment script (creates prod directory and starts service)
~/nfe-modbus-energy-logger/scripts/deploy.sh
```

This script will:
1. Create `/home/nfetestpi2/nfe-modbus-energy-logger-prod/`
2. Sync code from staging
3. Create data directories
4. Start the service

### Step 4.5: Create Systemd Service (First Time Only)
```bash
# Copy service file from repo
sudo cp /home/nfetestpi2/nfe-modbus-energy-logger/systemd/meter.service \
        /etc/systemd/system/meter.service

# OR create manually
sudo nano /etc/systemd/system/meter.service
```

**Service File Content** (already in `systemd/meter.service`):
```ini
[Unit]
Description=NFE Modbus Energy Logger
After=network.target

[Service]
Type=simple
User=nfetestpi2
WorkingDirectory=/home/nfetestpi2/nfe-modbus-energy-logger-prod
ExecStart=/usr/bin/python3 -m src.main config/config.prod.yaml
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

### Step 5: Enable and Start Service
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable meter.service

# Start service
sudo systemctl start meter.service

# Check status
sudo systemctl status meter.service

# View live logs
sudo journalctl -u meter.service -f
```

### Step 6: Verify Data Collection
```bash
# Wait 15+ minutes, then check for CSV files
ls -lh data/meter_*/

# Check state files
ls -lh data/state/

# View recent log entries
tail -20 data/meter_001/meter_001_*.csv
```

---

## Production Updates (Staging → Production)

### The Proper Workflow

```
Development Machine          Raspberry Pi
    (Local Repo)
         │              ┌─────────────────────────┐
         │              │  Staging (git repo)     │
         ├─git push────▶│  Test changes here      │
         │              │  ~/nfe-modbus-...       │
         │              └───────────┬─────────────┘
         │                          │
         │           scripts/deploy.sh (rsync)
         │                          │
         │                          ▼
         │              ┌─────────────────────────┐
         │              │  Production (active)    │
         │              │  Service runs here      │
         │              │  ~/nfe-...-prod/        │
         │              └─────────────────────────┘
```

### Scenario 1: Code Changes (Bug Fixes, New Features)

#### Step 1: On Development Machine
```bash
# Make changes, test locally if possible
git add .
git commit -m "Fix: description of change"
git push origin main
```

#### Step 2: On Raspberry Pi - Update Staging
```bash
# SSH into Pi
ssh nfetestpi2@<your-pi-ip>

# Update staging from git
cd ~/nfe-modbus-energy-logger
git pull origin main
```

#### Step 3: Test in Staging (IMPORTANT!)
```bash
# Test the changes in staging
python3 -m src.main config/config.prod.yaml
# Press Ctrl+C after 30-60 seconds if it looks good
```

#### Step 4: Deploy to Production
```bash
# Run the deployment script
~/nfe-modbus-energy-logger/scripts/deploy.sh
```

The script automatically:
- ✅ Creates backup of current production
- ✅ Stops production service
- ✅ Syncs staging → production (excludes `data/` directory)
- ✅ Starts production service
- ✅ Verifies service is running
- ✅ Auto-rollback if service fails to start
- ✅ Keeps last 5 backups

#### Step 5: Monitor
```bash
# Watch logs for issues
sudo journalctl -u meter.service -f

# Check service status
sudo systemctl status meter.service
```

### If Deployment Fails

The deploy script auto-rolls back, but you can also manually rollback:

```bash
# List available backups
ls -lh ~/nfe-backups/

# Rollback to specific backup
~/nfe-modbus-energy-logger/scripts/rollback.sh nfe-backup-20260319_143052
```

### Scenario 2: Configuration Changes Only (No Code Changes)

When you only need to change config (e.g., enable a new meter):

```bash
# SSH into Pi
ssh nfetestpi2@<your-pi-ip>

# Edit PRODUCTION config directly (since no code change)
cd ~/nfe-modbus-energy-logger-prod
nano config/config.prod.yaml

# Example: Enable a new meter
# Change:
#   enabled: false
# To:
#   enabled: true

# Stop service
sudo systemctl stop meter.service

# Test the configuration
python3 -m src.main config/config.prod.yaml
# Verify new meter is initialized
# Press Ctrl+C after verification

# Start service
sudo systemctl start meter.service

# Monitor logs
sudo journalctl -u meter.service -f
```

**Note:** Config-only changes don't need the deploy script since you're not changing code.

### Scenario 3: Package Updates (e.g., pymodbus upgrade)

```bash
# SSH into Pi
ssh nfetestpi2@<your-pi-ip>

# Update packages system-wide
sudo pip3 install --upgrade pymodbus pyyaml --break-system-packages

# Test in staging
cd ~/nfe-modbus-energy-logger
python3 -m src.main config/config.prod.yaml
# Press Ctrl+C after 30 seconds

# If test passes, restart production (no deployment needed)
sudo systemctl restart meter.service

# Monitor
sudo journalctl -u meter.service -f
```

### Scenario 4: Emergency Rollback

If production is broken and you need to rollback immediately:

```bash
# List recent backups
ls -lht ~/nfe-backups/ | head -10

# Rollback to last known good version
~/nfe-modbus-energy-logger/scripts/rollback.sh nfe-backup-20260319_143052
```

The rollback script:
- ✅ Stops service
- ✅ Restores code from backup (preserves data)
- ✅ Starts service
- ✅ Verifies service is running

---

## Log Upload Automation

### Option 1: Upload to Server via SCP (Scheduled)

Create upload script:
```bash
nano /home/pi/nfe-modbus-energy-logger/scripts/upload_logs.sh
```

**Script Content:**
```bash
#!/bin/bash

# Configuration
REMOTE_USER="your-username"
REMOTE_HOST="your-server.com"
REMOTE_PATH="/path/to/upload/"
LOCAL_DATA_DIR="/home/pi/nfe-modbus-energy-logger/data"
LOG_FILE="/home/pi/nfe-modbus-energy-logger/upload.log"

# Upload only .csv.gz files (compressed archives)
echo "[$(date)] Starting log upload..." >> "$LOG_FILE"

find "$LOCAL_DATA_DIR" -name "*.csv.gz" -type f -mtime +1 | while read file; do
    echo "[$(date)] Uploading $file..." >> "$LOG_FILE"
    scp "$file" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"

    if [ $? -eq 0 ]; then
        echo "[$(date)] Success: $file" >> "$LOG_FILE"
        # Optional: Delete local copy after successful upload
        # rm "$file"
    else
        echo "[$(date)] Failed: $file" >> "$LOG_FILE"
    fi
done

echo "[$(date)] Upload complete" >> "$LOG_FILE"
```

Make executable:
```bash
chmod +x /home/pi/nfe-modbus-energy-logger/scripts/upload_logs.sh
```

Setup SSH key for passwordless SCP:
```bash
# On Pi, generate SSH key if not exists
ssh-keygen -t rsa -b 4096

# Copy public key to remote server
ssh-copy-id your-username@your-server.com
```

Schedule with cron (daily at 2 AM):
```bash
crontab -e

# Add this line:
0 2 * * * /home/pi/nfe-modbus-energy-logger/scripts/upload_logs.sh
```

### Option 2: Email Logs (Daily Summary)

Create email script:
```bash
nano /home/pi/nfe-modbus-energy-logger/scripts/email_logs.sh
```

**Script Content:**
```bash
#!/bin/bash

# Configuration
EMAIL="your-email@example.com"
SUBJECT="NFE Logger - Daily Report $(date +%Y-%m-%d)"
DATA_DIR="/home/pi/nfe-modbus-energy-logger/data"

# Create temporary directory for attachments
TEMP_DIR=$(mktemp -d)

# Copy today's CSV files
find "$DATA_DIR" -name "*$(date +%Y-%m-%d).csv" -exec cp {} "$TEMP_DIR/" \;

# Create summary
SUMMARY="$TEMP_DIR/summary.txt"
echo "NFE Modbus Energy Logger - Daily Summary" > "$SUMMARY"
echo "Date: $(date)" >> "$SUMMARY"
echo "" >> "$SUMMARY"
echo "Active Meters:" >> "$SUMMARY"
ls -lh "$DATA_DIR"/meter_*/meter_*_$(date +%Y-%m-%d).csv >> "$SUMMARY"
echo "" >> "$SUMMARY"
echo "Disk Usage:" >> "$SUMMARY"
du -sh "$DATA_DIR" >> "$SUMMARY"

# Email with attachments (requires mailutils)
if [ -z "$(ls -A $TEMP_DIR/*.csv 2>/dev/null)" ]; then
    # No CSV files, send summary only
    mail -s "$SUBJECT" "$EMAIL" < "$SUMMARY"
else
    # Send with attachments
    (
        cat "$SUMMARY"
        for file in "$TEMP_DIR"/*.csv; do
            uuencode "$file" "$(basename $file)"
        done
    ) | mail -s "$SUBJECT" "$EMAIL"
fi

# Cleanup
rm -rf "$TEMP_DIR"
```

Install mailutils:
```bash
sudo apt install mailutils -y

# Configure mail (follow prompts)
sudo dpkg-reconfigure exim4-config
```

Make executable and schedule:
```bash
chmod +x /home/pi/nfe-modbus-energy-logger/scripts/email_logs.sh

# Add to crontab (daily at 11:59 PM)
crontab -e
59 23 * * * /home/pi/nfe-modbus-energy-logger/scripts/email_logs.sh
```

### Option 3: Cloud Upload (AWS S3, Google Drive, Dropbox)

**AWS S3 Example:**

Install AWS CLI:
```bash
sudo apt install awscli -y

# Configure credentials
aws configure
```

Create upload script:
```bash
nano /home/pi/nfe-modbus-energy-logger/scripts/upload_to_s3.sh
```

**Script Content:**
```bash
#!/bin/bash

S3_BUCKET="s3://your-bucket-name/nfe-logs/"
LOCAL_DATA_DIR="/home/pi/nfe-modbus-energy-logger/data"

# Upload compressed logs to S3
aws s3 sync "$LOCAL_DATA_DIR" "$S3_BUCKET" \
    --exclude "*" \
    --include "*.csv.gz" \
    --storage-class STANDARD_IA

# Optional: Upload current day's CSV
aws s3 sync "$LOCAL_DATA_DIR" "$S3_BUCKET/current/" \
    --exclude "*" \
    --include "*$(date +%Y-%m-%d).csv"
```

Make executable and schedule:
```bash
chmod +x /home/pi/nfe-modbus-energy-logger/scripts/upload_to_s3.sh

# Add to crontab (every 6 hours)
crontab -e
0 */6 * * * /home/pi/nfe-modbus-energy-logger/scripts/upload_to_s3.sh
```

---

## Troubleshooting

### Service Won't Start
```bash
# Check service status
sudo systemctl status meter.service

# View detailed logs
sudo journalctl -u meter.service -n 100

# Common issues:
# 1. Port permissions
sudo usermod -a -G dialout pi
# Then restart Pi

# 2. Missing dependencies
pip3 install pymodbus pyyaml --break-system-packages

# 3. Config syntax errors
python3 -c "import yaml; print(yaml.safe_load(open('config/config.prod.yaml')))"
```

### No Data Being Logged
```bash
# Check if service is running
sudo systemctl status meter.service

# Check for Modbus communication errors
sudo journalctl -u meter.service -f | grep "failed"

# Test Modbus connection manually
python3 scripts/test_modbus_read.py

# Verify meter IDs in config match physical meters
```

### Disk Full
```bash
# Check disk usage
df -h

# Check data directory size
du -sh /home/pi/nfe-modbus-energy-logger/data

# Compress old logs manually
find /home/pi/nfe-modbus-energy-logger/data -name "*.csv" -mtime +7 -exec gzip {} \;

# Delete very old compressed logs (older than 1 year)
find /home/pi/nfe-modbus-energy-logger/data -name "*.csv.gz" -mtime +365 -delete
```

### Service Crashes Frequently
```bash
# View crash logs
sudo journalctl -u meter.service --since "1 hour ago"

# Increase restart delay in service file
sudo nano /etc/systemd/system/meter.service
# Change: RestartSec=10
# To:     RestartSec=30

sudo systemctl daemon-reload
sudo systemctl restart meter.service
```

### Wrong Time/Timezone
```bash
# Check current timezone
timedatectl

# Set timezone (example: Africa/Kampala)
sudo timedatectl set-timezone Africa/Kampala

# Restart service
sudo systemctl restart meter.service
```

---

## Maintenance Schedule

### Daily
- Monitor service status: `sudo systemctl status meter.service`
- Check latest log entry: `tail data/meter_001/meter_001_*.csv`

### Weekly
- Review logs for errors: `sudo journalctl -u meter.service --since "7 days ago" | grep -i error`
- Check disk usage: `df -h`

### Monthly
- Verify all meters logging correctly
- Backup data directory: `tar -czf backup_$(date +%Y%m).tar.gz data/`
- Upload backups to remote server

### Quarterly
- Update system packages: `sudo apt update && sudo apt upgrade`
- Update Python packages: `sudo pip3 install --upgrade pymodbus pyyaml --break-system-packages`
- Review and clean old logs (>1 year)

---

## Quick Reference Commands

### Deployment Operations
```bash
# Update staging from git
cd ~/nfe-modbus-energy-logger && git pull

# Test in staging
cd ~/nfe-modbus-energy-logger
python3 -m src.main config/config.prod.yaml

# Deploy staging → production
~/nfe-modbus-energy-logger/scripts/deploy.sh

# Rollback to backup
~/nfe-modbus-energy-logger/scripts/rollback.sh <backup-name>

# List backups
ls -lht ~/nfe-backups/
```

### Service Management
```bash
# Start service
sudo systemctl start meter.service

# Stop service
sudo systemctl stop meter.service

# Restart service
sudo systemctl restart meter.service

# View status
sudo systemctl status meter.service

# View live logs
sudo journalctl -u meter.service -f

# View last 100 log lines
sudo journalctl -u meter.service -n 100
```

### Data Operations
```bash
# Check data files (production)
ls -lh ~/nfe-modbus-energy-logger-prod/data/meter_*/

# Check disk space
df -h
du -sh ~/nfe-modbus-energy-logger-prod/data/

# View latest CSV entries
tail -20 ~/nfe-modbus-energy-logger-prod/data/meter_001/meter_001_*.csv
```

### Directory Structure
```bash
~/nfe-modbus-energy-logger/          # Staging (git repo)
~/nfe-modbus-energy-logger-prod/     # Production (service runs here)
~/nfe-backups/                       # Automatic backups
```
