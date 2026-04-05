#!/usr/bin/env python3
"""
Quick Modbus connectivity test - run this first to confirm meter communication.
Uses the project's existing ModbusClient and ThreePhaseMeterReader.

Usage:
    cd ~/iot_meter
    python3 scripts/modbus_test.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import yaml
from src.modbus_factory import get_client
from src.meter_reader import ThreePhaseMeterReader

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.prod.yaml')
SLAVE_ID = 1     # DTSU666 three-phase meter address (factory default)


def test_connection():
    print("=" * 60)
    print("  DTSU666 Modbus Connectivity Test")
    print("=" * 60)

    # Load config
    try:
        cfg = yaml.safe_load(open(CONFIG_PATH))
    except FileNotFoundError:
        print(f"ERROR: Config not found at {CONFIG_PATH}")
        sys.exit(1)

    port = cfg.get("port", "/dev/ttyUSB0")
    print(f"Port     : {port}")
    print(f"Slave ID : {SLAVE_ID}")
    print(f"Baudrate : 9600  Stopbits: 2  Parity: N")
    print("-" * 60)

    # Connect
    try:
        client = get_client(cfg)
    except Exception as e:
        print(f"\nERROR: Cannot open {port}")
        print(f"  Detail: {e}")
        print("\n  -> Is the RS485-to-USB adapter plugged in?")
        print("  -> Run:  ls /dev/ttyUSB*  to check")
        return False

    # Read
    reader = ThreePhaseMeterReader(meter_id=SLAVE_ID, meter_name="DTSU666")
    data = reader.read(client)

    if data is None:
        print("\nERROR: Meter not responding.")
        print("  -> Check RS485 wiring: A+ to Pin 15, B- to Pin 16 on meter")
        print("  -> Check slave ID is 100 (default DTSU666 factory setting)")
        return False

    print(f"\n{'Measurement':<25} {'Value'}")
    print("-" * 45)
    print(f"{'Voltage A':<25} {data['V_L1']:.1f} V")
    print(f"{'Voltage B':<25} {data['V_L2']:.1f} V")
    print(f"{'Voltage C':<25} {data['V_L3']:.1f} V")
    print(f"{'Current A':<25} {data['I_L1']:.3f} A")
    print(f"{'Current B':<25} {data['I_L2']:.3f} A")
    print(f"{'Current C':<25} {data['I_L3']:.3f} A")
    print(f"{'Power Total':<25} {data['P_total']:.3f} kW")
    print(f"{'Power A':<25} {data['P_L1']:.3f} kW")
    print(f"{'Power B':<25} {data['P_L2']:.3f} kW")
    print(f"{'Power C':<25} {data['P_L3']:.3f} kW")
    print(f"{'Power Factor':<25} {data['PF_total']:.3f}")
    print(f"{'Frequency':<25} {data['frequency']:.2f} Hz")
    print(f"{'Energy Total':<25} {data['energy_total']:.3f} kWh")

    # Sanity checks
    print("\n--- Sanity Checks ---")
    pf = data['PF_total']
    freq = data['frequency']
    va = data['V_L1']

    pf_ok   = -1.0 <= pf <= 1.0
    freq_ok = 45.0 <= freq <= 55.0
    volt_ok = 180.0 <= va <= 260.0

    print(f"  Power Factor in [-1, 1] : {'PASS' if pf_ok   else 'FAIL'} ({pf})")
    print(f"  Frequency 45-55 Hz      : {'PASS' if freq_ok else 'FAIL'} ({freq} Hz)")
    print(f"  Voltage A 180-260 V     : {'PASS' if volt_ok else 'FAIL'} ({va} V)")

    if pf_ok and freq_ok and volt_ok:
        print("\n✓ All checks passed — meter is communicating correctly.\n")
        return True
    else:
        print("\n✗ Some checks failed — verify wiring and register scaling.\n")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
