import time
import yaml
import sys
import os
from datetime import datetime

from .modbus_factory import get_client
from .meter_reader import create_meter_reader
from .energy_calc import EnergyCalc
from .aggregator import FifteenMinuteAggregator
from .rotating_csv_logger import RotatingCSVLogger
from .state_manager import load, save


# -------------------------------
# Load config (dev or prod)
# -------------------------------
config_file = sys.argv[1] if len(sys.argv) > 1 else "config/config.dev.yaml"
cfg = yaml.safe_load(open(config_file))


# -------------------------------
# Init Modbus client (shared)
# -------------------------------
client = get_client(cfg)


# -------------------------------
# Create directories
# -------------------------------
os.makedirs(cfg['logging']['base_dir'], exist_ok=True)
os.makedirs(cfg['logging']['state_dir'], exist_ok=True)


# -------------------------------
# Init per-meter components
# -------------------------------
meters = {}  # meter_id -> {reader, calc, aggregator, logger, state_file}

for meter_cfg in cfg['meters']:
    if not meter_cfg.get('enabled', True):
        print(f"⏭️  Skipping disabled meter: {meter_cfg['name']}")
        continue

    meter_id = meter_cfg['id']
    meter_name = meter_cfg['name']
    meter_type = meter_cfg['type']

    # Create meter reader
    reader = create_meter_reader(meter_cfg)

    # Load state
    state_file = f"{cfg['logging']['state_dir']}/meter_{meter_id:03d}_state.json"
    state = load(state_file)

    # Create energy calculator (only for three-phase meters)
    # Single-phase meters use the meter's built-in cumulative energy
    if meter_type == '3phase':
        calc = EnergyCalc(state, phase_count=3)
    else:
        calc = None  # No calculation needed for single-phase

    # Create 15-minute aggregator
    aggregator = FifteenMinuteAggregator(log_interval=cfg['log_interval'])

    # Create rotating CSV logger
    logger = RotatingCSVLogger(
        meter_id=meter_id,
        meter_name=meter_name,
        meter_type=meter_type,
        base_dir=cfg['logging']['base_dir'],
        max_rows=cfg['logging']['rotation']['max_rows'],
        compress=cfg['logging']['rotation']['compress_old'],
        log_calculated_energy=cfg['logging'].get('log_calculated_energy', True)
    )

    meters[meter_id] = {
        'reader': reader,
        'calc': calc,
        'aggregator': aggregator,
        'logger': logger,
        'state_file': state_file,
        'name': meter_name,
        'type': meter_type
    }

    print(f"✅ Initialized meter {meter_id} ({meter_name}, {meter_type})")


# -------------------------------
# Billing snapshot helper functions
# -------------------------------
def should_take_billing_snapshot(now_dt, last_check):
    """Check if we've crossed into 1st of month at midnight"""
    if now_dt.day != 1:
        return False

    # Check if we're within first 15 minutes of 1st day of month
    if now_dt.hour == 0 and now_dt.minute < 15:
        # Haven't taken snapshot yet this month
        if last_check is None or last_check.month != now_dt.month:
            return True

    return False


def take_billing_snapshot(meter_id, components, now, now_dt):
    """Take immediate billing snapshot outside normal 15-min cycle"""
    reader = components['reader']
    calc = components['calc']
    logger = components['logger']
    state_file = components['state_file']

    # Read from meter immediately
    reading = reader.read(client)

    if reading is None:
        print(f"❌ Billing snapshot failed for meter {meter_id}: Read error")
        return

    # Determine quality marker based on how close to midnight
    minutes_past_midnight = now_dt.hour * 60 + now_dt.minute
    if minutes_past_midnight <= 1:
        billing_marker = 'BILL-EXACT'
    elif minutes_past_midnight <= 5:
        billing_marker = 'BILL-APPROX'
    else:
        billing_marker = 'BILL-LATE'

    # Build billing row (similar to normal logging, but with billing_marker)
    billing_row = {
        'timestamp': now_dt.strftime('%Y-%m-%d %H:%M:%S'),
        'billing_marker': billing_marker,
        **reading  # All meter readings
    }

    # Add calculated energy if three-phase
    if calc is not None:
        calc_state = calc.state()
        billing_row.update(calc_state)
        save(state_file, calc_state)

    # Write to CSV immediately
    logger.log(billing_row)

    print(f"✅ Billing snapshot for meter {meter_id}: {billing_marker} - energy_total={reading['energy_total']:.2f} kWh")


# -------------------------------
# Main polling loop
# -------------------------------
print(f"\n🚀 Starting multi-meter logger")
print(f"   Poll interval: {cfg['poll_interval']}s")
print(f"   Log interval: {cfg['log_interval']}s ({cfg['log_interval']//60} minutes)")
print(f"   Active meters: {len(meters)}\n")

# Track last billing check (persistent across loop iterations)
last_billing_check = None

while True:
    try:
        now = time.time()
        now_dt = datetime.fromtimestamp(now)

        # Check for month boundary crossing (billing snapshot)
        if should_take_billing_snapshot(now_dt, last_billing_check):
            print(f"\n💰 Billing snapshot triggered at {now_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            for meter_id, components in meters.items():
                take_billing_snapshot(meter_id, components, now, now_dt)
            last_billing_check = now_dt

        # Poll all meters
        for meter_id, components in meters.items():
            reader = components['reader']
            calc = components['calc']
            aggregator = components['aggregator']
            logger = components['logger']
            state_file = components['state_file']

            # Read from meter
            reading = reader.read(client)

            if reading is None:
                print(f"⚠️  Meter {meter_id} ({components['name']}): Read failed, skipping...")
                continue

            # Update energy calculation (only for three-phase meters)
            if calc is not None and reading['phases'] is not None:
                calc.update(reading['phases'], now)

            # Add to aggregation buffer
            aggregator.add_reading(reading, now)

            # Check if it's time to log (every 15 minutes)
            if aggregator.should_log(now):
                # Get aggregated data (with or without energy calc state)
                calc_state = calc.state() if calc is not None else {}
                aggregated = aggregator.get_aggregated(calc_state)

                # Use human-readable timestamp instead of epoch
                aggregated['timestamp'] = datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')
                aggregated['billing_marker'] = ''  # Empty for non-billing rows

                # Write to CSV
                logger.log(aggregated)

                # Persist state (only for three-phase meters with calc)
                if calc is not None:
                    save(state_file, calc.state())

                # Clear buffer
                aggregator.clear_buffer(now)

                # Dynamic log interval message
                log_interval_minutes = cfg['log_interval'] // 60
                if log_interval_minutes >= 1:
                    interval_str = f"{log_interval_minutes}-min"
                else:
                    interval_str = f"{cfg['log_interval']}-sec"
                print(f"📊 Meter {meter_id} ({components['name']}): Logged {interval_str} aggregation")

        # Wait for next poll cycle
        time.sleep(cfg['poll_interval'])

    except Exception as e:
        print(f"❌ Error in main loop: {e}")
        time.sleep(2)
