# 📋 Changelog

All notable changes to this project are documented here.

---

## 🚀 [4.0.0] - 2026-05-04

### 🎉 System Fully Live — End-to-End Theft Detection in Production

The entire pipeline is now running end-to-end on the Pi (`nfetestpi2`), writing alerts
and readings to Neon PostgreSQL in real time, and visible on the Streamlit Cloud dashboard.

### ✅ Added
- 📡 **`latest_reading_{meter_id}.json` hook in `src/main.py`** — 3-line addition (lines 188-190) that
  overwrites a JSON file with the freshest raw Modbus reading after every 10-second poll. This is the
  bridge between `meter.service` and `detect.py`, ensuring inference always sees the same data
  distribution the model was trained on (raw 10s readings, not 15-min averages).
- 🤖 **`detect.py` (Dennis)** — Full inference loop polling `latest_reading_{meter_id}.json` every 10s.
  Engineers 20 features, scales with `scaler.pkl`, runs `theft_detector.pkl` VotingClassifier.
  INSERTs every reading into the `readings` table; INSERTs into the `alerts` table only when
  `prob >= threshold (0.5)`. Skips unchanged readings via `last_seen` guard.
- ⚙️ **`theft-detector.service` (Dennis)** — systemd unit wrapping `detect.py`. Runs after `meter.service`.
  Active and running on `nfetestpi2`. Configured with `User=nfetestpi2` and correct `DATA_DIR`.
- 🖥️ **`monitor.py`** — Local Pi diagnostic Streamlit dashboard. Reads `latest_reading_1.json` every 5s.
  Shows metric tiles (V/I/P per phase) and rolling 60-reading line charts (Current, Voltage, Power tabs).
  Not deployed to cloud — used by field engineers for on-site commissioning and maintenance.
- 📊 **Neon `readings` table** — Schema recreated with correct column names (`i_l1`, `i_l2`, etc.) after
  original schema had wrong column names. Every 10-second reading now logged permanently.

### ✅ Cloud (Hillary)
- **`streamlit_app.py`** deployed to Streamlit Community Cloud.
  URL: `lubegacode-tbn4wlkpdrzqhjahqssdvf.streamlit.app`
- KPI row (total alerts, 24h count, latest probability, last alert time)
- Colour-coded alerts table (red ≥90%, yellow ≥70%)
- Live readings tabs (Current / Voltage / Power) — 30s auto-refresh
- Alert trend bar chart

### 🐛 Known Issue
- **I_L2 reads 0.000A permanently** — `I_L2_zero` feature fires on every reading, model classifies
  every reading as theft (~94% probability). Likely wiring issue or no load on L2 phase.
  Field investigation pending.

### 📐 Architecture
- `design-docs/architecture.dsl` updated to v4.0.0 — all "TO BUILD / PLANNED / NEEDS REWRITE" labels
  removed. `localMonitor` component added for `monitor.py`.

---

## 🚀 [3.0.0] - 2026-04-05

### 🤖 Theft Detection ML Pipeline — Data Collection Phase

This release pivots the project from a pure energy logger into a full
**electricity theft detection system** using an ML ensemble
(Isolation Forest + One-Class SVM + LSTM Autoencoder).

### ✅ Added
- 📊 `scripts/collect_data.py` — Labelled dataset collector for ML training.
  Reads all channels from the CHINT DTSU666 at a 5-second interval and writes
  rows with `scenario` and `label` columns (0 = normal, 1 = theft/bypass).
  Supports `--label`, `--duration`, and `--output` CLI arguments.
- 🔌 `scripts/modbus_test.py` — Modbus connectivity tester rewritten to use the
  existing `src/` infrastructure. Runs sanity checks on PF, frequency, and
  voltage and prints a pass/fail summary.
- 📄 `scripts/generate_report.py` — Automated PDF analysis report generator.
  Embeds all 8 matplotlib charts, descriptive statistics tables, ML feature
  implication mapping, and data quality assessment into a multi-page A4 report
  using ReportLab.
- 🖼️ `docs/charts/` — Auto-generated analysis charts from the normal baseline
  dataset (8 PNG files: voltage, current, power, hourly load, frequency,
  energy, current histogram, per-phase power).
- 📑 `docs/normal_baseline_report.pdf` — 24-hour normal baseline analysis report.
- ⚙️ `/etc/systemd/system/normal-collection.service` (on Pi) — systemd service
  for robust background data collection. Configured with:
  - `Restart=always` — restarts after any exit (crash, normal completion,
    or unexpected power cut ⚡).
  - `RestartSec=10` — 10-second cooldown before each restart.
  - `StartLimitIntervalSec=0` — systemd will never give up restarting.
  - `After=local-fs.target network.target` — waits for filesystem and network
    before starting.
  - `WantedBy=multi-user.target` + `systemctl enable` — auto-starts on every
    boot 🔁.

### 🐛 Fixed
- 🔢 **Slave ID**: Changed meter slave ID from `100` → `1` (CHINT DTSU666
  factory default). Previous config caused all Modbus reads to time out.
- 📡 **Stop bits**: Fixed `stopbits=2` → `stopbits=1` in `src/modbus_client.py`.
  Confirmed correct value via `scan_meter.py`.
- 📟 **Function code**: Previous scripts used `read_holding_registers` (FC 0x03).
  DTSU666 input registers require FC 0x04 (`read_input_registers`). Now uses
  the existing `ModbusClient.read_input_float()` throughout.

### 🔧 Changed
- `config/config.prod.yaml` — Updated meter slave ID from `100` to `1`.
- `src/modbus_client.py` — `stopbits` corrected from `2` to `1`.

---

## ⚡ [2.0.0] - 2026-03-19

### 🔀 Multi-Meter Support & Aggregation

- 📟 Multi-meter support: monitor multiple meters simultaneously (3-phase and
  single-phase).
- 🗜️ 15-minute aggregated logging — reduces disk usage by 99% vs continuous
  logging.
- 🔄 Automatic log rotation at 50,000 rows with gzip compression of old files.
- 📁 Per-meter directory organisation under `data/`.
- 🔌 Dual Modbus backends: `pymodbus` or `mbpoll` selectable via config.
- 🔋 Trapezoidal energy integration for per-phase energy calculation.
- 🔁 Hot-swappable meters: enable/disable without code changes.

---

## 🌱 [1.0.0] - Initial Release

- ⚡ Single CHINT DTSU666 three-phase meter logging via RS485/Modbus RTU.
- 📝 Continuous CSV logging at configurable poll interval.
- 🖥️ Basic systemd service deployment.
