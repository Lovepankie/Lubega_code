# DLT645 to Modbus Converter — CLI Version

Headless command-line tool for converting Chint DDSU666/DTSU666 meters from DLT645 protocol to Modbus RTU. Designed for Raspberry Pi deployment via SSH.

Supports both:
- **DDSU666** single-phase meters (uses register 0x0006 for address)
- **DTSU666** three-phase meters (uses register 0x002E for address)

## Installation

```bash
# Install dependencies
pip3 install pyserial

# Make executable (optional)
chmod +x converter_cli.py
```

## Quick Start

### Find your serial port
```bash
python3 converter_cli.py list
```

### Convert a meter to Modbus
```bash
# Example: Convert meter with station address 200322016690
python3 converter_cli.py convert --port /dev/ttyUSB0 --station 200322016690
```

### Full process (recommended)
Converts DLT645 → Modbus, scans for current address, and sets new address:

```bash
python3 converter_cli.py full --port /dev/ttyUSB0 --station 200322016690 --address 2
```

## Commands

### `list` — List available serial ports
```bash
python3 converter_cli.py list
```

### `convert` — Convert DLT645 to Modbus
Sends the protocol-switch command to change meter from DLT645 to Modbus RTU.

```bash
python3 converter_cli.py convert --port /dev/ttyUSB0 --station 200322016690
```

**Options:**
- `--port` (required): Serial port (e.g., `/dev/ttyUSB0` or `COM3`)
- `--station` (required): 12-digit DLT645 station address (meter serial number)
- `--baudrate`: DLT645 baud rate (default: 2400)
- `--reverse`: Reverse address bytes (use if conversion fails)

### `scan` — Scan for Modbus device
Scans Modbus addresses 1-247 to find the meter's current address.

```bash
# Scan all addresses (1-247)
python3 converter_cli.py scan --port /dev/ttyUSB0

# Quick scan of specific range (e.g., 90-100)
python3 converter_cli.py scan --port /dev/ttyUSB0 --start 90 --end 100 --timeout 0.05
```

**Options:**
- `--port` (required): Serial port
- `--baudrate`: Modbus baud rate (default: 9600)
- `--start`: Start address (default: 1)
- `--end`: End address (default: 247)
- `--timeout`: Timeout per address in seconds (default: 0.3, lower for faster scans)

### `change` — Change Modbus address
Changes the meter's Modbus slave address.

```bash
# Single-phase meter (DDSU666)
python3 converter_cli.py change --port /dev/ttyUSB0 --current 1 --new 10 --type 1phase

# Three-phase meter (DTSU666)
python3 converter_cli.py change --port /dev/ttyUSB0 --current 1 --new 100 --type 3phase
```

**Options:**
- `--port` (required): Serial port
- `--current` (required): Current Modbus address
- `--new` (required): New Modbus address (1-247)
- `--type`: Meter type - `1phase` (DDSU666) or `3phase` (DTSU666) (default: 1phase)
- `--baudrate`: Modbus baud rate (default: 9600)

### `full` — Full process (convert + scan + change)
**Recommended for new meter setup.** Performs all steps in sequence:
1. Converts DLT645 → Modbus
2. Scans to find current Modbus address
3. Changes to target address

```bash
# Single-phase meter (DDSU666) - set to address 10
python3 converter_cli.py full --port /dev/ttyUSB0 --station 200322016690 --address 10 --type 1phase

# Three-phase meter (DTSU666) - set to address 100
python3 converter_cli.py full --port /dev/ttyUSB0 --station 200322016690 --address 100 --type 3phase
```

**Options:**
- `--port` (required): Serial port
- `--station` (required): 12-digit DLT645 station address
- `--address` (required): Target Modbus address
- `--type`: Meter type - `1phase` (DDSU666) or `3phase` (DTSU666) (default: 1phase)
- `--dlt-baud`: DLT645 baud rate (default: 2400)
- `--modbus-baud`: Modbus baud rate (default: 9600)
- `--reverse`: Reverse address bytes

## Protocol Details

### DLT645 Mode (Before Conversion)
- **Baud rate**: 2400
- **Format**: 8E1 (8 data bits, EVEN parity, 1 stop bit)
- **Addressing**: 12-digit station address (meter serial number)

### Modbus RTU Mode (After Conversion)
- **Baud rate**: 9600
- **Format**: 8N2 (8 data bits, NO parity, 2 stop bits)
- **Addressing**: Slave address 1-247

## Finding Station Address

The 12-digit station address is the meter's serial number, typically printed on the meter's label or display.

If unknown, you can:
1. Check the meter's LCD display (often shows on startup)
2. Check the meter's label/sticker
3. Try common test addresses like `200322016690`

## Troubleshooting

### No response during conversion
- **Check wiring**: Ensure A/B terminals are correctly connected
- **Check station address**: Must match meter's 12-digit serial number
- **Try reverse flag**: Some firmware versions need `--reverse`
  ```bash
  python3 converter_cli.py convert --port /dev/ttyUSB0 --station 200322016690 --reverse
  ```
- **Check baud rate**: Default is 2400, but some meters use different rates

### No device found during scan
- **Meter still in DLT645 mode**: Run `convert` command first
- **Wrong baud rate**: Try `--baudrate 2400` or other rates
- **Wiring issue**: Check RS485 A/B connections

### Permission denied on Linux
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and back in for changes to take effect

# Or run with sudo (not recommended)
sudo python3 converter_cli.py ...
```

## Example Workflow

### Single-phase meter (DDSU666)
Convert a new single-phase meter and set to address 10:

```bash
# 1. Check available ports
python3 converter_cli.py list

# 2. Run full process (easiest)
python3 converter_cli.py full --port /dev/ttyUSB0 --station 200322016690 --address 10 --type 1phase

# 3. Verify meter responds at new address
# (Use your modbus client or energy logger)
```

### Three-phase meter (DTSU666)
Convert a new three-phase meter and set to address 100:

```bash
# 1. Check available ports
python3 converter_cli.py list

# 2. Run full process (easiest)
python3 converter_cli.py full --port /dev/ttyUSB0 --station 200322016690 --address 100 --type 3phase

# 3. Verify meter responds at new address
# (Use your modbus client or energy logger)
```

## Technical Details

### Protocol Conversion
The tool sends a DLT645 "protocol switch" command (Control Code 0x14) with magic data bytes that tell the meter to switch to Modbus RTU mode. This is a one-time operation.

### Address Change
Uses Modbus Function Code 16 (Write Multiple Registers) to write the new address to the appropriate register:
- **DDSU666 (single-phase)**: Register 0x0006 holds the Modbus address
- **DTSU666 (three-phase)**: Register 0x002E holds the Modbus address

**Important**: Always specify the correct `--type` parameter when changing addresses, otherwise the tool will write to the wrong register and the address change will not take effect.

### Modbus Functions Used
- **FC-04**: Read Input Registers (for scanning)
- **FC-16**: Write Multiple Registers (for address change)

## Related Files
- `converter.py` — GUI version (tkinter)
- `converter_cli.py` — This CLI version
