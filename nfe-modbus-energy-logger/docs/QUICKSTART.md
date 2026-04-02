# NFE Modbus Energy Logger - Quick Start Guide

**For New Team Members & Collaborators**

This guide will get you from zero to a fully operational energy logging system on a Raspberry Pi. Everything you need is documented here - no prior knowledge required.

---

## 📚 Documentation Overview

This project has three main guides:

1. **QUICKSTART.md** (this file) - Start here! Overview and step-by-step deployment
2. **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Detailed testing procedures before production
3. **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment, updates, rollback, log upload
4. **[README.md](README.md)** - Technical details, architecture, register maps

---

## 🎯 What You're Building

A multi-meter energy logging system that:
- Reads from Chint DDSU666 three-phase and single-phase meters via Modbus RTU
- Logs data every 15 minutes (polls every 10 seconds for accuracy)
- Automatically rotates and compresses log files
- Runs as a systemd service on Raspberry Pi
- Separates staging (development) from production code

**Expected Disk Usage:** ~13-14 MB per year for 3 meters (99% reduction vs continuous logging)

---

## 📋 Prerequisites Checklist

### Hardware
- [ ] Raspberry Pi (3B+ or newer recommended)
- [ ] MicroSD card (16GB+ recommended)
- [ ] RS485 to USB adapter
- [ ] Chint DDSU666 meter(s) connected via RS485
- [ ] Power supply for Raspberry Pi
- [ ] Network connection (WiFi or Ethernet)

### Software (will be installed in Step 2)
- [ ] Raspberry Pi OS (Debian-based)
- [ ] Python 3.7+
- [ ] Git
- [ ] SSH access enabled

### Information You'll Need
- [ ] Raspberry Pi IP address
- [ ] Raspberry Pi username (default: `pi`, or your custom username)
- [ ] Git repository URL (where this code is hosted)
- [ ] Meter IDs (physical Modbus addresses configured on your meters)
- [ ] RS485 adapter device path (usually `/dev/ttyUSB0`)

---

## 🚀 Complete Deployment Steps

### Step 1: Initial Raspberry Pi Setup

**On your Raspberry Pi:**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install python3 python3-pip git -y

# Install mbpoll (optional, for mbpoll backend)
sudo apt install mbpoll -y

# Add your user to dialout group (for serial port access)
sudo usermod -a -G dialout $(whoami)

# Set timezone (CRITICAL for accurate billing timestamps)
# For Kenya deployment:
sudo timedatectl set-timezone Africa/Nairobi
# For India/testing:
# sudo timedatectl set-timezone Asia/Kolkata

# Verify timezone is set correctly
timedatectl

# Reboot to apply group changes
sudo reboot
```

**Wait for Pi to reboot, then SSH back in.**

---

### Step 2: Clone Repository & Install Dependencies

```bash
# SSH into your Pi (replace YOUR_USERNAME with your actual username)
ssh YOUR_USERNAME@<your-pi-ip>

# Navigate to home directory
cd ~

# Clone repository as STAGING
git clone <your-git-repo-url> nfe-modbus-energy-logger

# Navigate to staging
cd nfe-modbus-energy-logger

# Install Python dependencies
# Note: On newer Raspberry Pi OS, you need --break-system-packages flag
pip3 install -r requirements.txt --break-system-packages

# Verify installation
python3 -c "import pymodbus, yaml; print('✅ Dependencies installed')"
```

**Note:** You may see a warning about PATH when installing. This is safe to ignore - the packages are installed correctly and will work with the systemd service.

---

### Step 3: Configure for Your Setup

```bash
# Create production config from example
cp config/config.yaml.example config/config.prod.yaml

# Edit production config
nano config/config.prod.yaml
```

**Note:** `config.prod.yaml` is gitignored (site-specific), so you create it from the example template.

**Key settings to verify/change:**

```yaml
port: /dev/ttyUSB0  # ← Verify this matches your RS485 adapter

modbus:
  backend: pymodbus  # ← Use 'pymodbus' for production (more reliable)

