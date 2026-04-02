# Testing on Test Pi - Complete Guide

This guide provides step-by-step instructions for testing the NFE Modbus Energy Logger on your test Raspberry Pi before deploying to production.

---

## Why Test on Test Pi First?

- **Validate functionality** before production deployment
- **Faster results** with 1-minute log intervals (vs 15 minutes in production)
- **Test billing feature** by manipulating system time
- **Safe environment** to experiment without affecting production data

---

## Test Pi Configuration

### Recommended Settings for Test Pi

Edit `config/config.prod.yaml` on your test Pi:

```yaml
port: /dev/ttyUSB0

modbus:
  backend: pymodbus

meters:
  - id: 10                        # Test single-phase meter
    name: "test_single_phase"
    type: "1phase"
    enabled: true

  # Optionally add a 3-phase meter for testing
  # - id: 100
  #   name: "test_three_phase"
  #   type: "3phase"
  #   enabled: false

poll_interval: 10                 # Poll every 10 seconds
log_interval: 60                  # ⚡ Log every 1 MINUTE for fast testing

logging:
  base_dir: data
  state_dir: data/state
  rotation:
    max_rows: 50000
    compress_old: true
```

**Key Difference from Production:**
- **`log_interval: 60`** (1 minute) instead of 900 (15 minutes)
- This means you'll see results in logs every minute instead of waiting 15 minutes
- Perfect for rapid testing and verification

---

## Step-by-Step Testing Procedure

### Step 1: Deploy to Test Pi

```bash
# SSH into test Pi
ssh nfetestpi2@<test-pi-ip>

# Clone repository (if first time)
git clone https://github.com/Nearly-Free-Energy/nfe-modbus-energy-logger.git
cd nfe-modbus-energy-logger

# Or pull latest changes (if already cloned)
cd ~/nfe-modbus-energy-logger
git pull

# Create/edit test configuration
cp config/config.yaml.example config/config.prod.yaml
nano config/config.prod.yaml
# Set log_interval: 60 (1 minute)
# Set meter ID to your test meter address (e.g., 10)

# Deploy
bash scripts/deploy.sh
```

**Expected Output:**
```
==================================================
NFE Logger Production Deployment
==================================================

🔍 Running first-time setup checks...
✅ Python dependencies already installed
✅ config.prod.yaml exists
✅ Systemd service already installed

🧪 Running tests in staging...
✅ Staging syntax check passed

💾 Backing up current production...
✅ Backup created: /home/nfetestpi2/nfe-backups/nfe-backup-20260329_150000

🛑 Stopping production service...
✅ Service stopped successfully

🔄 Syncing staging → production...
✅ Code synced
✅ Data directories ready

🚀 Starting production service...
✅ Service started successfully

==================================================
✅ Deployment successful!
==================================================
```

### Step 2: Monitor Live Logs

```bash
sudo journalctl -u meter.service -f
```

**Expected Output (within first minute):**
```
Mar 29 15:00:00 nfetestpi2 python3[1234]: ✅ Initialized meter 10 (test_single_phase, 1phase)
Mar 29 15:00:00 nfetestpi2 python3[1234]:
Mar 29 15:00:00 nfetestpi2 python3[1234]: 🚀 Starting multi-meter logger
Mar 29 15:00:00 nfetestpi2 python3[1234]:    Poll interval: 10s
Mar 29 15:00:00 nfetestpi2 python3[1234]:    Log interval: 60s (1 minutes)
Mar 29 15:00:00 nfetestpi2 python3[1234]:    Active meters: 1
Mar 29 15:00:00 nfetestpi2 python3[1234]:
Mar 29 15:01:00 nfetestpi2 python3[1234]: 📊 Meter 10 (test_single_phase): Logged 15-min aggregation
Mar 29 15:02:00 nfetestpi2 python3[1234]: 📊 Meter 10 (test_single_phase): Logged 15-min aggregation
```

**What to Look For:**
- ✅ Service starts without errors
- ✅ Meter initialization message appears
- ✅ Log entries appear **every 1 minute** (not 15)
- ✅ No "Read failed" errors

**Press Ctrl+C** to stop watching logs once verified.

### Step 3: Verify Data Files Created

```bash
# Check data directory
ls -lh ~/nfe-modbus-energy-logger-prod/data/meter_010/

# Should show CSV file
# meter_010_2026-03-29.csv
```

