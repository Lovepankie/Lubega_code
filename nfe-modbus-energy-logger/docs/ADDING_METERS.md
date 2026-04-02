# Adding New Meters

This guide walks you through adding a new energy meter to your NFE Modbus Energy Logger system.

---

## Overview

The system supports multiple Chint DDSU666 energy meters (both three-phase and single-phase) connected via RS485 Modbus RTU. Each meter must have a unique Modbus address.

---

## Before You Start

### Understand Meter Types

**Three-Phase Meters (DTSU666/DDSU666 3-phase)**
- Measures 3 phases independently (L1, L2, L3)
- Voltage, current, power per phase
- Requires calculated energy per phase (trapezoidal integration)
- Use meter IDs **100+** (e.g., 100, 101, 102)

**Single-Phase Meters (DDSU666 1-phase)**
- Measures single phase (L1 only)
- Uses meter's built-in cumulative energy register
- Use meter IDs **10-99** (e.g., 10, 11, 12)

### Addressing Scheme

| Meter Type | ID Range | Example IDs | Purpose |
|------------|----------|-------------|---------|
| Single-phase | 10-99 | 10, 11, 12 | Room for 90 single-phase meters |
| Three-phase | 100+ | 100, 101, 102 | High addresses to avoid conflicts |

---

## ⚠️ CRITICAL: Never Use Address 1

**NEVER set a meter to Modbus address 1.**

### Why This Is Critical

1. **Factory Default Address**: When you convert a meter from the Chinese 645 protocol to Modbus using the address changer tool, the meter resets to **address 1 by default**
2. **Address Conflicts**: If you have a meter set to address 1 and add a new meter (also at address 1), both meters will respond simultaneously, causing:
   - Garbled/corrupted Modbus responses
   - Intermittent communication failures
   - Data from the wrong meter
   - Extremely difficult to diagnose
3. **Hard to Fix**: You can't read a meter's current address if there's a conflict on the bus

### Safe Address Strategy

- Single-phase: Start at **10** (not 1)
- Three-phase: Start at **100** (not 1)
- Keep a written record of assigned addresses
- Test each meter individually after setting its address

---

## Step 1: Physical Installation

### 1.1 Set Meter Modbus Address

**Before connecting the meter to the RS485 bus:**

1. Use the Chint address changer tool to convert from 645 protocol to Modbus
2. **Immediately set a unique address** (10+ for single-phase, 100+ for three-phase)
3. **Never leave it at address 1**
4. Write down the meter's address on a label and attach it to the meter

**Example: Setting address to 10**
- Use address changer tool as per Chint manual
- Set protocol: Modbus RTU
- Set address: 10 (or your chosen unique address)
- Set baud rate: 9600 (default)
- Set parity: None (or Even, match your existing meters)

### 1.2 Verify Meter Type

Look at the meter's model number:
- **DDSU666 (single-phase)**: 2 terminals (L, N)
- **DTSU666 or DDSU666 3-phase**: 4 terminals (L1, L2, L3, N)

### 1.3 Connect to RS485 Bus

**Wiring:**
```
Raspberry Pi RS485 USB Adapter
    ├── A+ (yellow/green)
    └── B- (white/blue)
        │
        ├── Meter 1 (A+, B-)
        ├── Meter 2 (A+, B-)
        └── Meter 3 (A+, B-)
```

**Important:**
- Use twisted pair cable for A+/B-
- Keep RS485 cable runs under 1000m total
- Add 120Ω termination resistors at both ends if cable is long (>30m)

---

## Step 2: Test Communication

**Before adding to production config, test the meter individually.**

### 2.1 Find the Test Script

```bash
cd ~/nfe-modbus-energy-logger
ls scripts/test_modbus_read.py
```

### 2.2 Edit Test Script (if needed)

The script hardcodes meter ID and type. Edit to match your new meter:

```bash
nano scripts/test_modbus_read.py
```

Change:
```python
METER_ID = 10        # Your new meter's address
METER_TYPE = '1phase'  # or '3phase'
```

### 2.3 Run Test

```bash
python3 scripts/test_modbus_read.py
```

**Expected Output (single-phase example):**
```
Reading from meter 10 (type: 1phase)
✅ Success:
  V_L1: 230.5 V
  I_L1: 4.32 A
  P_total: 0.995 kW
  PF_total: 0.998
  frequency: 50.0 Hz
  energy_total: 456.78 kWh
```

