# NFE Modbus Energy Logger

Multi-meter energy logging system for Chint DDSU666 three-phase and single-phase energy meters via Modbus RTU over RS485.

---

## 📚 Documentation Guide

**New to this project? Start here:**

1. **[QUICKSTART.md](docs/QUICKSTART.md)** - Step-by-step deployment guide (start here!)
2. **[TESTING_ON_TEST_PI.md](docs/TESTING_ON_TEST_PI.md)** - Complete testing guide (test Pi)
3. **[TEST_VS_PRODUCTION.md](docs/TEST_VS_PRODUCTION.md)** - Test Pi vs Production Pi setup
4. **[ADDING_METERS.md](docs/ADDING_METERS.md)** - Adding new meters (single-phase & three-phase)
5. **[TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** - Testing procedures and troubleshooting
6. **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment, updates, rollback, log upload
7. **README.md** (this file) - Technical details and architecture

**Quick Links:**
- Need to deploy for the first time? → [QUICKSTART.md](docs/QUICKSTART.md)
- Testing on test Pi? → [TESTING_ON_TEST_PI.md](docs/TESTING_ON_TEST_PI.md)
- Setting up test vs production? → [TEST_VS_PRODUCTION.md](docs/TEST_VS_PRODUCTION.md)
- Adding a new meter? → [ADDING_METERS.md](docs/ADDING_METERS.md)
- Need to update production? → [DEPLOYMENT.md - Production Updates](docs/DEPLOYMENT.md#production-updates)
- Something broken? → [TESTING_GUIDE.md - Troubleshooting](docs/TESTING_GUIDE.md#troubleshooting)

---

## Features

- **Multi-meter support**: Monitor multiple meters simultaneously (3-phase and single-phase)
- **15-minute aggregated logging**: Reduces disk usage by 99% while maintaining accuracy
- **Automatic log rotation**: Files rotate at 50,000 rows (~17 months of data)
- **Gzip compression**: Old logs automatically compressed to save space
- **Per-meter organization**: Each meter has its own directory and CSV files
- **Dual Modbus backends**: Choose between `mbpoll` or `pymodbus`
- **Accurate energy calculation**: Trapezoidal integration for three-phase meters
- **Hot-swappable meters**: Enable/disable meters without code changes

## System Architecture

```
+------------------------------------------+
|  Raspberry Pi Gateway                   |
|  - RS485 to USB Adapter                 |
|  - Python 3.x                           |
|  - Modbus RTU Communication             |
|  - NFE Logger Service (systemd)         |
+------------------------------------------+
                    |
        +-----------+-----------+
        |           |           |
    +-------+   +-------+   +-------+
    |Meter 1|   |Meter 2|   |Meter 3|
    |3-phase|   |1-phase|   |1-phase|
    | ID: 1 |   | ID: 2 |   | ID: 3 |
    +-------+   +-------+   +-------+
```

## Quick Start

### Prerequisites
- Raspberry Pi (3B+ or newer recommended)
- Python 3.7+
- RS485 to USB adapter
- Chint DDSU666 meters connected via RS485

### Installation
```bash
# Clone repository
git clone <your-repo-url> nfe-modbus-energy-logger
cd nfe-modbus-energy-logger

# Install dependencies (use --break-system-packages on newer Pi OS)
pip3 install pymodbus pyyaml --break-system-packages

# For mbpoll backend (optional)
sudo apt install mbpoll

# Create directories
mkdir -p data/state

# Test run
python3 -m src.main config/config.dev.yaml
```

### Configuration

Edit `config/config.prod.yaml`:

```yaml
port: /dev/ttyUSB0

modbus:
  backend: pymodbus  # or mbpoll

meters:
  - id: 1
    name: "main_three_phase"
    type: "3phase"
    enabled: true

poll_interval: 10   # Read every 10 seconds
log_interval: 900   # Write to CSV every 15 minutes

logging:
  base_dir: data
  state_dir: data/state
  rotation:
    max_rows: 50000
    compress_old: true
```

## Data Output

### Directory Structure
```
data/
├── meter_001/
│   ├── meter_001_2026-03-19.csv          # Current day
│   └── meter_001_2026-03-18.csv.gz       # Compressed archive
├── meter_002/
│   └── meter_002_2026-03-19.csv
└── state/
    ├── meter_001_state.json
    └── meter_002_state.json
```

### CSV Format (3-Phase)
```
timestamp,meter_id,meter_name,V_L1,V_L2,V_L3,I_L1,I_L2,I_L3,
P_total,P_L1,P_L2,P_L3,PF_total,frequency,energy_total,
E_L1_cal,E_L2_cal,E_L3_cal
```

**Example:**
```
2026-03-19 14:30:15,1,main_three_phase,230.5,231.2,229.8,12.3,11.8,12.1,8.45,2.8,2.9,2.75,0.95,50.0,1234.56,412.3,415.8,406.46
```

**Timestamp:** `YYYY-MM-DD HH:MM:SS` format, using Raspberry Pi's local timezone (typically EAT/UTC+3 for Kenya deployments)

### CSV Format (Single-Phase)
```
timestamp,meter_id,meter_name,V_L1,I_L1,P_total,P_L1,
PF_total,frequency,energy_total
```

**Example:**
```
2026-03-19 14:30:15,2,office_single_phase,230.5,12.3,2.8,2.8,0.95,50.0,456.78
```

**Timestamp:** `YYYY-MM-DD HH:MM:SS` format, using Raspberry Pi's local timezone (typically EAT/UTC+3 for Kenya deployments)

## Meter Register Map & IEEE 754 Scaling

### Three-Phase Meter (DTSU666)
| Parameter | Register | Count | Unit | Scaling |
|-----------|----------|-------|------|---------|
| Voltage (3-phase) | 0x2006 | 3 | V | ÷ 10 |
| Current (3-phase) | 0x200C | 3 | A | ÷ 100 |
| Power (total + 3-phase) | 0x2012 | 4 | kW | ÷ 1000 |
| Power Factor | 0x2020 | 1 | - | ÷ 1000 |
| Frequency | 0x2044 | 1 | Hz | ÷ 100 |
| Energy (cumulative) | 0x4000 | 1 | kWh | None |

### Single-Phase Meter (DDSU666)
| Parameter | Register | Count | Unit | Scaling |
|-----------|----------|-------|------|---------|
| Voltage | 0x2000 | 1 | V | None |
| Current | 0x2002 | 1 | A | None |
| Power | 0x2004 | 1 | W | None (÷1000 for kW) |
| Power Factor | 0x200A | 1 | - | None |
| Frequency | 0x200E | 1 | Hz | None |
| Energy (cumulative) | 0x4000 | 1 | kWh | None |

### IEEE 754 Float Encoding Differences

Both meters store values as **IEEE 754 32-bit floats** (2 Modbus registers each), but they encode values differently:

**Three-Phase (DTSU666):** Stores **scaled integers** as floats
- Example: 230.9V is stored as `2309.0` → Read as float `2309.0` → Divide by 10 → **230.9V**
- Example: 5.25A is stored as `525.0` → Read as float `525.0` → Divide by 100 → **5.25A**
- **Why:** Maintains precision for large power values (up to 100kW+ range)

**Single-Phase (DDSU666):** Stores **actual values** as floats
- Example: 230.9V is stored as `230.9` → Read as float `230.9` → No scaling → **230.9V**
- Example: 5.25A is stored as `5.25` → Read as float `5.25` → No scaling → **5.25A**
- **Why:** Simpler implementation for smaller power range (up to ~20kW)

**Implementation:** See [src/meter_reader.py](src/meter_reader.py) for scaling logic. All values are rounded to 3 decimal places for consistency and to avoid floating-point artifacts.

## Deployment

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for:
- Initial deployment to Raspberry Pi
- Production updates and zero-downtime deployments
- Log upload automation (SCP, email, S3)
- Troubleshooting guide
- Maintenance schedule

## Development

### Project Structure
```
nfe-modbus-energy-logger/
├── config/
│   ├── config.dev.yaml          # Development config
│   └── config.prod.yaml         # Production config
├── src/
│   ├── __init__.py
│   ├── main.py                  # Main application loop
│   ├── meter_reader.py          # Meter abstraction layer
│   ├── energy_calc.py           # Energy integration
│   ├── aggregator.py            # 15-minute buffering
│   ├── rotating_csv_logger.py   # CSV writer with rotation
│   ├── state_manager.py         # State persistence
│   ├── modbus_client.py         # pymodbus wrapper
│   ├── mbpoll_client.py         # mbpoll wrapper
│   └── modbus_factory.py        # Backend selector
├── scripts/
│   └── test_modbus_read.py      # Modbus test utility
├── data/                        # Data directory (gitignored)
├── DEPLOYMENT.md                # Deployment guide
└── README.md                    # This file
```

### Adding a New Meter Type

1. Create a new reader class in `src/meter_reader.py`:
```python
class NewMeterReader(BaseMeterReader):
    REGISTERS = {
        'voltage': (0xXXXX, count),
        # ... other registers
    }

    def read(self, client):
        # Implementation
        pass
```

2. Update the factory function:
```python
def create_meter_reader(meter_config):
    if meter_config['type'] == 'newtype':
        return NewMeterReader(meter_config['id'], meter_config['name'])
    # ... existing types
```

3. Add CSV header in `src/rotating_csv_logger.py`

4. Update config and test

## Performance

### Before (Continuous Logging)
- Poll interval: 2 seconds
- Rows per day: 43,200
- File size per day: ~5 MB
- Annual file size: ~1.8 GB

### After (15-Minute Aggregation)
- Poll interval: 10 seconds (internal)
- Log interval: 15 minutes
- Rows per day: 96
- File size per day: ~10 KB
- Annual file size per meter: ~3.5 MB
- **99% reduction in disk usage**

### Multi-Meter (3 Meters, 1 Year)
- Active CSVs: ~10.5 MB
- Compressed archives: ~2-3 MB
- **Total: ~13-14 MB/year**

## Energy Calculation

### Three-Phase Meters
Uses trapezoidal integration to calculate cumulative energy per phase:

```
E_Ln_cal += (P_last + P_current) / 2 * dt
```

Where:
- `E_Ln_cal`: Calculated energy for phase L1, L2, or L3 (kWh)
- `P_last`: Power from previous reading (kW)
- `P_current`: Power from current reading (kW)
- `dt`: Time delta in hours (with 30-minute safety cap)

### Single-Phase Meters
No calculation needed - uses meter's built-in cumulative energy register directly.

## License

Proprietary - NFE Internal Use Only

## Support

For issues or questions:
1. Check [DEPLOYMENT.md](docs/DEPLOYMENT.md) troubleshooting section
2. Review logs: `sudo journalctl -u meter.service -f`
3. Contact: [Your contact info]

## Version History

- **v2.0.0** (2026-03-19): Multi-meter support, 15-minute aggregation, log rotation
- **v1.0.0** (Initial): Single meter continuous logging
