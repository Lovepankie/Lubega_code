# Test vs Production Environment Setup

This document explains how to set up both test and production Raspberry Pi environments for the NFE Modbus Energy Logger.

---

## Key Principle: Same Structure, Different Config

**Both test and production Pis use the same folder structure and deployment process.** The only difference is the content of `config.prod.yaml` (which is gitignored).

---

## Folder Structure (Same on Both Pis)

```
/home/username/
├── nfe-modbus-energy-logger/          # STAGING (git repo)
│   ├── config/
│   │   ├── config.prod.yaml          # Site-specific config (gitignored)
│   │   └── config.yaml.example       # Template in repo
│   ├── src/                          # Python source code
│   ├── docs/                         # Documentation
│   ├── scripts/                      # Deployment scripts
│   └── systemd/                      # Service files
│
└── nfe-modbus-energy-logger-prod/     # PRODUCTION RUNTIME
    ├── config/
    │   └── config.prod.yaml           # Copied from staging
    ├── src/                           # Python source (copied from staging)
    └── data/                          # Runtime data (NOT copied)
        ├── meter_XXX/                # CSV files
        └── state/                    # State files
```

---

## Test Pi Setup

### Purpose
- Test new features before production
- Validate single-phase meter setup
- Short log intervals for faster testing

### Configuration Example

**Test Pi - config.prod.yaml:**
```yaml
port: /dev/ttyUSB0

modbus:
  backend: pymodbus

meters:
  - id: 10                           # Test meter address
    name: "test_single_phase"
    type: "1phase"
    enabled: true

poll_interval: 10
log_interval: 60                     # 1 minute for faster testing

logging:
  base_dir: data
  state_dir: data/state
  rotation:
    max_rows: 50000
    compress_old: true
```

### Setup Commands

```bash
# Clone repo
git clone https://github.com/Nearly-Free-Energy/nfe-modbus-energy-logger.git
cd nfe-modbus-energy-logger

# Create test-specific config
cp config/config.yaml.example config/config.prod.yaml
nano config/config.prod.yaml
# Edit: set meter ID 10, type 1phase, log_interval 60

# Deploy (auto-installs dependencies, service, creates prod folder)
bash scripts/deploy.sh

# Monitor logs
sudo journalctl -u meter.service -f
```

### Expected Output

**Data location:**
```
~/nfe-modbus-energy-logger-prod/data/meter_010/meter_010_2026-03-29.csv
```

**CSV format (single-phase):**
```csv
timestamp,meter_id,meter_name,V_L1,I_L1,P_total,P_L1,PF_total,frequency,energy_total
2026-03-29 15:00:00,10,test_single_phase,230.5,4.32,0.995,0.995,0.998,50.0,456.78
```

---

## Production Pi Setup

### Purpose
- Production customer deployment
- Long-term data logging
- Multiple meters (3-phase + single-phase)

### Configuration Example

**Production Pi - config.prod.yaml:**
```yaml
port: /dev/ttyUSB0

modbus:
  backend: pymodbus

meters:
  - id: 100                          # Production 3-phase meter
    name: "main_three_phase"
    type: "3phase"
    enabled: true

  - id: 10                           # Production single-phase meter
    name: "customer_single_phase"
    type: "1phase"
    enabled: true

poll_interval: 10
log_interval: 900                    # 15 minutes for production

logging:
  base_dir: data
  state_dir: data/state
  rotation:
    max_rows: 50000
    compress_old: true
```

### Setup Commands

```bash
# Clone repo
git clone https://github.com/Nearly-Free-Energy/nfe-modbus-energy-logger.git
cd nfe-modbus-energy-logger

# Create production-specific config
cp config/config.yaml.example config/config.prod.yaml
nano config/config.prod.yaml
# Edit: set meter IDs (100, 10), types, production settings

# Deploy
bash scripts/deploy.sh

# Monitor logs
sudo journalctl -u meter.service -f
```

### Expected Output

**Data locations:**
```
~/nfe-modbus-energy-logger-prod/data/meter_100/meter_100_2026-03-29.csv  # 3-phase
~/nfe-modbus-energy-logger-prod/data/meter_010/meter_010_2026-03-29.csv  # 1-phase
```