meters:
  - id: 1                      # ← Meter's Modbus address
    name: "main_three_phase"   # ← Descriptive name
    type: "3phase"             # ← Meter type: "3phase" or "1phase"
    enabled: true              # ← Set to true to activate

poll_interval: 10     # ← Read meters every 10 seconds (don't change)
log_interval: 900     # ← Write to CSV every 15 minutes (don't change)

logging:
  base_dir: data
  state_dir: data/state
  log_calculated_energy: true  # ← Log calculated energy for 3-phase meters
                               #   Set to false to leave E_L1_cal, E_L2_cal, E_L3_cal blank
```

**To find your RS485 adapter path:**
```bash
ls /dev/tty*
# Look for /dev/ttyUSB0, /dev/ttyUSB1, etc.
```

**Save and exit:** Press `Ctrl+X`, then `Y`, then `Enter`

---

### Step 4: Test in Staging (CRITICAL - Don't Skip!)

```bash
# Create necessary directories
mkdir -p data/state

# Test run in foreground
python3 -m src.main config/config.prod.yaml
```

**What you should see:**
```
✅ Initialized meter 1 (main_three_phase, 3phase)

🚀 Starting multi-meter logger
   Poll interval: 10s
   Log interval: 900s (15 minutes)
   Active meters: 1
```

**Let it run for 60 seconds.** You should see no errors.

**Stop the test:** Press `Ctrl+C`

**If you see errors:**
- Port permission errors → Check you added user to `dialout` group and rebooted
- Modbus read errors → Verify meter IDs and RS485 connection
- Import errors → Check Python dependencies installed correctly

---

### Step 5: Deploy to Production (First Time)

```bash
# Run deployment script from staging repo
~/nfe-modbus-energy-logger/scripts/deploy.sh
```

**On first deployment, this script automatically:**
1. Checks Python dependencies and installs if missing
2. Creates `config/config.prod.yaml` from template if missing (in staging)
3. **Installs systemd service** (auto-configured for your username)
4. Creates `~/nfe-modbus-energy-logger-prod/` directory
5. Syncs code from staging → production
6. Copies config.prod.yaml to production (first-time only)
7. Creates backup directory (`~/nfe-backups/`)
8. Starts the service

**Note:** The script detects first-time deployment and handles all setup automatically, including systemd service installation with your correct username and paths. The config file is copied to production once and then preserved on all future deployments.

---

### Step 6: Verify Service is Running

```bash
# Check service status
sudo systemctl status meter.service
```

**What you should see:**
```
● meter.service - NFE Modbus Energy Logger
   Loaded: loaded (/etc/systemd/system/meter.service; enabled)
   Active: active (running) since ...
```

**If status shows "failed":**
```bash
# View detailed error logs
sudo journalctl -u meter.service -n 50
```

---

### Step 7: Monitor Live Logs (15 minutes)

```bash
# Watch live logs
sudo journalctl -u meter.service -f
```

**What you should see:**
```
Mar 19 14:30:15 python3[1234]: ✅ Initialized meter 1 (main_three_phase, 3phase)
Mar 19 14:30:15 python3[1234]: 🚀 Starting multi-meter logger
Mar 19 14:30:15 python3[1234]:    Poll interval: 10s
Mar 19 14:30:15 python3[1234]:    Log interval: 900s (15 minutes)

[... 15 minutes later ...]

Mar 19 14:45:20 python3[1234]: 📊 Meter 1 (main_three_phase): Logged 15-min aggregation
```

**Press `Ctrl+C` to stop watching logs.**

---

### Step 8: Verify Data Collection

```bash
# Wait 15+ minutes after service start, then check for CSV files
ls -lh ~/nfe-modbus-energy-logger-prod/data/meter_001/

# You should see:
# meter_001_2026-03-19.csv

# View CSV content
tail -20 ~/nfe-modbus-energy-logger-prod/data/meter_001/meter_001_*.csv

