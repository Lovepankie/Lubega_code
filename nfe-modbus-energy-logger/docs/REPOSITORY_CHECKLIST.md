# Repository Pre-Push Checklist

**Complete this checklist before pushing to git repository.**

Run these commands in the repository root directory.

---

## ✅ File Existence Check

```bash
# Documentation files
ls -1 *.md
```

**Expected output:**
```
DEPLOYMENT.md
PRE_DEPLOYMENT_CHECKLIST.md
QUICKSTART.md
README.md
REPOSITORY_CHECKLIST.md
START_HERE.md
TESTING_GUIDE.md
```

- [ ] All 7 documentation files present

```bash
# Configuration files
ls -1 config/
```

**Expected output:**
```
config.dev.yaml
config.prod.yaml
```

- [ ] Both config files present

```bash
# Scripts
ls -1 scripts/
```

**Expected output:**
```
deploy.sh
rollback.sh
test_modbus_read.py
validate_deployment.sh
```

- [ ] All 4 scripts present

```bash
# Source files
ls -1 src/
```

**Expected output:**
```
__init__.py
aggregator.py
csv_logger.py
energy_calc.py
main.py
mbpoll_client.py
meter_reader.py
modbus_client.py
modbus_factory.py
rotating_csv_logger.py
state_manager.py
```

- [ ] All 11 source files present

```bash
# Systemd service
ls -1 systemd/
```

**Expected output:**
```
meter.service
```

- [ ] Service file present

```bash
# Root files
ls -1 | grep -E "requirements.txt|.gitignore"
```

**Expected output:**
```
.gitignore
requirements.txt
```

- [ ] requirements.txt present
- [ ] .gitignore present

---

## ✅ Script Validation

```bash
# Check shebangs
head -1 scripts/deploy.sh
head -1 scripts/rollback.sh
head -1 scripts/validate_deployment.sh
```

**Expected:** All should show `#!/bin/bash`

- [ ] deploy.sh has shebang
- [ ] rollback.sh has shebang
- [ ] validate_deployment.sh has shebang

```bash
# Check service name consistency
grep SERVICE_NAME scripts/deploy.sh
grep SERVICE_NAME scripts/rollback.sh
```

**Expected:** Both should show `SERVICE_NAME="meter.service"`

- [ ] Scripts use correct service name

---

## ✅ Configuration Validation

```bash
# Test YAML syntax
python3 -c "import yaml; print('✅ config.dev.yaml valid') if yaml.safe_load(open('config/config.dev.yaml')) else print('❌ Invalid')"
python3 -c "import yaml; print('✅ config.prod.yaml valid') if yaml.safe_load(open('config/config.prod.yaml')) else print('❌ Invalid')"
```

- [ ] config.dev.yaml has valid YAML
- [ ] config.prod.yaml has valid YAML

```bash
# Check for required keys in prod config
python3 << 'PYEOF'
import yaml
cfg = yaml.safe_load(open('config/config.prod.yaml'))
keys = ['port', 'modbus', 'meters', 'poll_interval', 'log_interval', 'logging']
missing = [k for k in keys if k not in cfg]
if missing:
    print(f"❌ Missing keys: {missing}")
else:
    print("✅ All required keys present in config.prod.yaml")
PYEOF
```

- [ ] config.prod.yaml has all required keys

---

## ✅ Python Code Validation

```bash
# Test imports
python3 -c "from src.meter_reader import create_meter_reader; print('✅ meter_reader imports OK')"
python3 -c "from src.aggregator import FifteenMinuteAggregator; print('✅ aggregator imports OK')"
python3 -c "from src.rotating_csv_logger import RotatingCSVLogger; print('✅ rotating_csv_logger imports OK')"
python3 -c "from src.energy_calc import EnergyCalc; print('✅ energy_calc imports OK')"
python3 -c "from src.state_manager import load, save; print('✅ state_manager imports OK')"
python3 -c "from src.modbus_factory import get_client; print('✅ modbus_factory imports OK')"
```