### Step 4: Check CSV Content

```bash
# View first 5 rows
head -5 ~/nfe-modbus-energy-logger-prod/data/meter_010/meter_010_*.csv
```

**Expected Output (single-phase meter):**
```csv
timestamp,meter_id,meter_name,V_L1,I_L1,P_total,P_L1,PF_total,frequency,energy_total,billing_marker
2026-03-29 15:01:00,10,test_single_phase,230.5,4.32,0.995,0.995,0.998,50.0,456.78,
2026-03-29 15:02:00,10,test_single_phase,230.4,4.35,1.001,1.001,0.997,50.0,456.79,
2026-03-29 15:03:00,10,test_single_phase,230.6,4.30,0.990,0.990,0.999,50.0,456.80,
```

**What to Look For:**
- ✅ Header has `billing_marker` as last column
- ✅ New row appears **every 1 minute**
- ✅ Readings look reasonable (voltage ~230V, frequency ~50Hz)
- ✅ Energy total increases gradually

### Step 5: Let It Run for 10 Minutes

```bash
# Watch row count increase
watch -n 30 'wc -l ~/nfe-modbus-energy-logger-prod/data/meter_010/meter_010_*.csv'
```

**Expected:**
- Row count increases by 1 every minute
- After 10 minutes: ~11 rows (1 header + 10 data rows)

---

## Testing the Billing Feature

The billing feature takes a snapshot at midnight on the 1st of each month. To test this without waiting for the actual date, you'll manipulate the system time.

### ⚠️ Important Notes Before Testing

1. **Only do this on test Pi** - Never on production!
2. **Billing snapshots happen in first 15 minutes** of 1st day of month
3. **Quality markers**:
   - `BILL-EXACT`: Snapshot within 1 minute of midnight
   - `BILL-APPROX`: Snapshot within 5 minutes (e.g., service restart)
   - `BILL-LATE`: Snapshot more than 5 minutes late

### Test Scenario 1: Perfect Midnight Snapshot (BILL-EXACT)

**Goal:** Service running at midnight → immediate snapshot

```bash
# Step 1: Stop the service
sudo systemctl stop meter.service

# Step 2: Disable automatic time sync
sudo timedatectl set-ntp false

# Step 3: Set time to 23:59:00 on last day of month
sudo date -s "2026-03-31 23:59:00"

# Step 4: Verify time is set
date

# Step 5: Start service and watch logs
sudo systemctl start meter.service
sudo journalctl -u meter.service -f
```

**Expected Output (when time crosses to 00:00:00):**
```
Mar 31 23:59:00 nfetestpi2 python3[1234]: 📊 Meter 10 (test_single_phase): Logged 15-min aggregation
Apr 01 00:00:10 nfetestpi2 python3[1234]:
Apr 01 00:00:10 nfetestpi2 python3[1234]: 💰 Billing snapshot triggered at 2026-04-01 00:00:10
Apr 01 00:00:10 nfetestpi2 python3[1234]: ✅ Billing snapshot for meter 10: BILL-EXACT - energy_total=456.85 kWh
Apr 01 00:01:00 nfetestpi2 python3[1234]: 📊 Meter 10 (test_single_phase): Logged 15-min aggregation
```

**Check CSV for Billing Row:**
```bash
grep "BILL-EXACT" ~/nfe-modbus-energy-logger-prod/data/meter_010/meter_010_*.csv
```

**Expected:**
```
2026-04-01 00:00:10,10,test_single_phase,230.5,4.32,0.995,0.995,0.998,50.0,456.85,BILL-EXACT
```

### Test Scenario 2: Service Restart at 00:03 (BILL-APPROX)

**Goal:** Service starts at 00:03 → still captures snapshot (approximate)

```bash
# Step 1: Set time to 00:03 on 1st of month
sudo systemctl stop meter.service
sudo date -s "2026-04-01 00:03:00"

# Step 2: Start service
sudo systemctl start meter.service
sudo journalctl -u meter.service -f
```

**Expected Output:**
```
Apr 01 00:03:00 nfetestpi2 python3[1234]:
Apr 01 00:03:00 nfetestpi2 python3[1234]: 💰 Billing snapshot triggered at 2026-04-01 00:03:15
Apr 01 00:03:00 nfetestpi2 python3[1234]: ✅ Billing snapshot for meter 10: BILL-APPROX - energy_total=456.87 kWh
```