# Check state files
cat ~/nfe-modbus-energy-logger-prod/data/state/meter_001_state.json
```

**Expected CSV format:**
```
timestamp,meter_id,meter_name,V_L1_V,V_L2_V,V_L3_V,I_L1_A,I_L2_A,I_L3_A,P_total_kW,...
2026-03-29 04:15:00,1,main_three_phase,230.5,231.2,229.8,12.3,11.8,12.1,8.45,...
```

**Note:** Timestamps are in `YYYY-MM-DD HH:MM:SS` format using the Pi's local timezone (EAT for Kenya, IST for India testing)

**CSV Columns for Three-Phase Meters:**
- `timestamp` - Log timestamp (YYYY-MM-DD HH:MM:SS)
- `meter_id` - Modbus address
- `meter_name` - Descriptive name
- `V_L1_V`, `V_L2_V`, `V_L3_V` - Phase voltages (Volts)
- `I_L1_A`, `I_L2_A`, `I_L3_A` - Phase currents (Amps)
- `P_total_kW`, `P_L1_kW`, `P_L2_kW`, `P_L3_kW` - Power (kW)
- `PF_total` - Power factor
- `frequency_Hz` - Frequency (Hz)
- `energy_total_kWh` - Cumulative energy from meter (kWh)
- `E_L1_cal_kWh`, `E_L2_cal_kWh`, `E_L3_cal_kWh` - Calculated energy per phase (kWh)
- `billing_marker` - Special marker for monthly billing snapshots

**Calculated Energy Columns (`E_L1_cal`, `E_L2_cal`, `E_L3_cal`):**

For three-phase meters, the system calculates energy consumption per phase by integrating power over time. This is useful for:
- Understanding load distribution across phases
- Detecting phase imbalance
- Detailed energy analysis per phase

**To disable logging calculated energy** (columns will be blank but calculation still happens internally):
```yaml
logging:
  log_calculated_energy: false  # Set to false to leave calculated energy columns blank
```

**When to disable:**
- You only need total energy from the meter (`energy_total_kWh`)
- You want to reduce CSV file size slightly
- You don't need per-phase energy breakdown

**CSV Columns for Single-Phase Meters:**
- Same format but only `V_L1_V`, `I_L1_A`, `P_total_kW`, `P_L1_kW` (no L2/L3)
- No calculated energy columns (meter's `energy_total_kWh` is sufficient)

---

### Step 9: Let It Run for 24 Hours

**Monitor periodically:**

```bash
# Check service is still running
sudo systemctl status meter.service

# Check for errors
sudo journalctl -u meter.service --since "1 hour ago" | grep -i error

# Check disk usage
df -h

