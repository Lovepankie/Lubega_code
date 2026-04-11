# IoT Electricity Theft Detection — Project Handoff

> **University Thesis Project** by Arinda Hillary (AH)
> Last updated: 2026-04-11

---

## What This Project Is

A real-time electricity theft detection system using:
- **Raspberry Pi 4** (headless, Debian 13 Trixie) — field data collection device
- **CHINT DTSU666 3-phase energy meter** — measures L1 (Red), L2 (Yellow), L3 (Blue)
- **RS485/Modbus RTU** via CH341 USB adapter (`/dev/ttyUSB0`)
- **Machine Learning ensemble** (RandomForest + XGBoost VotingClassifier) — detects theft scenarios
- **Python + pymodbus** — data collection pipeline on Pi

The goal is to detect when one or more phases of a 3-phase electricity supply have been bypassed (a common theft method where a wire is clipped around the CT/current transformer so current flows but isn't measured).

---

## Hardware Setup

| Component | Detail |
|---|---|
| Pi model | Raspberry Pi 4 |
| Pi OS | Debian 13 Trixie (headless) |
| Pi username | `nfetestpi2` |
| Pi WiFi IP | `192.168.100.11` |
| Meter model | CHINT DTSU666 (3-phase) |
| Interface | RS485 → USB (CH341 chip) → `/dev/ttyUSB0` |
| Modbus slave ID | 1 |
| GitHub repo | `https://github.com/Lovepankie/Lubega_code` |

**SSH access:** `ssh nfetestpi2@192.168.100.11` (works when on same LAN or ethernet)
**Remote access:** Pi Connect browser terminal (when on different network)

---

## Known Pi Issues

### Clock Drift (IMPORTANT)
The Pi has **no RTC (real-time clock)**. After every power cut it resets to an old date (usually April 6 2026). Always fix this before starting data collection:

```bash
sudo timedatectl set-time '2026-04-11 HH:MM:SS'
```

Replace with current EAT (East Africa Time = UTC+3) time. Failure to fix this causes timestamp corruption in the CSV files.

---

## Project File Structure

```
nfe-modbus-energy-logger/
├── data/                        # All collected CSVs (Windows laptop)
│   ├── normal_final.csv         # 22,081 rows — baseline normal
│   ├── bypass_yellow.csv        # 16,612 rows — L2 bypassed
│   ├── bypass_blue.csv          # 12,027 rows — L3 bypassed
│   ├── bypass_red.csv           # 28,947 rows — L1 bypassed
│   └── bypass_red_blue.csv      # 12,617 rows — L1+L3 bypass attempt
├── model/
│   ├── theft_detector.pkl       # Trained VotingClassifier (RF + XGBoost)
│   ├── scaler.pkl               # StandardScaler fitted on training data
│   └── features.pkl             # Ordered list of 20 feature names
├── scripts/
│   ├── train_model.py           # Full ML training pipeline
│   ├── generate_model_report.py # PDF report for model performance
│   ├── generate_bypass_yellow_report.py
│   ├── generate_bypass_blue_report.py
│   └── generate_bypass_red_blue_report.py
├── docs/
│   ├── bypass_yellow_report.pdf
│   ├── bypass_blue_report.pdf
│   ├── bypass_red_blue_report.pdf
│   └── model_report.pdf
└── Pi path: /home/nfetestpi2/iot_meter/
    ├── scripts/collect_data.py  # Data collection script
    ├── src/                     # Modbus client, meter reader, CSV logger
    └── data/                    # CSVs stored on Pi
```

---

## Data Collection — How It Works

Data is collected on the Pi via systemd services. Each scenario has its own service:

```bash
# Service template (stored at /etc/systemd/system/<name>.service)
[Unit]
Description=Bypass <scenario> data collection
After=local-fs.target network.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=nfetestpi2
WorkingDirectory=/home/nfetestpi2/iot_meter
ExecStart=/usr/bin/python3 scripts/collect_data.py --label <scenario> --duration 999999999 --output data/<scenario>.csv
Restart=always
RestartSec=10
StandardOutput=append:/home/nfetestpi2/iot_meter/logs/<scenario>_collection.log
StandardError=append:/home/nfetestpi2/iot_meter/logs/<scenario>_collection.log

[Install]
WantedBy=multi-user.target
```

**Start a new scenario:**
```bash
sudo systemctl start bypass-<scenario>-collection.service
```

**Stop a scenario:**
```bash
sudo systemctl stop bypass-<scenario>-collection.service
sudo systemctl disable bypass-<scenario>-collection.service
```

**Check status + row count:**
```bash
sudo systemctl status bypass-<scenario>-collection.service
wc -l /home/nfetestpi2/iot_meter/data/<scenario>.csv
tail -3 /home/nfetestpi2/iot_meter/data/<scenario>.csv
```

**Download CSV to Windows (when on same LAN):**
```bash
scp nfetestpi2@192.168.100.11:/home/nfetestpi2/iot_meter/data/<scenario>.csv "D:/Engineering/Lubega_Project/CUSTOM_CODE/Lubega_Project/nfe-modbus-energy-logger/data/<scenario>.csv"
```

---

## CSV Format

Each row has these columns:

```
timestamp, scenario, label, V_L1, V_L2, V_L3, I_L1, I_L2, I_L3, P_L1, P_L2, P_L3, P_total, PF_total, frequency, energy_total
```

- `label` = 1 for bypass (theft), 0 for normal
- Voltages in V, Currents in A, Power in kW, frequency in Hz

---

## Completed Scenarios

| Scenario | File | Rows | Notes |
|---|---|---|---|
| Normal baseline | `normal_final.csv` | 22,081 | Clean reference data |
| Bypass Yellow (L2) | `bypass_yellow.csv` | 16,612 | I_L2 = 0.0A confirmed |
| Bypass Blue (L3) | `bypass_blue.csv` | 12,027 | I_L3 = 0.0A confirmed. Filter rows >= 2026-04-09 (clock drift) |
| Bypass Red (L1) | `bypass_red.csv` | 28,947 | I_L1 suppressed confirmed |
| Bypass Red+Blue (L1+L3) | `bypass_red_blue.csv` | 12,617 | L3 confirmed (I_L3=0.0A). L1 bypass wire ineffective (I_L1=1.27A). Filter rows >= 2026-04-10 |
| **Bypass Red+Yellow (L1+L2)** | On Pi now | ~14,594+ rows | **CURRENTLY COLLECTING** as of 2026-04-11 01:38 EAT |

### Remaining Scenarios to Collect
- `bypass_blue_yellow` — L2+L3 bypassed
- `bypass_all` — All 3 phases bypassed

---

## ML Model

### Architecture
- **VotingClassifier** (soft voting): RandomForestClassifier + XGBClassifier
- **Scaler**: StandardScaler (fitted on training data)
- **Performance**: AUC = 1.0000 on test set

### 20 Features Used

**Raw readings (9):**
`I_L1, I_L2, I_L3, V_L1, V_L2, V_L3, P_total, PF_total, frequency`

**Engineered features (11):**
```python
I_imbalance = std([I_L1, I_L2, I_L3]) / mean([I_L1, I_L2, I_L3])
V_imbalance = std([V_L1, V_L2, V_L3]) / mean([V_L1, V_L2, V_L3])
I_L1_zero   = (I_L1 < 0.05).astype(int)
I_L2_zero   = (I_L2 < 0.05).astype(int)
I_L3_zero   = (I_L3 < 0.05).astype(int)
V_L1_zero   = (V_L1 < 10).astype(int)
V_L2_zero   = (V_L2 < 10).astype(int)
V_L3_zero   = (V_L3 < 10).astype(int)
PF_zero     = (PF_total < 0.01).astype(int)
I_total     = I_L1 + I_L2 + I_L3
P_per_I     = P_total / (I_total + 1e-6)
```

### Saved Model Files
```
model/theft_detector.pkl   # VotingClassifier
model/scaler.pkl           # StandardScaler
model/features.pkl         # ['I_L1', 'I_L2', ... ] ordered list
```

### Using the Model for Inference
```python
import pickle
import pandas as pd
import numpy as np

model    = pickle.load(open('model/theft_detector.pkl', 'rb'))
scaler   = pickle.load(open('model/scaler.pkl', 'rb'))
features = pickle.load(open('model/features.pkl', 'rb'))

# Build feature row from a reading
def engineer_features(row):
    I = [row['I_L1'], row['I_L2'], row['I_L3']]
    V = [row['V_L1'], row['V_L2'], row['V_L3']]
    row['I_imbalance'] = np.std(I) / (np.mean(I) + 1e-6)
    row['V_imbalance'] = np.std(V) / (np.mean(V) + 1e-6)
    row['I_L1_zero']   = int(row['I_L1'] < 0.05)
    row['I_L2_zero']   = int(row['I_L2'] < 0.05)
    row['I_L3_zero']   = int(row['I_L3'] < 0.05)
    row['V_L1_zero']   = int(row['V_L1'] < 10)
    row['V_L2_zero']   = int(row['V_L2'] < 10)
    row['V_L3_zero']   = int(row['V_L3'] < 10)
    row['PF_zero']     = int(row['PF_total'] < 0.01)
    row['I_total']     = sum(I)
    row['P_per_I']     = row['P_total'] / (row['I_total'] + 1e-6)
    return row

X = pd.DataFrame([engineer_features(reading)])[features]
X_scaled = scaler.transform(X)
prediction = model.predict(X_scaled)[0]
probability = model.predict_proba(X_scaled)[0][1]
print(f"Theft detected: {bool(prediction)}, confidence: {probability:.2%}")
```

---

## Pending Tasks

### High Priority
1. **Wait for bypass_red_yellow** to collect enough data (~8–12 hours minimum), then:
   - `scp` the CSV to `data/bypass_red_yellow.csv` on Windows
   - Run `scripts/generate_bypass_red_blue_report.py` as template (adjust for red+yellow)
   - Generate PDF report to `docs/bypass_red_yellow_report.pdf`

2. **Collect bypass_blue_yellow** (L2 + L3):
   - Stop current service
   - Create new systemd service with `--label bypass_blue_yellow`
   - Collect ~8–12 hours

3. **Collect bypass_all** (all 3 phases):
   - Same process, label `bypass_all`

4. **Retrain model** with all scenarios included (currently trained on partial data)

5. **Deploy model to Pi**:
   - Push `model/` folder to GitHub
   - Pi pulls from GitHub
   - Create `detect.py` live detection script on Pi that reads meter and runs inference every N seconds
   - Create systemd service for live detection

### Lower Priority
- Build `master_dataset.csv` merging all scenario CSVs
- Dashboard / web UI for live alerts

---

## ReportLab PDF Generation — Known Bug

**DO NOT** use `borderColor` or `borderWidth` in `ParagraphStyle` with ReportLab 4.4.10+. It causes:

```
ValueError: The truth value of an array with more than one element is ambiguous
```

Just omit those parameters entirely. All report scripts have this fix applied already.

---

## Previous Reports Generated

| Report | File | Description |
|---|---|---|
| Bypass Yellow | `docs/bypass_yellow_report.pdf` | Yellow (#f9a825) theme, L2 phase analysis |
| Bypass Blue | `docs/bypass_blue_report.pdf` | Blue (#1e88e5) theme, L3 phase, filtered >= 2026-04-09 |
| Bypass Red+Blue | `docs/bypass_red_blue_report.pdf` | Purple (#8e24aa) theme, L1+L3, 11,329 rows, 18.3h |
| Model Report | `docs/model_report.pdf` | AUC=1.0, confusion matrix, feature importance |

---

## How to Generate a New Scenario Report

Use an existing report script as a template (e.g. `scripts/generate_bypass_red_blue_report.py`) and change:
1. `CSV_FILE` path
2. `SCENARIO_NAME` and `BYPASSED_PHASES`
3. `COLOR` (hex)
4. `ACTUAL_START` / `ACTUAL_END` timestamps
5. Clock-drift filter line (e.g. `df = df[df['timestamp'] >= '2026-04-11']`)
6. Output path for charts folder and PDF

Then run:
```bash
cd "D:/Engineering/Lubega_Project/CUSTOM_CODE/Lubega_Project/nfe-modbus-energy-logger"
python scripts/generate_bypass_<scenario>_report.py
```

---

## Quick Reference Commands

```bash
# SSH into Pi
ssh nfetestpi2@192.168.100.11

# Fix Pi clock (always do this first)
sudo timedatectl set-time '2026-04-11 HH:MM:SS'

# Check current collection status
sudo systemctl status bypass-red-yellow-collection.service
wc -l /home/nfetestpi2/iot_meter/data/bypass_red_yellow.csv

# Download current CSV
scp nfetestpi2@192.168.100.11:/home/nfetestpi2/iot_meter/data/bypass_red_yellow.csv "D:/Engineering/Lubega_Project/CUSTOM_CODE/Lubega_Project/nfe-modbus-energy-logger/data/bypass_red_yellow.csv"

# Train model
cd "D:/Engineering/Lubega_Project/CUSTOM_CODE/Lubega_Project/nfe-modbus-energy-logger"
python scripts/train_model.py
python scripts/generate_model_report.py
```
