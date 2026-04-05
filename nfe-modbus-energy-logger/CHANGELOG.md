# Changelog

All notable changes to this project are documented here.

---

## [3.0.0] - 2026-04-05

### Theft Detection ML Pipeline — Data Collection Phase

This release pivots the project from a pure energy logger into a full
**electricity theft detection system** using an ML ensemble
(Isolation Forest + One-Class SVM + LSTM Autoencoder).

### Added
- `scripts/collect_data.py` — Labelled dataset collector for ML training.
  Reads all channels from the CHINT DTSU666 at a 5-second interval and writes
  rows with `scenario` and `label` columns (0 = normal, 1 = theft/bypass).
  Supports `--label`, `--duration`, and `--output` CLI arguments.
- `scripts/modbus_test.py` — Modbus connectivity tester rewritten to use the
  existing `src/` infrastructure. Runs sanity checks on PF, frequency, and
  voltage and prints a pass/fail summary.
- `scripts/generate_report.py` — Automated PDF analysis report generator.
  Embeds all 8 matplotlib charts, descriptive statistics tables, ML feature
  implication mapping, and data quality assessment into a multi-page A4 report
  using ReportLab.
- `docs/charts/` — Auto-generated analysis charts from the normal baseline
  dataset (8 PNG files: voltage, current, power, hourly load, frequency,
  energy, current histogram, per-phase power).
- `docs/normal_baseline_report.pdf` — 24-hour normal baseline analysis report.
- `/etc/systemd/system/normal-collection.service` (on Pi) — systemd service
  for robust background data collection. Configured with:
  - `Restart=always` — restarts after any exit (crash, normal completion,
    or unexpected power cut).
  - `RestartSec=10` — 10-second cooldown before each restart.
  - `StartLimitIntervalSec=0` — systemd will never give up restarting.
  - `After=local-fs.target network.target` — waits for filesystem and network
    before starting.
  - `WantedBy=multi-user.target` + `systemctl enable` — auto-starts on every
    boot.

### Fixed
- **Slave ID**: Changed meter slave ID from `100` → `1` (CHINT DTSU666
  factory default). Previous config caused all Modbus reads to time out.
- **Stop bits**: Fixed `stopbits=2` → `stopbits=1` in `src/modbus_client.py`.
  Confirmed correct value via `scan_meter.py`.
- **Function code**: Previous scripts used `read_holding_registers` (FC 0x03).
  DTSU666 input registers require FC 0x04 (`read_input_registers`). Now uses
  the existing `ModbusClient.read_input_float()` throughout.

### Changed
- `config/config.prod.yaml` — Updated meter slave ID from `100` to `1`.
- `src/modbus_client.py` — `stopbits` corrected from `2` to `1`.

---

## [2.0.0] - 2026-03-19

### Multi-Meter Support & Aggregation

- Multi-meter support: monitor multiple meters simultaneously (3-phase and
  single-phase).
- 15-minute aggregated logging — reduces disk usage by 99% vs continuous
  logging.
- Automatic log rotation at 50,000 rows with gzip compression of old files.
- Per-meter directory organisation under `data/`.
- Dual Modbus backends: `pymodbus` or `mbpoll` selectable via config.
- Trapezoidal energy integration for per-phase energy calculation.
- Hot-swappable meters: enable/disable without code changes.

---

## [1.0.0] - Initial Release

- Single CHINT DTSU666 three-phase meter logging via RS485/Modbus RTU.
- Continuous CSV logging at configurable poll interval.
- Basic systemd service deployment.