**Check CSV:**
```bash
grep "BILL-APPROX" ~/nfe-modbus-energy-logger-prod/data/meter_010/meter_010_*.csv
```

### Test Scenario 3: Service Restart at 00:10 (BILL-LATE)

**Goal:** Service starts late (>5 min after midnight) → marked as late

```bash
# Step 1: Set time to 00:10 on 1st of month
sudo systemctl stop meter.service
sudo date -s "2026-04-01 00:10:00"

# Step 2: Start service
sudo systemctl start meter.service
sudo journalctl -u meter.service -f
```

**Expected Output:**
```
Apr 01 00:10:00 nfetestpi2 python3[1234]:
Apr 01 00:10:00 nfetestpi2 python3[1234]: 💰 Billing snapshot triggered at 2026-04-01 00:10:12
Apr 01 00:10:00 nfetestpi2 python3[1234]: ✅ Billing snapshot for meter 10: BILL-LATE - energy_total=456.90 kWh
```

**Check CSV:**
```bash
grep "BILL-LATE" ~/nfe-modbus-energy-logger-prod/data/meter_010/meter_010_*.csv
```

### Test Scenario 4: Already Logged This Month (No Duplicate)

**Goal:** Billing snapshot only happens once per month

```bash
# Service already took snapshot at 00:00
# If you restart at 00:05 same month → NO new snapshot

sudo systemctl stop meter.service
sudo date -s "2026-04-01 00:05:00"
sudo systemctl start meter.service
sudo journalctl -u meter.service -f
```

**Expected Output:**
```
Apr 01 00:05:00 nfetestpi2 python3[1234]: ✅ Initialized meter 10 (test_single_phase, 1phase)
Apr 01 00:05:00 nfetestpi2 python3[1234]: 🚀 Starting multi-meter logger
Apr 01 00:06:00 nfetestpi2 python3[1234]: 📊 Meter 10 (test_single_phase): Logged 15-min aggregation
```

**Note:** No `💰 Billing snapshot triggered` message because snapshot already taken this month.

### Restore Normal Time After Testing

```bash
# Step 1: Stop service
sudo systemctl stop meter.service

# Step 2: Re-enable automatic time sync
sudo timedatectl set-ntp true

# Step 3: Wait for time to sync (usually instant)
sleep 5

# Step 4: Verify correct time
date

# Step 5: Start service
sudo systemctl start meter.service

# Step 6: Monitor to ensure normal operation
sudo journalctl -u meter.service -f
```

**Expected Output:**
```
Mar 29 15:30:00 nfetestpi2 python3[1234]: ✅ Initialized meter 10 (test_single_phase, 1phase)
Mar 29 15:30:00 nfetestpi2 python3[1234]: 🚀 Starting multi-meter logger
Mar 29 15:31:00 nfetestpi2 python3[1234]: 📊 Meter 10 (test_single_phase): Logged 15-min aggregation
```

---

## Complete Test Checklist

Use this checklist to verify everything works:

### Basic Functionality
- [ ] Service deploys without errors
- [ ] Service starts successfully
- [ ] Meter initialization appears in logs
- [ ] CSV file created in correct directory
- [ ] CSV header has all expected columns including `billing_marker`
- [ ] New rows appear every 1 minute
- [ ] Voltage readings look reasonable (~230V)
- [ ] Frequency is ~50Hz (or ~60Hz for US)
- [ ] Energy total increases gradually
- [ ] No "Read failed" errors in logs

### Billing Feature Testing
- [ ] Test Scenario 1: BILL-EXACT marker appears at midnight
- [ ] Test Scenario 2: BILL-APPROX marker for restart at 00:03
- [ ] Test Scenario 3: BILL-LATE marker for restart at 00:10
- [ ] Test Scenario 4: No duplicate snapshots same month
- [ ] Billing rows have actual meter readings (not zeros)
- [ ] Normal 1-minute logs have empty billing_marker field

### Time Restoration
- [ ] NTP time sync re-enabled
- [ ] System time is correct
- [ ] Service running normally after time reset

---

## Common Testing Issues

### "No response from meter" errors

