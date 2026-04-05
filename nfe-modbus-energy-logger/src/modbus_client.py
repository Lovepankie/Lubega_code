from pymodbus.client import ModbusSerialClient
import struct

class ModbusClient:
    def __init__(self, cfg):
        self.client = ModbusSerialClient(
            port=cfg["port"],
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=1
        )
        self.client.connect()

    def _decode_float(self, registers):
        # Decode as big-endian float
        raw = struct.pack('>HH', registers[0], registers[1])
        value = struct.unpack('>f', raw)[0]
        return value

    def read_input_float(self, address, count, slave):
        rr = self.client.read_input_registers(address=address, count=count*2, device_id=slave)
        if rr.isError():
            return None

        values = []
        for i in range(0, len(rr.registers), 2):
            values.append(self._decode_float(rr.registers[i:i+2]))

        return values

    def read_holding_float(self, address, count, slave):
        rr = self.client.read_holding_registers(address=address, count=count*2, device_id=slave)
        if rr.isError():
            return None

        values = []
        for i in range(0, len(rr.registers), 2):
            values.append(self._decode_float(rr.registers[i:i+2]))

        return values