- [ ] All source files import without errors

```bash
# Check for syntax errors
python3 -m py_compile src/*.py
echo "✅ All Python files compile successfully"
```

- [ ] All Python files compile successfully

---

## ✅ Documentation Link Check

```bash
# Check if documentation files reference each other correctly
grep -l "QUICKSTART.md" *.md | sort
grep -l "DEPLOYMENT.md" *.md | sort
grep -l "TESTING_GUIDE.md" *.md | sort
```

- [ ] Documentation files properly cross-reference each other

---

## ✅ Requirements File

```bash
# Check requirements.txt content
cat requirements.txt
```

**Expected content:**
```
pymodbus>=3.0.0
pyyaml>=6.0
```

- [ ] requirements.txt has pymodbus and pyyaml

---

## ✅ Git Ignore Check

```bash
# Check .gitignore includes necessary patterns
cat .gitignore | grep -E "pycache|\.pyc|data/|\.pdf"
```

**Expected patterns:**
```
__pycache__/
*.pyc
data/
*.pdf
```

- [ ] .gitignore excludes __pycache__
- [ ] .gitignore excludes *.pyc
- [ ] .gitignore excludes data/
- [ ] .gitignore excludes *.pdf

---

## ✅ File Count Summary

```bash
# Total file count
find . -type f \
    -not -path "./.git/*" \
    -not -path "./__pycache__/*" \
    -not -path "*/data/*" \
    -not -name "*.pyc" \
    -not -name "*.pdf" \
    | wc -l
```

**Expected:** ~30-35 files

- [ ] Reasonable number of files (not missing major components)

---

## ✅ Service File Validation

```bash
# Check service file content
grep WorkingDirectory systemd/meter.service
grep ExecStart systemd/meter.service
grep StandardOutput systemd/meter.service
```

**Expected:**
```
WorkingDirectory=/home/nfetestpi2/nfe-modbus-energy-logger-prod
ExecStart=/usr/bin/python3 -m src.main config/config.prod.yaml
StandardOutput=journal
```

- [ ] Service uses correct working directory (-prod)
- [ ] Service uses correct ExecStart command
- [ ] Service logs to journal

---

## ✅ Documentation Completeness

Check each documentation file has required sections:

```bash
# START_HERE.md sections
grep -E "^##" START_HERE.md
```
- [ ] START_HERE.md has navigation sections

```bash
# QUICKSTART.md sections
grep -E "^##" QUICKSTART.md
```
- [ ] QUICKSTART.md has complete deployment steps

```bash
# DEPLOYMENT.md sections
grep -E "^##" DEPLOYMENT.md
```
- [ ] DEPLOYMENT.md has production update scenarios

```bash
# TESTING_GUIDE.md sections
grep -E "^##" TESTING_GUIDE.md
```
- [ ] TESTING_GUIDE.md has testing phases and troubleshooting

---

## ✅ Final Checks

```bash
# No TODO comments left in production code
grep -r "TODO\|FIXME\|XXX" src/ || echo "✅ No TODO comments found"
```
- [ ] No unresolved TODO/FIXME comments in source code

```bash
# Check for hardcoded paths that might need updating
grep -r "/home/nfetestpi2" --include="*.py" src/ || echo "✅ No hardcoded paths in Python code"
```
- [ ] No hardcoded paths in Python source files

```bash
# Verify print statements use proper formatting
grep -r "print(f" src/main.py | head -3
```
- [ ] Print statements in main.py use f-strings (modern formatting)

---

## ✅ Ready to Push

If all checkboxes are checked:

```bash
# Add all files
git add .

# Commit
git commit -m "Complete multi-meter logging system with deployment automation

- Multi-meter support (3-phase and single-phase)
- 15-minute aggregated logging with automatic rotation
- Staging/production separation with rsync deployment
- Comprehensive documentation for new team members
- Automatic backups and rollback capability"

# Push to repository
git push origin main
```

**Repository is ready for deployment! 🚀**

New team members should start with: [START_HERE.md](START_HERE.md)