**Symptoms:**
```
⚠️  Meter 10 (test_single_phase): Read failed, skipping...
```

**Possible Causes:**
1. Wrong meter ID in config (doesn't match physical meter address)
2. RS485 wiring issue (A+/B- reversed)
3. Meter not powered
4. Address conflict (another meter at same address)

**Solution:**
```bash
# Test meter communication
cd ~/nfe-modbus-energy-logger
python3 scripts/test_modbus_read.py
```

### Billing snapshot not triggered

**Symptoms:** Time passes 00:00 but no `💰 Billing snapshot triggered` message

**Possible Causes:**
1. Not the 1st day of month (check with `date`)
2. Past the 15-minute window (00:00-00:14 only)
3. Already logged this month (check last_billing_check)

**Solution:**
```bash
# Verify current date
date

# Restart service to reset billing check
sudo systemctl restart meter.service
```

### CSV missing billing_marker column

**Symptoms:** Old CSV doesn't have billing_marker column

**Solution:** This is expected for files created before the upgrade. Schema versioning will force rotation to new file with new column on next restart.

---

## Moving to Production

Once all tests pass on test Pi:

### Step 1: Update Production Config

```bash
# SSH into production Pi
ssh nfetestpi2@<production-pi-ip>

cd ~/nfe-modbus-energy-logger
nano config/config.prod.yaml
```

**Change log_interval back to 15 minutes:**
```yaml
log_interval: 900              # 15 minutes for production
```

**Update meter IDs to production addresses:**
```yaml
meters:
  - id: 100                    # Production three-phase meter
    name: "main_three_phase"
    type: "3phase"
    enabled: true

  - id: 10                     # Production single-phase meter (if any)
    name: "customer_single_phase"
    type: "1phase"
    enabled: true
```

### Step 2: Deploy to Production

```bash
cd ~/nfe-modbus-energy-logger
bash scripts/deploy.sh
```

### Step 3: Monitor Production

```bash
sudo journalctl -u meter.service -f
```

**Wait 15 minutes for first log entry to confirm everything works.**

### Step 4: Verify Production Data

```bash
# Check data files after 15 minutes
ls -lh ~/nfe-modbus-energy-logger-prod/data/meter_*/

# Check CSV content
head -3 ~/nfe-modbus-energy-logger-prod/data/meter_100/meter_100_*.csv
```

---

## Quick Command Reference

### Monitoring
```bash
# Live logs
sudo journalctl -u meter.service -f

# Last 50 log entries
sudo journalctl -u meter.service -n 50

# Service status
sudo systemctl status meter.service

# Check CSV files
ls -lh ~/nfe-modbus-energy-logger-prod/data/meter_*/
head -10 ~/nfe-modbus-energy-logger-prod/data/meter_010/*.csv
```

### Time Manipulation (Test Pi Only!)
```bash
# Stop service
sudo systemctl stop meter.service

# Disable NTP
sudo timedatectl set-ntp false

# Set time
sudo date -s "2026-03-31 23:59:00"

# Verify
date

# Start service
sudo systemctl start meter.service

# Re-enable NTP when done
sudo timedatectl set-ntp true
```

### Debugging
```bash
# Test meter communication
cd ~/nfe-modbus-energy-logger
python3 scripts/test_modbus_read.py

# Test configuration
python3 -m src.main config/config.prod.yaml
# Press Ctrl+C after 30 seconds

# Check service errors
sudo journalctl -u meter.service | grep -i "error\|failed"
```

---

## Success Criteria

Your test is successful when:

1. ✅ Service runs continuously without crashes
2. ✅ New CSV rows appear every 1 minute (test) or 15 minutes (production)
3. ✅ Meter readings are accurate (match physical meter display)
4. ✅ Energy total increases steadily
5. ✅ Billing snapshots work correctly (all 3 scenarios tested)
6. ✅ No communication errors in logs
7. ✅ CSV files have correct format with billing_marker column

Once all criteria are met, you're ready for production deployment!

---

## Need Help?

1. Check [TESTING_GUIDE.md](TESTING_GUIDE.md) for additional troubleshooting
2. Review logs: `sudo journalctl -u meter.service -n 100`
3. Test meter individually: `python3 scripts/test_modbus_read.py`
4. Check [ADDING_METERS.md](ADDING_METERS.md) if meter communication fails
