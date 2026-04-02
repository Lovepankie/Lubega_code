# Testing Guide - Before Production Deployment

## Quick Answers to Your Questions

### 1. "We don't have any sys log in the code" - How does journalctl work?

**Answer:** You don't need explicit syslog code! The systemd service file automatically captures all output.

**How it works:**
- Your Python code uses `print()` statements (already in the code)
- The service file has these lines:
  ```ini
  StandardOutput=journal
  StandardError=journal
  Environment="PYTHONUNBUFFERED=1"
  ```
- Systemd automatically captures:
  - All `print()` statements → sent to journalctl
  - All error messages → sent to journalctl
  - All exceptions/tracebacks → sent to journalctl

**What you'll see in journalctl:**
```bash
# Run this command:
sudo journalctl -u meter.service -f

# You'll see output like:
Mar 19 14:30:15 nfetestpi2 python3[1234]: ✅ Initialized meter 1 (main_three_phase, 3phase)
Mar 19 14:30:15 nfetestpi2 python3[1234]: 🚀 Starting multi-meter logger
Mar 19 14:30:15 nfetestpi2 python3[1234]:    Poll interval: 10s
Mar 19 14:30:15 nfetestpi2 python3[1234]:    Log interval: 900s (15 minutes)
Mar 19 14:45:20 nfetestpi2 python3[1234]: 📊 Meter 1 (main_three_phase): Logged 15-min aggregation
```

**Already in your code (src/main.py):**
```python
print(f"✅ Initialized meter {meter_id} ({meter_name}, {meter_type})")  # → journalctl
print(f"🚀 Starting multi-meter logger")                                # → journalctl
print(f"📊 Meter {meter_id} ({components['name']}): Logged 15-min...")  # → journalctl
print(f"⚠️  Meter {meter_id} ({components['name']}): Read failed...")   # → journalctl
print(f"❌ Error in main loop: {e}")                                     # → journalctl
```

**Bottom Line:** Your existing `print()` statements are already being logged. No additional logging code needed!

---

### 2. Service Name: `meter.service` is Correct

**Clarification:** I incorrectly used `nfe-logger.service` in some places. The correct name is **`meter.service`**.

**What I fixed:**
- ✅ `scripts/deploy.sh` → now uses `meter.service`
- ✅ `scripts/rollback.sh` → now uses `meter.service`
- ✅ `DEPLOYMENT.md` → all references updated to `meter.service`

**File locations:**
- Service definition: `systemd/meter.service`
- Installed location: `/etc/systemd/system/meter.service`

**Correct commands:**
```bash
sudo systemctl status meter.service
sudo journalctl -u meter.service -f
sudo systemctl restart meter.service
```

---

### 3. Log Upload Strategy - Test Core System First, Add Upload Later

**Recommendation:** Yes, deploy and test the core logging system FIRST. Add log upload as a separate service/script AFTER you confirm data collection works.

**Why?**
1. ✅ Verify meters are reading correctly
2. ✅ Confirm 15-minute aggregation works
3. ✅ Ensure CSV files are being created
4. ✅ Check energy calculations are accurate
5. **Then** add log upload once you trust the data

**Log Upload Options (already documented in DEPLOYMENT.md):**

The upload functionality should be implemented as a **separate cron job** that runs independently:

**Option 1: SCP Upload (simplest)**
```bash
# Create script: scripts/upload_logs.sh
# Schedule with cron: 0 2 * * * ~/upload_logs.sh
# Uploads compressed logs to your server via SCP
```

**Option 2: Email Daily Reports**
```bash
# Create script: scripts/email_logs.sh
# Schedule with cron: 59 23 * * * ~/email_logs.sh
# Emails today's CSV files as attachments
```

**Option 3: Cloud Upload (AWS S3, etc.)**
```bash
# Create script: scripts/upload_to_s3.sh
# Schedule with cron: 0 */6 * * * ~/upload_to_s3.sh
# Syncs logs to cloud storage
```

**Recommendation:** Start with **Option 1 (SCP)** - it's the simplest and most reliable.

**When to implement:** After 24-48 hours of successful data collection on the Pi.

---

## Testing Checklist (Run This on Pi)

