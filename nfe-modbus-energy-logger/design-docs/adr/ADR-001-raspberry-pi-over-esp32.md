# ADR-001: Raspberry Pi 4 Instead of ESP32 + PZEM004T

## Status
Accepted

## Context
The original academic proposal specified an ESP32 microcontroller paired with a PZEM004T current/voltage sensor module. This is a common low-cost IoT pairing for basic energy monitoring.

The project requires:
- Reliable polling of a 3-phase CHINT DTSU666 energy meter via Modbus RTU
- Storing ML model files (~14.4 MB) in memory
- Running scikit-learn inference (VotingClassifier with 200-tree RandomForest + XGBoost)
- Writing rotating CSV logs to persistent storage
- Supporting systemd service management
- Remote SSH access and deployment

The ESP32 has ~520 KB SRAM and ~4 MB flash. It cannot hold a 14.4 MB sklearn model, run Python, or use a Linux process manager. The PZEM004T does not support Modbus RTU addressing and is limited to single-phase measurement.

## Decision
Replace ESP32 + PZEM004T with Raspberry Pi 4 + CHINT DTSU666 (3-phase) over Modbus RTU via a CH341 USB-to-RS485 adapter.

- **Raspberry Pi 4:** Full Linux (Debian 13 Trixie), Python 3, systemd, SSH, 4 GB RAM — can run the full sklearn model and logging stack
- **CHINT DTSU666:** Industrial-grade 3-phase energy meter with Modbus RTU, addressable up to 247 slave IDs, supports multi-meter bus topology
- **CH341 USB-RS485 adapter:** Appears as `/dev/ttyUSB0`, works natively with pymodbus

## Consequences

**Better:**
- Can run the full scikit-learn VotingClassifier in memory (14.4 MB model + inference in <2 ms)
- Supports multi-meter deployments on a single RS485 bus (up to 247 meters)
- Python ecosystem: pymodbus, pandas, numpy, joblib — all standard
- systemd for robust auto-restart, journalctl for log management
- SSH + ZeroTier for remote deployment without physical access
- CHINT DTSU666 is a commercially calibrated, UEDCL-approved meter — readings are legally defensible

**Worse:**
- Higher unit cost: Pi ~UGX 250,000 vs. ESP32 ~UGX 15,000
- Higher power consumption: Pi ~5W vs. ESP32 ~0.3W
- Requires stable 5V power supply and protective enclosure
- Not as miniaturised — harder to embed inside a meter cabinet

**Trade-off accepted:** The ML model requirement makes the ESP32 infeasible. The Pi is the minimum viable compute platform for on-device sklearn inference. Power cost difference (~4.7W extra) is negligible at site scale.
