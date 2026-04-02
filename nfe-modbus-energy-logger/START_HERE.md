# 🚀 START HERE - NFE Modbus Energy Logger

**Welcome! This guide will get you from zero to a fully operational system.**

---

## 📖 What is This Project?

This is a production-ready energy logging system that:
- Reads data from Chint DDSU666 energy meters (three-phase and single-phase)
- Logs data every 15 minutes to CSV files
- Runs automatically as a system service on Raspberry Pi
- Handles log rotation and compression automatically
- Supports multiple meters simultaneously

**Perfect for:** Energy monitoring, consumption tracking, grid analysis, industrial applications.

---

## 🎯 Your Mission (Choose One)

### Option A: I'm Deploying for the First Time
**You have a Raspberry Pi and want to get the system running.**

👉 **Follow this path:**
1. Read [PRE_DEPLOYMENT_CHECKLIST.md](docs/PRE_DEPLOYMENT_CHECKLIST.md) - Gather info you need
2. Follow [QUICKSTART.md](docs/QUICKSTART.md) - Step-by-step deployment (30-60 minutes)
3. **Test on Test Pi:** [TESTING_ON_TEST_PI.md](docs/TESTING_ON_TEST_PI.md) - Complete testing guide
4. Deploy to production following [DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

### Option B: I Need to Update Production Code
**The system is already running and you need to deploy changes.**

👉 **Follow this path:**
1. Go to [DEPLOYMENT.md - Production Updates](docs/DEPLOYMENT.md#production-updates)
2. Choose your scenario:
   - Code changes (bug fixes, features)
   - Configuration changes (enable new meter)
   - Emergency rollback

---

### Option C: I'm Troubleshooting an Issue
**Something isn't working and you need help.**

👉 **Follow this path:**
1. Check [TESTING_GUIDE.md - Troubleshooting](docs/TESTING_GUIDE.md#troubleshooting)
2. Check [DEPLOYMENT.md - Troubleshooting](docs/DEPLOYMENT.md#troubleshooting)
3. Review service logs: `sudo journalctl -u meter.service -n 100`

---

### Option D: I Want to Understand the System
**You want to learn how it works before deploying.**

👉 **Follow this path:**
1. Read [README.md](README.md) - Architecture and technical details
2. Review [QUICKSTART.md - Understanding the System](docs/QUICKSTART.md#understanding-the-system)
3. Look at configuration files:
   - [config/config.yaml.example](config/config.yaml.example) - Configuration template
   - [systemd/meter.service](systemd/meter.service) - Service definition

---

## 📚 All Documentation Files

| File | Purpose | When to Use |
|------|---------|-------------|
| **START_HERE.md** | You are here! Navigation guide | First stop for everyone |
| **[PRE_DEPLOYMENT_CHECKLIST.md](docs/PRE_DEPLOYMENT_CHECKLIST.md)** | Checklist before deploying | Before first deployment |
| **[QUICKSTART.md](docs/QUICKSTART.md)** | Complete deployment guide | First-time deployment |
| **[TESTING_ON_TEST_PI.md](docs/TESTING_ON_TEST_PI.md)** | Complete testing guide | Testing on test Pi before production |
| **[ADDING_METERS.md](docs/ADDING_METERS.md)** | Adding new meters guide | When adding or removing meters |
| **[TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** | Testing & troubleshooting | After deployment, when issues arise |
| **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** | Production operations | Updates, rollback, log upload |
| **[README.md](README.md)** | Technical documentation | Understanding architecture |

---

## ⚡ Quick Command Reference

### On Raspberry Pi - Check Status
```bash
# Is the service running?
sudo systemctl status meter.service

# View live logs
sudo journalctl -u meter.service -f

# Check data files
ls -lh ~/nfe-modbus-energy-logger-prod/data/meter_*/
```

### On Raspberry Pi - Deploy Updates
```bash
# Update staging from git
cd ~/nfe-modbus-energy-logger
git pull

# Test in staging
python3 -m src.main config/config.prod.yaml
# Press Ctrl+C after 30 seconds

# Deploy to production
~/nfe-modbus-energy-logger/scripts/deploy.sh
```

### On Raspberry Pi - Emergency Rollback
```bash
# List backups
ls -lht ~/nfe-backups/

# Rollback to specific backup
~/nfe-modbus-energy-logger/scripts/rollback.sh nfe-backup-20260319_143052
```

---

## 🏗️ Project Structure Quick Reference

```
/home/nfetestpi2/
├── nfe-modbus-energy-logger/          # STAGING (git repo, for testing)
│   ├── config/config.prod.yaml        # Configuration template
│   ├── scripts/                       # Deployment scripts
│   │   ├── deploy.sh                  # Deploy staging → production
│   │   ├── rollback.sh                # Rollback to backup
│   │   └── validate_deployment.sh     # Validate deployment
│   └── src/                           # Source code
│
├── nfe-modbus-energy-logger-prod/     # PRODUCTION (service runs here)
│   ├── config/config.prod.yaml        # Active configuration
│   ├── data/                          # CSV files and state
│   │   ├── meter_001/                 # Data for meter 1
│   │   └── state/                     # Energy calculation state
│   └── src/                           # Running code
│
├── nfe-backups/                       # Automatic backups
│   └── nfe-backup-YYYYMMDD_HHMMSS/   # Timestamped backups
│
├── deploy.sh                          # Quick access to deploy
└── rollback.sh                        # Quick access to rollback
```

---

## ✅ First-Time Deployment (30-Second Overview)

1. **Prepare:** Complete [PRE_DEPLOYMENT_CHECKLIST.md](docs/PRE_DEPLOYMENT_CHECKLIST.md)
2. **Deploy:** Follow [QUICKSTART.md](docs/QUICKSTART.md) steps 1-10
3. **Verify:** Run validation script and check logs
4. **Monitor:** Let it run for 24 hours
5. **Done:** System is operational!

---

## 🎓 Key Concepts

### Staging vs Production
- **Staging** (`~/nfe-modbus-energy-logger/`) - Where you test changes
- **Production** (`~/nfe-modbus-energy-logger-prod/`) - Where service runs
- **Never edit production directly** - Always test in staging first

### How Data Logging Works
1. **Polls meters every 10 seconds** (for accurate energy calculation)
2. **Logs to CSV every 15 minutes** (averages buffered readings)
3. **Rotates files at 50,000 rows** (~17 months of data)
4. **Compresses old files** (saves 90% disk space)

### Why 15-Minute Intervals?
- Industry standard for energy monitoring
- Reduces disk usage by 99% vs continuous logging
- Still accurate - polls frequently for energy integration
- ~96 rows per day = ~10 KB per day per meter

---

## 🆘 Common Issues & Quick Fixes

### "Service failed to start"
```bash
# Check logs for specific error
sudo journalctl -u meter.service -n 50

# Common fix: User not in dialout group
sudo usermod -a -G dialout nfetestpi2
sudo reboot
```

### "No data after 15 minutes"
```bash
# Check if service is actually running
sudo systemctl status meter.service

# Check for Modbus errors
sudo journalctl -u meter.service | grep -i "failed"

# Test Modbus connection manually
cd ~/nfe-modbus-energy-logger
python3 scripts/test_modbus_read.py
```

### "Wrong meter readings"
```bash
# Verify meter IDs in config match physical meters
nano ~/nfe-modbus-energy-logger-prod/config/config.prod.yaml

# Restart service after config change
sudo systemctl restart meter.service
```

---

## 📞 Need More Help?

1. **Search the documentation:**
   - [TESTING_GUIDE.md](docs/TESTING_GUIDE.md) has detailed troubleshooting
   - [DEPLOYMENT.md](docs/DEPLOYMENT.md) covers production scenarios

2. **Check the logs:**
   ```bash
   sudo journalctl -u meter.service -n 100
   ```

3. **Test components individually:**
   ```bash
   # Test Modbus connection
   cd ~/nfe-modbus-energy-logger
   python3 scripts/test_modbus_read.py

   # Test configuration
   python3 -c "import yaml; print(yaml.safe_load(open('config/config.prod.yaml')))"
   ```

4. **Validate deployment:**
   ```bash
   cd ~/nfe-modbus-energy-logger
   bash scripts/validate_deployment.sh
   ```

---

## 🎯 Next Steps

**Choose your path from the top of this document and get started!**

New to deployment? → [PRE_DEPLOYMENT_CHECKLIST.md](docs/PRE_DEPLOYMENT_CHECKLIST.md)

Ready to deploy? → [QUICKSTART.md](docs/QUICKSTART.md)

Need to troubleshoot? → [TESTING_GUIDE.md](docs/TESTING_GUIDE.md)

---

**Good luck! 🚀**
