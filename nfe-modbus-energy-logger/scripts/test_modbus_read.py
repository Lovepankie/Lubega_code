import sys
import os
# Add parent directory to path so we can import src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.modbus_factory import get_client
from src.meter_reader import ThreePhaseMeterReader
import yaml

cfg = yaml.safe_load(open("config/config.prod.yaml"))
client = get_client(cfg)

# Use meter reader to get properly scaled values
reader = ThreePhaseMeterReader(meter_id=1, meter_name="test_meter")

print("Testing Modbus reads for Meter ID: 1")
print("=" * 50)

data = reader.read(client)

if data:
    print(f"Voltage (V):        [{data['V_L1']:.1f}, {data['V_L2']:.1f}, {data['V_L3']:.1f}] V")
    print(f"Current (I):        [{data['I_L1']:.1f}, {data['I_L2']:.1f}, {data['I_L3']:.1f}] A")
    print(f"Power (P):          [{data['P_total']:.1f}, {data['P_L1']:.1f}, {data['P_L2']:.1f}, {data['P_L3']:.1f}] kW")
    print(f"Power Factor (PF):  [{data['PF_total']:.2f}]")
    print(f"Frequency (F):      [{data['frequency']:.2f}] Hz")
    print(f"Energy (E):         [{data['energy_total']:.2f}] kWh")
    print("=" * 50)
    print("✅ Meter reading successful!")
else:
    print("❌ Meter reading failed!")