# Count CSV rows (should be ~96 rows per day)
wc -l ~/nfe-modbus-energy-logger-prod/data/meter_001/*.csv
```

**After 24 hours, you should see:**
- ✅ ~96 rows in CSV file (4 per hour × 24 hours)
- ✅ File size: ~10-15 KB
- ✅ Service running without crashes
- ✅ No error messages in logs

---

## ✅ You're Done! System is Operational

**What happens now:**
- Service runs automatically on boot
- Data is logged every 15 minutes
- Logs rotate at 50,000 rows (~17 months)
- Old logs are compressed with gzip
- Backups are created on every deployment

---

## 🔄 Making Updates Later

### Scenario 1: Code Updates (Bug Fixes, New Features)

```bash
# On your development machine
git add .
git commit -m "Fix: description"
git push origin main

# On Raspberry Pi - Update staging
ssh YOUR_USERNAME@<your-pi-ip>
cd ~/nfe-modbus-energy-logger
git pull origin main

# Stop production service (required to test in staging - serial port can only be used by one process)
sudo systemctl stop meter.service

# Test in staging
python3 -m src.main config/config.prod.yaml
# Press Ctrl+C after 30 seconds if it looks good

# Deploy to production
~/nfe-modbus-energy-logger/scripts/deploy.sh

# Monitor
sudo journalctl -u meter.service -f
```

**The deploy script automatically:**
- ✅ Backs up current production
- ✅ Stops service
- ✅ Syncs staging → production
- ✅ Starts service
- ✅ Auto-rollback if service fails

---

### Scenario 2: Configuration Changes (Enable New Meter)

**Important**: Always edit the **production** config for operational changes. The config file is read once at service startup and is NOT synced during deployments (your changes are preserved).

```bash
# Edit production config directly
ssh YOUR_USERNAME@<your-pi-ip>
cd ~/nfe-modbus-energy-logger-prod
nano config/config.prod.yaml

# Change: enabled: false → enabled: true

# Restart service (required - config is only read at startup)
sudo systemctl restart meter.service

# Monitor
sudo journalctl -u meter.service -f
```

**Note**:
- Config is read **once** at service startup, not dynamically
- Config changes require service restart to take effect
- Config is **NOT** synced during deployments - your production config is preserved
- Only edit staging config if you need to test before deploying a code change

---

### Scenario 3: Emergency Rollback

```bash
# List available backups
ls -lht ~/nfe-backups/

# Rollback to specific backup
~/nfe-modbus-energy-logger/scripts/rollback.sh nfe-backup-20260319_143052
```

---

## 📤 Setting Up Log Upload (Optional)

**After the system runs successfully for 24-48 hours**, you can setup automatic log upload.

See **[DEPLOYMENT.md - Log Upload Automation](DEPLOYMENT.md#log-upload-automation)** for three options:

1. **SCP Upload** (recommended) - Upload to your server via SSH
2. **Email Reports** - Daily email with CSV attachments
3. **Cloud Upload** - Sync to AWS S3, Google Drive, etc.

---

## 🆘 Troubleshooting

### Service won't start
```bash
# Check detailed logs
sudo journalctl -u meter.service -n 100

# Common fixes:
# 1. Port permissions
sudo usermod -a -G dialout $(whoami)
sudo reboot

# 2. Wrong port
ls /dev/tty*  # Find correct port
nano ~/nfe-modbus-energy-logger-prod/config/config.prod.yaml
sudo systemctl restart meter.service
```

### No data after 15 minutes
```bash
# Check if service is running
sudo systemctl status meter.service

# Check logs for Modbus errors
sudo journalctl -u meter.service | grep -i "failed"

# Test Modbus connection manually
cd ~/nfe-modbus-energy-logger
python3 scripts/test_modbus_read.py
```

### Wrong meter readings
```bash
# Verify meter IDs match physical meters
# Check meter display for Modbus address

# Edit config
nano ~/nfe-modbus-energy-logger-prod/config/config.prod.yaml
sudo systemctl restart meter.service
```

---

## 📞 Getting Help

1. **Check logs first:**
   ```bash
   sudo journalctl -u meter.service -n 100
   ```

2. **Review troubleshooting guides:**
   - [TESTING_GUIDE.md - Troubleshooting](TESTING_GUIDE.md#troubleshooting)
   - [DEPLOYMENT.md - Troubleshooting](DEPLOYMENT.md#troubleshooting)

3. **Test Modbus connection:**
   ```bash
   cd ~/nfe-modbus-energy-logger
   python3 scripts/test_modbus_read.py
   ```

---

## 📂 File Locations Reference

```
~/  (your home directory)
├── nfe-modbus-energy-logger/          # STAGING (git repo, testing)
│   ├── config/config.prod.yaml        # Initial config template (copied once to prod)
│   ├── scripts/                       # Deployment scripts
│   └── src/                           # Source code
│
├── nfe-modbus-energy-logger-prod/     # PRODUCTION (service runs here)
│   ├── config/config.prod.yaml        # Active config (EDIT THIS for changes)
│   ├── data/
│   │   ├── meter_001/                 # CSV files for meter 1
│   │   │   ├── meter_001_2026-03-19.csv
│   │   │   └── meter_001_2026-03-18.csv.gz
│   │   └── state/                     # Energy calculation state
│   │       └── meter_001_state.json
│   └── src/                           # Running code
│
├── nfe-backups/                       # Automatic backups
│   ├── nfe-backup-20260319_143052/
│   └── nfe-backup-20260319_120000/
│
├── deploy.sh                          # Deployment script
└── rollback.sh                        # Rollback script

/etc/systemd/system/
└── meter.service                      # Systemd service definition
```

---

## 🎓 Understanding the System

### How Logging Works

1. **Polling (every 10 seconds):**
   - Reads voltage, current, power from meter via Modbus
   - Updates energy calculations (three-phase only)
   - Buffers data in memory

2. **Logging (every 15 minutes):**
   - Averages buffered readings (voltage, current, power factor, frequency)
   - Uses final energy calculation values
   - Writes single row to CSV file
   - Clears buffer and starts new 15-minute window

3. **Rotation (at 50,000 rows):**
   - Closes current CSV file
   - Compresses old file with gzip
   - Creates new CSV file
   - Continues logging

### Why Staging + Production?

- **Staging directory:** Where you test changes safely
- **Production directory:** Where the service runs (never touch git here)
- **Deploy script:** Safely syncs staging → production with automatic backup
- **Rollback script:** Quickly restore from backup if something breaks

### Why 15-Minute Aggregation?

- **Reduces disk usage by 99%** (96 rows/day vs 43,200 rows/day)
- **Still accurate** - polls every 10 seconds for energy integration
- **Industry standard** - 15-minute intervals used in grid monitoring
- **File size:** ~10 KB/day vs 5 MB/day with continuous logging

### Resource Usage & Scaling

#### Single Meter (Typical Setup)
- **RAM**: ~18 KB buffer per meter (~40-50 MB total with Python overhead)
- **CPU**: <5% on Raspberry Pi 3B+
- **Disk**: ~11-19 KB/day per meter (~4-7 MB/year compressed)

#### Multi-Meter Setup (30 Single-Phase + 1 Three-Phase)
- **RAM**: ~558 KB for buffers (31 meters × 18 KB) - negligible
- **CPU**: <5% (minimal overhead for 31 meters)
- **Disk**: ~364 KB/day, ~133 MB/year compressed
- **Serial Port**: **This is the bottleneck!**

**Critical: Poll Interval Adjustment**

With many meters, the RS485 serial bus becomes the limiting factor:

| Meters | Read Time per Meter | Total Cycle Time | Recommended poll_interval |
|--------|-------------------|------------------|--------------------------|
| 1-3 | 0.6-1.2s | 1-4s | 10s (default) ✅ |
| 5-10 | 0.6-1.2s | 5-12s | 15s |
| 15-20 | 0.6-1.2s | 10-24s | 30s |
| 25-35 | 0.6-1.2s | 15-42s | 40-45s |

**Why adjust poll_interval?**
- Each meter takes 0.6-1.2 seconds to read (6 Modbus register reads)
- If total read time > poll_interval, readings will overlap and timeout
- Slower polling reduces samples per 15-min window but maintains accuracy

**Example config for 31 meters:**
```yaml
poll_interval: 40     # Allow time to read all 31 meters
log_interval: 900     # Keep 15-minute aggregation
```

This gives:
- ~22 samples per 15-minute window (vs 90 with default 10s polling)
- Still excellent averaging and noise reduction
- Reliable Modbus communication without timeouts
- Same 99% disk savings

**Disk Usage Comparison (31 Meters, 1 Year):**

| Approach | Rows/Day | Disk/Day | Disk/Year | Savings |
|----------|----------|----------|-----------|---------|
| Continuous (10s) | 259,200 | 31.7 MB | 11.6 GB | - |
| Aggregated (15min) | 2,976 | 364 KB | 133 MB | 99% |

**Bottom line:** The aggregation strategy scales excellently. RAM and CPU are never concerns. Only the serial bus speed limits how many meters you can connect to one Pi.

---

## ✨ Next Steps

Once your system is running:

1. ✅ Monitor for 24-48 hours to ensure stability
2. ✅ Set up log upload (SCP, email, or cloud)
3. ✅ Enable additional meters if needed
4. ✅ Schedule regular backups
5. ✅ Document your specific meter configuration for team

**Congratulations! You now have a production energy logging system running independently on your Raspberry Pi.**
