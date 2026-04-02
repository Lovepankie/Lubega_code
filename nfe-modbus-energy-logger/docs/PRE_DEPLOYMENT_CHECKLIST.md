# Pre-Deployment Checklist

**Complete this checklist before deploying to a new Raspberry Pi.**

Use this to verify everything is ready for a smooth deployment.

---

## ✅ Code Repository Checks

### Files Present
- [ ] `README.md` - Project documentation
- [ ] `QUICKSTART.md` - Step-by-step deployment guide
- [ ] `TESTING_GUIDE.md` - Testing procedures
- [ ] `DEPLOYMENT.md` - Production deployment guide
- [ ] `requirements.txt` - Python dependencies
- [ ] `config/config.dev.yaml` - Development configuration
- [ ] `config/config.prod.yaml` - Production configuration template
- [ ] `scripts/deploy.sh` - Deployment script
- [ ] `scripts/rollback.sh` - Rollback script
- [ ] `scripts/test_modbus_read.py` - Manual Modbus test script
- [ ] `systemd/meter.service` - Systemd service file
- [ ] `src/__init__.py` - Python package marker
- [ ] `src/main.py` - Main application
- [ ] `src/meter_reader.py` - Meter type abstraction
- [ ] `src/energy_calc.py` - Energy calculation
- [ ] `src/aggregator.py` - 15-minute aggregation
- [ ] `src/rotating_csv_logger.py` - CSV logging with rotation
- [ ] `src/state_manager.py` - State persistence
- [ ] `src/modbus_client.py` - PyModbus client
- [ ] `src/mbpoll_client.py` - MBPoll client
- [ ] `src/modbus_factory.py` - Backend selector

### Script Permissions
Run these commands in the repository root:
```bash
# Verify scripts have shebang
head -1 scripts/deploy.sh    # Should show: #!/bin/bash
head -1 scripts/rollback.sh  # Should show: #!/bin/bash

# Make scripts executable (if not already)
chmod +x scripts/deploy.sh
chmod +x scripts/rollback.sh
```
- [ ] `scripts/deploy.sh` has `#!/bin/bash` shebang
- [ ] `scripts/rollback.sh` has `#!/bin/bash` shebang
- [ ] Scripts are executable

### Configuration Files Valid
```bash
# Test YAML syntax
python3 -c "import yaml; print(yaml.safe_load(open('config/config.dev.yaml')))"
python3 -c "import yaml; print(yaml.safe_load(open('config/config.prod.yaml')))"
```
- [ ] `config.dev.yaml` has valid YAML syntax
- [ ] `config.prod.yaml` has valid YAML syntax

### Git Repository
- [ ] Repository is hosted (GitHub, GitLab, Bitbucket, etc.)
- [ ] Repository URL is accessible
- [ ] Main branch is up to date
- [ ] All changes are committed and pushed

---

## ✅ Hardware Checks

### Raspberry Pi
- [ ] Raspberry Pi is powered on and accessible via SSH
- [ ] Pi has network connection (can reach internet)
- [ ] Pi has sufficient disk space (check with `df -h`, need at least 2GB free)
- [ ] Pi has Raspberry Pi OS installed (Debian-based)
- [ ] You know the Pi's IP address
- [ ] You know the Pi's username (default: `pi` or `nfetestpi2`)
- [ ] You can SSH into the Pi: `ssh username@<pi-ip>`

### RS485 Adapter
- [ ] RS485 to USB adapter is connected to Raspberry Pi
- [ ] Adapter is recognized by Pi (check with `ls /dev/tty*`)
- [ ] You know the device path (usually `/dev/ttyUSB0`)
- [ ] Adapter has proper permissions (user in `dialout` group)

### Meters
- [ ] Chint DDSU666 meter(s) are connected via RS485
- [ ] Meters are powered on
- [ ] You know each meter's Modbus address (ID)
- [ ] You know each meter's type (three-phase or single-phase)
- [ ] RS485 wiring is correct (A to A, B to B)
- [ ] RS485 termination resistors are in place (if needed)

---

## ✅ Software Prerequisites (Raspberry Pi)

SSH into your Pi and verify:

### System Packages
```bash
# Check Python version (need 3.7+)
python3 --version

# Check if git is installed
git --version

# Check if pip is installed
pip3 --version
```
- [ ] Python 3.7+ installed
- [ ] Git installed
- [ ] pip3 installed

### Optional: mbpoll
```bash
# Check if mbpoll is installed (only needed if using mbpoll backend)
mbpoll --version
```
- [ ] mbpoll installed (if using mbpoll backend)
- [ ] OR using pymodbus backend (no mbpoll needed)

### User Permissions
```bash
# Check if user is in dialout group
groups | grep dialout
```
- [ ] User is in `dialout` group (for serial port access)
- [ ] If not, run: `sudo usermod -a -G dialout <username>` then reboot

---

## ✅ Information Gathering

### Network Information
- [ ] Raspberry Pi IP address: `_________________`
- [ ] Raspberry Pi username: `_________________`
- [ ] SSH access confirmed: `ssh <username>@<ip>`

### Git Repository
- [ ] Repository URL: `_______________________________`
- [ ] Branch to deploy: `_________________` (usually `main`)

### RS485 Configuration
- [ ] RS485 adapter device path: `_________________` (e.g., `/dev/ttyUSB0`)
- [ ] Verify with: `ls /dev/tty*`

### Meter Configuration
Fill in for each meter you have:

**Meter 1:**
- [ ] Modbus address (ID): `_____`
- [ ] Meter type: `☐ 3phase` or `☐ 1phase`
- [ ] Descriptive name: `_______________________________`

**Meter 2 (if applicable):**
- [ ] Modbus address (ID): `_____`
- [ ] Meter type: `☐ 3phase` or `☐ 1phase`
- [ ] Descriptive name: `_______________________________`