**CSV formats differ by meter type** (see examples above)

---

## Key Differences Summary

| Aspect | Test Pi | Production Pi |
|--------|---------|---------------|
| **Folder names** | Same (`nfe-modbus-energy-logger`, `nfe-modbus-energy-logger-prod`) | Same |
| **Config file name** | `config.prod.yaml` | `config.prod.yaml` |
| **Meter IDs** | 10-19 (test range) | 100+ (production range) |
| **Log interval** | 60s (1 minute, faster testing) | 900s (15 minutes, production) |
| **Meter types** | Usually single meter for testing | Multiple meters (3-phase + 1-phase) |
| **Data folders** | `meter_010/` etc. | `meter_100/`, `meter_010/` etc. |
| **Systemd service** | `meter.service` | `meter.service` |
| **Deployment process** | Identical | Identical |

---

## Why This Approach?

### Benefits

1. **Test the exact deployment** - Same scripts, same paths, same process
2. **No surprises in production** - If it works on test Pi, it works in production
3. **Easy to maintain** - One set of scripts, one systemd service
4. **Config stays local** - Each Pi has its own gitignored `config.prod.yaml`
5. **Data separation** - Different meter IDs = different data folders

### Config is NOT in Git

**config.prod.yaml is gitignored** because it contains:
- Customer-specific meter IDs
- Site-specific RS485 port paths
- Environment-specific settings
- Customer data privacy

Each Pi gets its own config file that never goes into version control.

---

## Deployment Workflow

### Initial Setup (Once per Pi)

```bash
git clone <repo>
cd nfe-modbus-energy-logger
cp config/config.yaml.example config/config.prod.yaml
nano config/config.prod.yaml  # Edit for this specific Pi
bash scripts/deploy.sh         # Handles everything automatically
```

### Code Updates (After First Deployment)

```bash
cd ~/nfe-modbus-energy-logger
git pull                       # Get latest code
bash scripts/deploy.sh         # Deploy to production runtime
```

**The deploy script automatically:**
- Skips dependency installation (already installed)
- Skips service setup (already configured)
- Creates backup of current production
- Syncs new code to production runtime
- Restarts service with new code
- Rolls back if deployment fails

---

## Testing New Features

### On Test Pi:

1. Pull latest code: `git pull`
2. Check changes won't break existing config
3. Deploy: `bash scripts/deploy.sh`
4. Monitor: `sudo journalctl -u meter.service -f`
5. Verify data: `ls -lh ~/nfe-modbus-energy-logger-prod/data/meter_010/`
6. Check CSV: `head -20 ~/nfe-modbus-energy-logger-prod/data/meter_010/*.csv`

### On Production Pi (After test validation):

1. Pull same code: `git pull`
2. Deploy: `bash scripts/deploy.sh`
3. Monitor: `sudo journalctl -u meter.service -f`
4. Verify all meters: `ls -lh ~/nfe-modbus-energy-logger-prod/data/`

---

## Troubleshooting

### "How do I know which environment I'm on?"

```bash
# Check config to see meter IDs
cat ~/nfe-modbus-energy-logger/config/config.prod.yaml

# Test environment typically has:
# - Meter IDs 10-19
# - log_interval: 60 (1 minute)

# Production environment typically has:
# - Meter IDs 100+
# - log_interval: 900 (15 minutes)
```

### "Can I have both test and production on same Pi?"

No, not with this setup. The systemd service path and production folder are fixed. Use separate Pis for test and production.

### "What if I want different log intervals on same Pi?"

Edit `config.prod.yaml` in staging, then run `bash scripts/deploy.sh` to sync the change to production runtime.

---

## Quick Reference

### Test Pi
- **Purpose**: Feature validation, testing
- **Meter IDs**: 10-19
- **Log interval**: 60s (faster testing)
- **Config**: Test meter addresses

### Production Pi
- **Purpose**: Customer deployment
- **Meter IDs**: 100+ (3-phase), 10+ (1-phase)
- **Log interval**: 900s (15 minutes)
- **Config**: Customer meter addresses

### Both Use
- Same folder names
- Same systemd service
- Same deployment script
- Same code from git repo
- Different `config.prod.yaml` (gitignored)