**Expected Output (three-phase example):**
```
Reading from meter 100 (type: 3phase)
✅ Success:
  V_L1: 230.5 V, V_L2: 231.2 V, V_L3: 229.8 V
  I_L1: 12.3 A, I_L2: 11.8 A, I_L3: 12.1 A
  P_total: 8.45 kW (P_L1: 2.8, P_L2: 2.9, P_L3: 2.75)
  PF_total: 0.95
  frequency: 50.0 Hz
  energy_total: 1234.56 kWh
```

### 2.4 Troubleshooting Test Failures

**"No response from meter" / Timeout errors:**
- Check RS485 wiring (A+ and B- reversed?)
- Verify meter address matches test script
- Ensure meter has power
- Check if another meter is using the same address (address conflict)

**"Wrong number of registers" / Parsing errors:**
- Verify meter type in script matches physical meter (1phase vs 3phase)
- Check meter model number

**Garbled/inconsistent readings:**
- Possible address conflict (another meter at same address)
- Check RS485 termination resistors if cable is long

---

## Step 3: Add to Configuration

### 3.1 Edit Staging Config

**Important:** Always edit the **staging** config first, then deploy to production.

```bash
cd ~/nfe-modbus-energy-logger
nano config/config.prod.yaml
```

### 3.2 Add Meter Entry

**For single-phase meter (ID 10):**
```yaml
meters:
  - id: 100
    name: "main_three_phase"
    type: "3phase"
    enabled: true

  - id: 10
    name: "office_single_phase"   # Give it a descriptive name
    type: "1phase"
    enabled: true                  # Set to true to enable
```

**For three-phase meter (ID 101):**
```yaml
meters:
  - id: 100
    name: "main_three_phase"
    type: "3phase"
    enabled: true

  - id: 101
    name: "backup_three_phase"    # Give it a descriptive name
    type: "3phase"
    enabled: true                  # Set to true to enable
```

**Naming Conventions:**
- Use descriptive names: `office_single_phase`, `main_building_3phase`, `backup_generator`
- No spaces (use underscores)
- Lowercase preferred
- Name appears in CSV files and logs

### 3.3 Test in Staging

Before deploying to production, test in staging:

```bash
cd ~/nfe-modbus-energy-logger
python3 -m src.main config/config.prod.yaml
```

**Expected Output:**
```
✅ Initialized meter 100 (main_three_phase, 3phase)
✅ Initialized meter 10 (office_single_phase, 1phase)

🚀 Starting multi-meter logger
   Poll interval: 10s
   Log interval: 900s (15 minutes)
   Active meters: 2
```

Watch for errors. Press **Ctrl+C** after 30 seconds if all looks good.

---

## Step 4: Deploy to Production

### 4.1 Run Deployment Script

```bash
cd ~/nfe-modbus-energy-logger
bash scripts/deploy.sh
```

The script will:
1. Test staging configuration
2. Create backup of current production
3. Sync code and config to production runtime
4. Restart service with new configuration
5. Verify service started successfully

### 4.2 Monitor Service

```bash
sudo journalctl -u meter.service -f
```

**Look for:**
```
✅ Initialized meter 100 (main_three_phase, 3phase)
✅ Initialized meter 10 (office_single_phase, 1phase)
📊 Meter 100 (main_three_phase): Logged 15-min aggregation
📊 Meter 10 (office_single_phase): Logged 15-min aggregation
```

---

## Step 5: Verify Data Logging

### 5.1 Check Data Directory

After 15 minutes (one log interval), verify CSV file was created:

```bash
ls -lh ~/nfe-modbus-energy-logger-prod/data/meter_010/
```

**Expected:**
```
meter_010_2026-03-29.csv
```

### 5.2 Check CSV Content

```bash
head -3 ~/nfe-modbus-energy-logger-prod/data/meter_010/meter_010_*.csv
```

**Expected (single-phase):**
```csv
timestamp,meter_id,meter_name,V_L1,I_L1,P_total,P_L1,PF_total,frequency,energy_total,billing_marker
2026-03-29 15:00:00,10,office_single_phase,230.5,4.32,0.995,0.995,0.998,50.0,456.78,
```

**Expected (three-phase):**
```csv
timestamp,meter_id,meter_name,V_L1,V_L2,V_L3,I_L1,I_L2,I_L3,P_total,P_L1,P_L2,P_L3,PF_total,frequency,energy_total,E_L1_cal,E_L2_cal,E_L3_cal,billing_marker
2026-03-29 15:00:00,100,main_three_phase,230.5,231.2,229.8,12.3,11.8,12.1,8.45,2.8,2.9,2.75,0.95,50.0,1234.56,412.3,415.8,406.46,
```