**Meter 3 (if applicable):**
- [ ] Modbus address (ID): `_____`
- [ ] Meter type: `☐ 3phase` or `☐ 1phase`
- [ ] Descriptive name: `_______________________________`

---

## ✅ Pre-Deployment Test (Local)

Before deploying to Pi, test locally if possible:

### Import Test
```bash
# In repository root
python3 -c "from src.meter_reader import create_meter_reader; print('✅ Imports OK')"
python3 -c "from src.aggregator import FifteenMinuteAggregator; print('✅ Aggregator OK')"
python3 -c "from src.rotating_csv_logger import RotatingCSVLogger; print('✅ Logger OK')"
```
- [ ] All imports work without errors

### Configuration Test
```bash
# Test that config can be loaded
python3 -c "import yaml; cfg=yaml.safe_load(open('config/config.prod.yaml')); print('✅ Config valid')"
```
- [ ] Configuration loads without errors

---

## ✅ Documentation Review

### Read Before Deploying
- [ ] Read `QUICKSTART.md` completely
- [ ] Understand staging vs production separation
- [ ] Know how to check service status
- [ ] Know how to view logs with journalctl
- [ ] Know how to rollback if needed

### Have Ready for Reference
- [ ] `QUICKSTART.md` - For step-by-step deployment
- [ ] `TESTING_GUIDE.md` - For testing procedures
- [ ] `DEPLOYMENT.md` - For troubleshooting

---

## ✅ Deployment Day Checklist

### Before You Start
- [ ] Backup any existing data on Pi (if applicable)
- [ ] Have at least 30 minutes uninterrupted time
- [ ] Have access to meter physical display (to verify readings)
- [ ] Have terminal/SSH client ready

### During Deployment
Follow `QUICKSTART.md` step by step:
- [ ] Step 1: Initial Raspberry Pi Setup (system packages)
- [ ] Step 2: Clone Repository & Install Dependencies
- [ ] Step 3: Configure for Your Setup
- [ ] Step 4: Test in Staging (**CRITICAL - Don't Skip!**)
- [ ] Step 5: Setup Deployment Scripts
- [ ] Step 6: Deploy to Production
- [ ] Step 7: Install Systemd Service
- [ ] Step 8: Monitor Live Logs (15 minutes)
- [ ] Step 9: Verify Data Collection
- [ ] Step 10: Let It Run for 24 Hours

### After Initial Deployment
- [ ] Service is running: `sudo systemctl status meter.service`
- [ ] First CSV file created after 15 minutes
- [ ] No errors in logs: `sudo journalctl -u meter.service -n 100`
- [ ] CSV data looks reasonable (voltage, current values make sense)

---

## ✅ 24-Hour Verification

After 24 hours of operation:

### Data Quality
```bash
# Check CSV row count (should be ~96 rows)
wc -l ~/nfe-modbus-energy-logger-prod/data/meter_001/*.csv

# Check file size (should be ~10-15 KB)
ls -lh ~/nfe-modbus-energy-logger-prod/data/meter_001/

# View latest entries
tail -10 ~/nfe-modbus-energy-logger-prod/data/meter_001/*.csv
```
- [ ] CSV has ~96 rows (4 per hour × 24 hours)
- [ ] File size is ~10-15 KB
- [ ] Timestamps are correct
- [ ] Voltage values are reasonable (e.g., 220-240V)
- [ ] Current values are reasonable
- [ ] Power values are reasonable

### System Health
```bash
# Check service status
sudo systemctl status meter.service

# Check for errors
sudo journalctl -u meter.service --since "24 hours ago" | grep -i error

# Check disk usage
df -h
```
- [ ] Service is still running (active)
- [ ] No repeating error messages
- [ ] Disk usage is normal
- [ ] No crashes or restarts

---

## ✅ Post-Deployment Tasks

### Optional Enhancements (After Stable Operation)
- [ ] Set up log upload (SCP, email, or cloud) - See `DEPLOYMENT.md`
- [ ] Configure automatic backups
- [ ] Set up monitoring/alerting
- [ ] Document your specific deployment for team

### Team Handoff
- [ ] Update team wiki/documentation with Pi IP and credentials
- [ ] Share meter IDs and configuration
- [ ] Document any site-specific settings
- [ ] Add to team's infrastructure inventory

---

## 🆘 If Something Goes Wrong

### Service Won't Start
1. Check logs: `sudo journalctl -u meter.service -n 100`
2. Check permissions: `sudo usermod -a -G dialout <username>; sudo reboot`
3. Test Modbus manually: `cd ~/nfe-modbus-energy-logger && python3 scripts/test_modbus_read.py`

### No Data After 15 Minutes
1. Check service is running: `sudo systemctl status meter.service`
2. Check logs for Modbus errors: `sudo journalctl -u meter.service | grep failed`
3. Verify meter IDs in config match physical meters

### Wrong Readings
1. Verify meter IDs: Check meter physical display
2. Verify meter type: 3phase vs 1phase in config
3. Verify RS485 wiring: A to A, B to B

### Need to Rollback
```bash
# List backups
ls -lht ~/nfe-backups/

# Rollback to last backup
~/nfe-modbus-energy-logger/scripts/rollback.sh <backup-name>
```

---

## 📋 Summary

**Before you start deployment, ensure:**
1. ✅ All files are in repository
2. ✅ Hardware is connected and accessible
3. ✅ You have all necessary information (IPs, meter IDs, etc.)
4. ✅ You've read the documentation
5. ✅ You have time to monitor for 24 hours

**Ready to deploy?** Start with `QUICKSTART.md` Step 1!

**Not ready?** Review sections above with ☐ unchecked boxes.
