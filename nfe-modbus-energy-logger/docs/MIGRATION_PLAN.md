# Meter Address Migration Plan

## Overview
Reconfigure addressing scheme to accommodate future single-phase meter expansion:
- **Current**: 3-phase meter at address 1
- **Target**: 3-phase meter at address 100, new single-phase meter at address 10

## Addressing Scheme
```
Single-phase meters: 10-99  (90 meter capacity)
Three-phase meters:  100+   (reserved for main/high-power meters)
```

## Prerequisites
- NFE logger currently running on Raspberry Pi
- 3-phase meter at address 1 (operational)
- New single-phase meter in DLT645 mode (needs conversion)
- RS485 bus with both meters connected

---

## Step-by-Step Execution Plan

### Phase 1: Prepare Local Changes (Local Mac)

**Status**: ✅ COMPLETED

1. ✅ Updated `config/config.prod.yaml`:
   - Changed 3-phase meter: id 1 → 100
   - Added single-phase meter: id 10 (enabled)
   - Added addressing scheme comments

2. ✅ Commit and push changes to GitHub

---

### Phase 2: Stop Current Logger (Raspberry Pi)

**Critical**: This stops data collection temporarily

```bash
# SSH into Raspberry Pi
ssh pi@<raspberry_pi_ip>

# Navigate to production directory
cd ~/nfe-modbus-energy-logger-prod

# Stop the service
sudo systemctl stop nfe-modbus-logger.service

# Verify it's stopped
sudo systemctl status nfe-modbus-logger.service
```

**Expected downtime**: ~5-10 minutes

---

### Phase 3: Reconfigure 3-Phase Meter Address (Raspberry Pi)

Change 3-phase meter from address 1 → 100

```bash
# Navigate to converter tool
cd ~/chint-protocol-modbus-gateway

# Pull latest CLI tool (if not already done)
git pull

# Change 3-phase meter address: 1 → 100
python3 converter_cli.py change --port /dev/ttyUSB0 --current 1 --new 100
```

**Expected output**:
```
📡 Opening /dev/ttyUSB0 @ 9600 baud (Modbus mode)...
📤 TX: 01100006000100640cb4
📥 RX: 0110000600017091
✅ Address changed: 1 → 100
```

**Verification**:
```bash
# Verify 3-phase meter responds at address 100
python3 converter_cli.py scan --port /dev/ttyUSB0 --start 100 --end 100
```

---

### Phase 4: Convert & Configure Single-Phase Meter (Raspberry Pi)

Convert new meter from DLT645 to Modbus and set to address 10

```bash
# Full conversion process
# Replace <STATION_ADDRESS> with the 12-digit meter serial number
python3 converter_cli.py full --port /dev/ttyUSB0 --station <STATION_ADDRESS> --address 10
```

**Example** (if station address is 200322016690):
```bash
python3 converter_cli.py full --port /dev/ttyUSB0 --station 200322016690 --address 10
```

**Expected output**:
```
═══ FULL PROCESS STARTED ═══

[1/3] Converting DLT645 → Modbus
🔄 Converting DLT645 → Modbus
   Station: 200322016690
   ...
✅ Protocol conversion successful!

[2/3] Scanning for Modbus device
🔍 Scanning Modbus addresses 1–247...
✅ Found device at Modbus address 1

[3/3] Changing Modbus address: 1 → 10
📡 Opening /dev/ttyUSB0 @ 9600 baud (Modbus mode)...
✅ Address changed: 1 → 10

═══ FULL PROCESS COMPLETE ═══
```

**Verification**:
```bash
# Verify single-phase meter responds at address 10
python3 converter_cli.py scan --port /dev/ttyUSB0 --start 10 --end 10
```

---

### Phase 5: Deploy Updated Logger (Raspberry Pi)

Pull latest code and deploy with new configuration

```bash
# Navigate to staging directory
cd ~/nfe-modbus-energy-logger

# Pull latest changes (includes updated config.prod.yaml)
git pull

# Run deployment script
cd scripts
./deploy.sh
```

**What deploy.sh does**:
1. Backs up current production
2. Stops service (already stopped)
3. Syncs staging → production (preserves data directory)
4. Restarts service with new config

**Expected output**:
```
🚀 NFE Modbus Energy Logger - Deployment Script
...
✅ Production directory ready
✅ Service restarted successfully
✅ Service is running
...
🎉 Deployment complete!
```

---

### Phase 6: Verify Operation (Raspberry Pi)

Check that both meters are logging correctly

```bash
# Check service status
sudo systemctl status nfe-modbus-logger.service

# Watch logs in real-time
sudo journalctl -u nfe-modbus-logger.service -f

# Check for meter data directories
ls -la ~/nfe-modbus-energy-logger-prod/data/
```

**Expected directories**:
```
meter_010/  (single-phase meter)
meter_100/  (three-phase meter)
state/      (energy calculation state)
```

**Check CSV files**:
```bash
# Three-phase meter
ls -lh ~/nfe-modbus-energy-logger-prod/data/meter_100/

# Single-phase meter
ls -lh ~/nfe-modbus-energy-logger-prod/data/meter_010/

# View recent data
tail -5 ~/nfe-modbus-energy-logger-prod/data/meter_100/*.csv
tail -5 ~/nfe-modbus-energy-logger-prod/data/meter_010/*.csv
```

---

## Rollback Plan (If Something Goes Wrong)

### If conversion fails:

**3-phase meter won't respond at address 100**:
```bash
# Change it back to address 1
python3 converter_cli.py change --port /dev/ttyUSB0 --current 100 --new 1

# Revert config changes
cd ~/nfe-modbus-energy-logger
git checkout HEAD~1 config/config.prod.yaml

# Redeploy
cd scripts && ./deploy.sh
```

### If logger fails to start:

```bash
# Check logs for errors
sudo journalctl -u nfe-modbus-logger.service -n 50

# Restore from backup
cd ~/nfe-backups
ls -lt  # Find latest backup
cp -r nfe-backup-YYYYMMDD_HHMMSS ~/nfe-modbus-energy-logger-prod

# Restart service
sudo systemctl restart nfe-modbus-logger.service
```

---

## Post-Migration Checklist

- [ ] Both meters responding at correct addresses (100 and 10)
- [ ] Service running without errors
- [ ] Data logging to separate directories (meter_010 and meter_100)
- [ ] CSV files contain valid data for both meters
- [ ] Energy calculations resuming correctly (check calculated energy columns)
- [ ] No error messages in service logs

---

## Future Single-Phase Meter Additions

When adding more single-phase meters:

```bash
# 1. Convert meter to Modbus with next address (11, 12, 13, etc.)
python3 converter_cli.py full --port /dev/ttyUSB0 --station <STATION_ADDR> --address 11

# 2. Update config.prod.yaml (add new meter)
vim ~/nfe-modbus-energy-logger/config/config.prod.yaml

# 3. Deploy
cd ~/nfe-modbus-energy-logger/scripts && ./deploy.sh
```

---

## Notes

- **Total downtime**: ~5-10 minutes (time between stopping service and successful restart)
- **Data preservation**: All existing CSV files in `data/` directory are preserved
- **State preservation**: Energy calculation state preserved in `data/state/`
- **Backup**: deploy.sh creates automatic backup before deployment
- **No data loss**: Data collection resumes from where it left off

## Contact Info

If issues arise, check:
1. Service logs: `sudo journalctl -u nfe-modbus-logger.service -n 100`
2. Meter connectivity: Use scan command to verify addresses
3. Backups: `~/nfe-backups/` contains last 5 deployments
