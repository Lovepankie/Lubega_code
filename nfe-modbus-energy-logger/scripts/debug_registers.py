import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.modbus_client import ModbusClient
import yaml
import struct

cfg = yaml.safe_load(open("config/config.prod.yaml"))
# Force pymodbus for this debug
cfg['modbus']['backend'] = 'pymodbus'
client = ModbusClient(cfg)

print("Raw Register Debug - Meter ID: 1")
print("=" * 60)

# Read voltage registers (should be ~230V)
print("\nVoltage Register 0x2006 (expecting ~230V):")
rr = client.client.read_input_registers(address=0x2006, count=2, device_id=1)
if not rr.isError():
    regs = rr.registers
    print(f"  Raw registers: {regs}")
    print(f"  Hex: {[hex(r) for r in regs]}")

    # Try different decodings
    print(f"  Big-endian (>HH >f):     {struct.unpack('>f', struct.pack('>HH', regs[0], regs[1]))[0]:.2f}")
    print(f"  Swapped (>HH >f):        {struct.unpack('>f', struct.pack('>HH', regs[1], regs[0]))[0]:.2f}")
    print(f"  Little-endian (<HH <f):  {struct.unpack('<f', struct.pack('<HH', regs[0], regs[1]))[0]:.2f}")
    print(f"  Mixed (>HH <f):          {struct.unpack('<f', struct.pack('>HH', regs[0], regs[1]))[0]:.2f}")
    print(f"  Mixed swap (>HH <f):     {struct.unpack('<f', struct.pack('>HH', regs[1], regs[0]))[0]:.2f}")
    print(f"  As 16-bit int /10:       {regs[0]/10:.2f}")
    print(f"  As 32-bit int /100:      {(regs[0] << 16 | regs[1])/100:.2f}")

# Read frequency (should be ~50Hz)
print("\nFrequency Register 0x2044 (expecting ~50Hz):")
rr = client.client.read_input_registers(address=0x2044, count=2, device_id=1)
if not rr.isError():
    regs = rr.registers
    print(f"  Raw registers: {regs}")
    print(f"  Hex: {[hex(r) for r in regs]}")

    print(f"  Big-endian (>HH >f):     {struct.unpack('>f', struct.pack('>HH', regs[0], regs[1]))[0]:.2f}")
    print(f"  Swapped (>HH >f):        {struct.unpack('>f', struct.pack('>HH', regs[1], regs[0]))[0]:.2f}")
    print(f"  Little-endian (<HH <f):  {struct.unpack('<f', struct.pack('<HH', regs[0], regs[1]))[0]:.2f}")
    print(f"  Mixed (>HH <f):          {struct.unpack('<f', struct.pack('>HH', regs[0], regs[1]))[0]:.2f}")
    print(f"  Mixed swap (>HH <f):     {struct.unpack('<f', struct.pack('>HH', regs[1], regs[0]))[0]:.2f}")

print("\n" + "=" * 60)