### 5.3 Monitor for 30 Minutes

Let the system run for at least 30 minutes (2 log intervals) to ensure stable operation:

```bash
# Watch logs
sudo journalctl -u meter.service -f

# Check CSV row count (should increase every 15 minutes)
wc -l ~/nfe-modbus-energy-logger-prod/data/meter_010/*.csv
```

---

## Disabling a Meter (Temporary)

If you need to temporarily disable a meter without removing it from config:

### Option 1: Set `enabled: false` (Recommended)

```bash
cd ~/nfe-modbus-energy-logger-prod
nano config/config.prod.yaml
```

Change:
```yaml
  - id: 10
    name: "office_single_phase"
    type: "1phase"
    enabled: false              # Disable meter
```

Restart service:
```bash
sudo systemctl restart meter.service
```

The meter will be skipped but config remains for future re-enabling.

### Option 2: Comment Out Meter Entry

```yaml
#  - id: 10
#    name: "office_single_phase"
#    type: "1phase"
#    enabled: true
```

---

## Permanently Removing a Meter

### 1. Stop Service

```bash
sudo systemctl stop meter.service
```

### 2. Remove from Config

```bash
cd ~/nfe-modbus-energy-logger-prod
nano config/config.prod.yaml
```

Delete the meter entry completely.

### 3. Archive Data (Optional)

```bash
# Move data to archive location
mkdir -p ~/meter_archives
mv ~/nfe-modbus-energy-logger-prod/data/meter_010 ~/meter_archives/meter_010_$(date +%Y%m%d)
```

### 4. Restart Service

```bash
sudo systemctl start meter.service
```

---

## Troubleshooting

### Meter Not Appearing in Logs

**Check service logs:**
```bash
sudo journalctl -u meter.service -n 50
```

**Possible causes:**
- `enabled: false` in config
- Wrong meter type (1phase vs 3phase)
- Communication failure (check RS485 wiring)
- Address conflict with another meter

### Wrong Readings

**Symptom**: Readings don't match meter display

**Possible causes:**
1. Wrong meter type configured
   - Solution: Change `type: "1phase"` to `"3phase"` or vice versa
2. Wrong meter ID
   - Solution: Verify physical meter address matches config
3. Reading from wrong meter (address conflict)
   - Solution: Check no other meter is using same address

### No Data Files Created

**Check data directory permissions:**
```bash
ls -ld ~/nfe-modbus-energy-logger-prod/data/
```

**Check state directory:**
```bash
ls -l ~/nfe-modbus-energy-logger-prod/data/state/
```

**Ensure directories exist:**
```bash
mkdir -p ~/nfe-modbus-energy-logger-prod/data/state
```

### Address Conflicts (Two Meters, Same Address)

**Symptoms:**
- Intermittent "No response" errors
- Garbled readings
- Data from wrong meter

**Solution:**
1. **Disconnect all meters** from RS485 bus
2. Connect meters **one at a time**
3. Test each meter individually with `test_modbus_read.py`
4. Change duplicate addresses using address changer tool
5. Reconnect all meters to bus

**Prevention:**
- **Never use address 1**
- Keep a written record of all assigned addresses
- Label each meter with its address

---

## Quick Reference

### Meter ID Ranges
- Single-phase: **10-99**
- Three-phase: **100+**
- **Never use address 1**

### Key Files
- Config: `~/nfe-modbus-energy-logger/config/config.prod.yaml`
- Test script: `~/nfe-modbus-energy-logger/scripts/test_modbus_read.py`
- Data directory: `~/nfe-modbus-energy-logger-prod/data/meter_XXX/`

### Common Commands
```bash
# Test meter communication
python3 scripts/test_modbus_read.py

# Deploy configuration changes
bash scripts/deploy.sh

# Monitor logs
sudo journalctl -u meter.service -f

# Restart service
sudo systemctl restart meter.service

# Check data files
ls -lh ~/nfe-modbus-energy-logger-prod/data/meter_*/
```

---

## Need Help?

1. Check [TESTING_GUIDE.md](TESTING_GUIDE.md) for troubleshooting
2. Review service logs: `sudo journalctl -u meter.service -n 100`
3. Test meter individually with `test_modbus_read.py`
4. Verify RS485 wiring and addresses