### Phase 1: Initial Staging Test (5-10 minutes)
```bash
# SSH into Pi
ssh nfetestpi2@<your-pi-ip>

# Clone repo to staging
cd ~
git clone <your-repo-url> nfe-modbus-energy-logger
cd nfe-modbus-energy-logger

# Install dependencies
sudo pip3 install pymodbus pyyaml

# Create directories
mkdir -p data/state

# Edit config if needed
nano config/config.prod.yaml

# Test run in foreground
python3 -m src.main config/config.prod.yaml
```

**What to look for:**
- ✅ "Initialized meter 1" message
- ✅ "Starting multi-meter logger" message
- ✅ No error messages about port or Modbus connection
- ✅ Wait 60 seconds, press Ctrl+C

**If it looks good, proceed to Phase 2.**

---

### Phase 2: Deploy to Production (10 minutes)
```bash
# Deploy to production
~/nfe-modbus-energy-logger/scripts/deploy.sh

# Install systemd service (FIRST TIME ONLY)
sudo cp systemd/meter.service /etc/systemd/system/meter.service
sudo systemctl daemon-reload
sudo systemctl enable meter.service
sudo systemctl start meter.service

# Check status
sudo systemctl status meter.service
```

**What to look for:**
- ✅ Service shows "active (running)"
- ✅ No errors in status output

---

### Phase 3: Monitor for 15 Minutes
```bash
# Watch live logs
sudo journalctl -u meter.service -f
```

**What to look for:**
- ✅ After ~15 minutes: "📊 Meter 1: Logged 15-min aggregation"
- ✅ No repeating error messages

**Press Ctrl+C to stop watching logs.**

---

### Phase 4: Verify Data Files (After 15 minutes)
```bash
# Check production data directory
cd ~/nfe-modbus-energy-logger-prod

# List CSV files
ls -lh data/meter_001/

# View CSV content
tail -20 data/meter_001/meter_001_*.csv

# Check state files
cat data/state/meter_001_state.json
```

**What to look for:**
- ✅ CSV file exists: `meter_001_2026-03-19.csv`
- ✅ CSV has header row + at least 1 data row
- ✅ Timestamp values are correct
- ✅ Voltage, current, power values are reasonable
- ✅ State file has energy calculation values

---

### Phase 5: Monitor for 24 Hours

**Let it run for 24 hours**, checking periodically:

```bash
# Check service status
sudo systemctl status meter.service

# Check logs for errors
sudo journalctl -u meter.service --since "1 hour ago" | grep -i error

# Check disk usage
df -h

# Count rows in CSV (should be ~96 rows per day at 15-min intervals)
wc -l ~/nfe-modbus-energy-logger-prod/data/meter_001/*.csv
```

**What you should see after 24 hours:**
- ✅ ~96 rows in CSV (4 per hour × 24 hours)
- ✅ File size: ~10-15 KB
- ✅ Service still running without crashes

---

### Phase 6: Implement Log Upload (Optional, after successful 24h test)

**Only proceed here if Phase 5 is successful.**

See [DEPLOYMENT.md - Log Upload Automation](DEPLOYMENT.md#log-upload-automation) for detailed scripts.

**Recommended approach:**
1. Use SCP upload script
2. Run daily at 2 AM via cron
3. Upload compressed logs only (`.csv.gz` files)
4. Keep local copies for backup

---

## Troubleshooting

### Issue: Service fails to start
```bash
# Check detailed error
sudo journalctl -u meter.service -n 50

# Common fixes:
# 1. Port permissions
sudo usermod -a -G dialout nfetestpi2
sudo reboot

# 2. Wrong port in config
ls /dev/tty*  # Find your RS485 adapter
nano ~/nfe-modbus-energy-logger-prod/config/config.prod.yaml
```

### Issue: No data after 15 minutes
```bash
# Check if service is actually running
sudo systemctl status meter.service

# Check logs for Modbus errors
sudo journalctl -u meter.service -f | grep -i "failed"

# Test Modbus connection manually
cd ~/nfe-modbus-energy-logger
python3 scripts/test_modbus_read.py
```

### Issue: Wrong meter readings
```bash
# Verify meter IDs in config match physical meter IDs
# Check physical meter display for its Modbus address

# Edit config
nano ~/nfe-modbus-energy-logger-prod/config/config.prod.yaml

# Restart service
sudo systemctl restart meter.service
```

---

## Summary

1. **Logging to journalctl:** Already works via `print()` statements + systemd service config
2. **Service name:** `meter.service` (now corrected everywhere)
3. **Log upload:** Implement AFTER core system is tested and working for 24-48 hours

**Next Step:** Run Phase 1 testing on your Pi!
