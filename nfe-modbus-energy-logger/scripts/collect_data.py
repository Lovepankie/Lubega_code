#!/usr/bin/env python3
"""
DTSU666 Bypass Scenario Data Collection Script
Reads 3-phase meter every 5 seconds and saves to CSV with a scenario label.

Usage:
    cd ~/iot_meter
    python3 scripts/collect_data.py --label normal        --duration 900
    python3 scripts/collect_data.py --label bypass_red    --duration 2700
    python3 scripts/collect_data.py --label bypass_yellow --duration 2700
    python3 scripts/collect_data.py --label bypass_blue   --duration 2700
    python3 scripts/collect_data.py --label bypass_red_yellow --duration 2700
    python3 scripts/collect_data.py --label bypass_red_blue   --duration 2700
    python3 scripts/collect_data.py --label bypass_blue_yellow --duration 2700
    python3 scripts/collect_data.py --label bypass_all    --duration 2700

Labels:
    0 = normal  (baseline / no bypass)
    1 = any bypass scenario
"""
import argparse
import csv
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import yaml
from src.modbus_factory import get_client
from src.meter_reader import ThreePhaseMeterReader

CONFIG_PATH     = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.prod.yaml')
SLAVE_ID        = 1     # DTSU666 factory default slave ID
SAMPLE_INTERVAL = 5   # seconds

# Numeric label: normal=0, any bypass=1
LABEL_MAP = {
    "normal": 0,
    "bypass_red": 1,
    "bypass_yellow": 1,
    "bypass_blue": 1,
    "bypass_red_yellow": 1,
    "bypass_red_blue": 1,
    "bypass_blue_yellow": 1,
    "bypass_all": 1,
}

FIELDNAMES = [
    "timestamp", "scenario", "label",
    "V_L1", "V_L2", "V_L3",
    "I_L1", "I_L2", "I_L3",
    "P_total", "P_L1", "P_L2", "P_L3",
    "PF_total",
    "frequency",
    "energy_total",
]


def collect(label, duration_secs, output_path, port_override=None):
    cfg = yaml.safe_load(open(CONFIG_PATH))
    if port_override:
        cfg["port"] = port_override

    numeric_label = LABEL_MAP.get(label, 1)

    print("=" * 65)
    print(f"  Data Collection  |  Scenario: {label}  |  Label: {numeric_label}")
    print(f"  Duration: {duration_secs}s ({duration_secs/60:.0f} min)  |  Output: {output_path}")
    print("=" * 65)

    try:
        client = get_client(cfg)
    except Exception as e:
        print(f"ERROR: Cannot connect — {e}")
        print("  -> Is the RS485-to-USB adapter plugged in?")
        sys.exit(1)

    reader = ThreePhaseMeterReader(meter_id=SLAVE_ID, meter_name="DTSU666")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    file_exists = os.path.isfile(output_path)

    with open(output_path, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        start = time.time()
        sample_count = 0
        error_count = 0

        try:
            while (time.time() - start) < duration_secs:
                data = reader.read(client)

                if data is None:
                    error_count += 1
                    print(f"  WARNING: Read failed (total errors: {error_count})")
                    time.sleep(SAMPLE_INTERVAL)
                    continue

                row = {
                    "timestamp":    datetime.now().isoformat(),
                    "scenario":     label,
                    "label":        numeric_label,
                    "V_L1":         data["V_L1"],
                    "V_L2":         data["V_L2"],
                    "V_L3":         data["V_L3"],
                    "I_L1":         data["I_L1"],
                    "I_L2":         data["I_L2"],
                    "I_L3":         data["I_L3"],
                    "P_total":      data["P_total"],
                    "P_L1":         data["P_L1"],
                    "P_L2":         data["P_L2"],
                    "P_L3":         data["P_L3"],
                    "PF_total":     data["PF_total"],
                    "frequency":    data["frequency"],
                    "energy_total": data["energy_total"],
                }

                writer.writerow(row)
                csvfile.flush()
                sample_count += 1

                elapsed   = time.time() - start
                remaining = duration_secs - elapsed
                print(
                    f"[{sample_count:4d}] {row['timestamp']}  "
                    f"V={data['V_L1']:.1f}/{data['V_L2']:.1f}/{data['V_L3']:.1f}V  "
                    f"I={data['I_L1']:.3f}/{data['I_L2']:.3f}/{data['I_L3']:.3f}A  "
                    f"P={data['P_total']:.3f}kW  PF={data['PF_total']:.3f}  "
                    f"Remaining: {remaining:.0f}s"
                )

                time.sleep(SAMPLE_INTERVAL)

        except KeyboardInterrupt:
            print(f"\nStopped by user.")

    print(f"\nDone. {sample_count} samples saved to {output_path}  ({error_count} read errors)")


def main():
    parser = argparse.ArgumentParser(description="DTSU666 bypass scenario data collector")
    parser.add_argument("--label", required=True,
                        choices=list(LABEL_MAP.keys()),
                        help="Scenario label for this collection run")
    parser.add_argument("--duration", type=int, default=900,
                        help="Duration in seconds (default: 900 = 15 min)")
    parser.add_argument("--output", default=None,
                        help="Output CSV path (default: data/<label>.csv)")
    parser.add_argument("--port", default=None,
                        help="Override serial port (default: from config.prod.yaml)")
    args = parser.parse_args()

    output = args.output or os.path.join(
        os.path.dirname(__file__), '..', 'data', f"{args.label}.csv"
    )
    collect(args.label, args.duration, output, args.port)


if __name__ == "__main__":
    main()
