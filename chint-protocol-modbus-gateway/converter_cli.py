#!/usr/bin/env python3
"""
DLT645 to Modbus Converter — CLI Version
For headless operation on Raspberry Pi via SSH
"""

import argparse
import time
import struct
import serial
import serial.tools.list_ports
import sys


# ─────────────────────────── CRC / Modbus helpers ────────────────────────────

def _calculate_crc(data: bytes) -> int:
    """Modbus CRC-16."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc


def _raw_change_slave_address(port: str, baudrate: int,
                               current_address: int, new_address: int,
                               meter_type: str = "1phase") -> None:
    """Write Modbus FC-16 to change slave address.

    Args:
        port: Serial port
        baudrate: Modbus baud rate
        current_address: Current slave address
        new_address: New slave address
        meter_type: "1phase" (uses 0x0006) or "3phase" (uses 0x002E)
    """
    # Select register based on meter type
    if meter_type == "3phase":
        start_reg = 0x002E  # DTSU666 three-phase register
        meter_name = "DTSU666 (3-phase)"
    else:
        start_reg = 0x0006  # DDSU666 single-phase register
        meter_name = "DDSU666 (1-phase)"

    print(f"📡 Opening {port} @ {baudrate} baud (Modbus mode)...")
    print(f"   Meter type: {meter_name}")
    print(f"   Address register: 0x{start_reg:04X}")

    client = serial.Serial(
        port,
        baudrate=baudrate,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_TWO,
        timeout=1,
    )
    try:
        fc = 0x10  # FC-16: Write Multiple Registers
        reg_count = 0x0001
        byte_count = 0x02
        request = struct.pack(
            ">B B H H B H",
            current_address, fc, start_reg, reg_count, byte_count, new_address,
        )
        crc = _calculate_crc(request)
        request += struct.pack("BB", crc & 0xFF, (crc >> 8) & 0xFF)

        print(f"📤 TX: {request.hex()}")
        client.write(request)
        time.sleep(0.5)

        resp = client.read(client.in_waiting or 1)
        if resp:
            print(f"📥 RX: {resp.hex()}")
            print(f"✅ Address changed: {current_address} → {new_address}")
        else:
            print("⚠️  No response received (change may still have succeeded)")
    finally:
        client.close()


def _probe_modbus_address(port: str, baudrate: int,
                           scan_range: range = range(1, 248),
                           timeout: float = 0.3) -> int | None:
    """Scan Modbus addresses and return the first one that responds.
    Sends FC-04 (Read Input Registers) to each address.
    Returns the responding address, or None if nothing found.
    """
    print(f"🔍 Scanning Modbus addresses {scan_range.start}–{scan_range.stop - 1}...")
    print(f"📡 Opening {port} @ {baudrate} baud (Modbus mode)...")

    client = serial.Serial(
        port,
        baudrate=baudrate,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_TWO,
        timeout=timeout,
    )
    try:
        for addr in scan_range:
            # FC-04: read 1 input register at 0x0000
            req = struct.pack(">BBHH", addr, 0x04, 0x0000, 0x0001)
            crc = _calculate_crc(req)
            req += struct.pack("BB", crc & 0xFF, (crc >> 8) & 0xFF)
            client.reset_input_buffer()
            client.write(req)
            time.sleep(timeout)
            resp = client.read(client.in_waiting or 1)
            if resp and resp[0] == addr and (resp[1] == 0x04 or resp[1] == 0x84):
                print(f"✅ Found device at Modbus address {addr}")
                return addr

            # Progress indicator every 50 addresses
            if addr % 50 == 0:
                print(f"   ... checked up to address {addr}")

        print("❌ No Modbus device responded")
        return None
    finally:
        client.close()


# ─────────────────────────── DLT645 helpers ──────────────────────────────────

def _calculate_checksum(data: bytes) -> int:
    """DLT645 checksum: simple sum modulo 256."""
    return sum(data) % 256


def _construct_frame(station_addr: str, reverse: bool = False) -> bytes:
    """Build a DL/T 645 protocol-switch frame.

    Frame structure:
    - Preamble: FE FE FE FE (wake-up bytes)
    - Start: 68
    - Address: 6 bytes (12-digit station address as hex)
    - Start: 68
    - Control: 14 (WRITE command)
    - Length: 0E (14 bytes)
    - Data: Magic protocol-switch command
    - Checksum: Sum of all bytes from first 68 to data
    - End: 16
    """
    preamble = b"\xFE\xFE\xFE\xFE"
    start = b"\x68"
    addr = bytes.fromhex(station_addr)
    if reverse:
        addr = addr[::-1]
    ctrl = b"\x14"
    length = b"\x0E"
    data = bytes.fromhex("3333353D35333333333333333333")
    body = start + addr + start + ctrl + length + data
    cs = _calculate_checksum(body)
    return preamble + body + bytes([cs]) + b"\x16"


# ─────────────────────────── Port detection ──────────────────────────────────

def list_serial_ports() -> list[str]:
    """Return all available serial port names (Windows + Linux)."""
    ports = serial.tools.list_ports.comports()
    return sorted(p.device for p in ports)


# ─────────────────────────── Protocol conversion ─────────────────────────────

def convert_protocol(port: str, station_addr: str, baudrate: int = 2400,
                     reverse: bool = False) -> bool:
    """Convert a meter from DLT645 to Modbus protocol.

    Args:
        port: Serial port (e.g., /dev/ttyUSB0 or COM3)
        station_addr: 12-digit meter station address
        baudrate: DLT645 baud rate (default: 2400)
        reverse: Reverse address bytes (default: False)

    Returns:
        True if conversion succeeded, False otherwise
    """
    print(f"🔄 Converting DLT645 → Modbus")
    print(f"   Station: {station_addr}")
    print(f"   Port: {port}")
    print(f"   Baud: {baudrate}")
    print(f"   Reverse: {reverse}")
    print()

    # Validate station address
    if len(station_addr) != 12 or not station_addr.isdigit():
        print("❌ Error: Station address must be exactly 12 digits")
        return False

    # Open serial port in DLT645 mode (EVEN parity)
    print(f"📡 Opening {port} @ {baudrate} baud (DLT645 mode: 8E1)...")
    try:
        ser = serial.Serial(
            port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_EVEN,
            stopbits=serial.STOPBITS_ONE,
            timeout=2,
        )
    except serial.SerialException as e:
        print(f"❌ Failed to open port: {e}")
        return False

    try:
        # Flush any stale data
        if ser.in_waiting:
            stale = ser.read(ser.in_waiting)
            print(f"🗑️  Flushed {len(stale)} stale bytes")

        # Attempt 1: Standard conversion
        print("\n📤 Attempt 1: Sending protocol-switch frame...")
        frame = _construct_frame(station_addr, reverse)
        print(f"   TX: {frame.hex()}")
        ser.write(frame)
        time.sleep(2.0)

        if ser.in_waiting:
            resp = ser.read(ser.in_waiting)
            print(f"   📥 RX: {resp.hex()}")
            print("✅ Protocol conversion successful!")
            return True

        print("   ⚠️  No response")

        # Attempt 2: Toggle reverse flag
        print(f"\n📤 Attempt 2: Retrying with reverse={not reverse}...")
        frame = _construct_frame(station_addr, not reverse)
        print(f"   TX: {frame.hex()}")
        ser.write(frame)
        time.sleep(2.0)

        if ser.in_waiting:
            resp = ser.read(ser.in_waiting)
            print(f"   📥 RX: {resp.hex()}")
            print("✅ Protocol conversion successful!")
            return True

        print("   ⚠️  No response")

        # Attempt 3: Extended timing
        print("\n📤 Attempt 3: Retrying with extended timing (5s)...")
        frame = _construct_frame(station_addr, reverse)
        print(f"   TX: {frame.hex()}")
        ser.write(frame)
        time.sleep(5.0)

        if ser.in_waiting:
            resp = ser.read(ser.in_waiting)
            print(f"   📥 RX: {resp.hex()}")
            print("✅ Protocol conversion successful!")
            return True

        print("   ⚠️  No response")
        print("\n❌ Protocol conversion failed")
        print("   Check: wiring, station address, baud rate")
        return False

    finally:
        ser.close()


# ─────────────────────────── CLI commands ────────────────────────────────────

def cmd_list_ports():
    """List available serial ports."""
    ports = list_serial_ports()
    if ports:
        print(f"Found {len(ports)} serial port(s):")
        for p in ports:
            print(f"  - {p}")
    else:
        print("No serial ports detected")


def cmd_convert(args):
    """Convert DLT645 meter to Modbus."""
    success = convert_protocol(
        port=args.port,
        station_addr=args.station,
        baudrate=args.baudrate,
        reverse=args.reverse
    )
    sys.exit(0 if success else 1)


def cmd_scan(args):
    """Scan for Modbus device."""
    found = _probe_modbus_address(
        port=args.port,
        baudrate=args.baudrate,
        scan_range=range(args.start, args.end + 1),
        timeout=args.timeout
    )

    if found is not None:
        print(f"\n✅ Meter is at Modbus address: {found}")
        sys.exit(0)
    else:
        print("\n❌ No device found")
        print("   → Device may still be in DLT645 mode")
        print("   → Run 'convert' command first")
        sys.exit(1)


def cmd_change(args):
    """Change Modbus address."""
    _raw_change_slave_address(
        port=args.port,
        baudrate=args.baudrate,
        current_address=args.current,
        new_address=args.new,
        meter_type=args.type
    )


def cmd_full(args):
    """Full process: convert + scan + change address."""
    print("═══ FULL PROCESS STARTED ═══\n")

    # Step 1: Convert protocol
    print("[1/3] Converting DLT645 → Modbus\n")
    success = convert_protocol(
        port=args.port,
        station_addr=args.station,
        baudrate=args.dlt_baud,
        reverse=args.reverse
    )

    if not success:
        print("\n⚠️  Conversion uncertain — proceeding anyway...")

    print("\n" + "─" * 50)
    time.sleep(1)

    # Step 2: Scan for current address
    print("\n[2/3] Scanning for Modbus device\n")
    current_addr = _probe_modbus_address(
        port=args.port,
        baudrate=args.modbus_baud,
        scan_range=range(1, 248),
        timeout=0.3
    )

    if current_addr is None:
        print("\n⚠️  No device found — assuming address 1")
        current_addr = 1

    print("\n" + "─" * 50)
    time.sleep(1)

    # Step 3: Change address
    print(f"\n[3/3] Changing Modbus address: {current_addr} → {args.address}\n")
    _raw_change_slave_address(
        port=args.port,
        baudrate=args.modbus_baud,
        current_address=current_addr,
        new_address=args.address,
        meter_type=args.type
    )

    print("\n═══ FULL PROCESS COMPLETE ═══")
    print(f"\n🎉 Meter should now be at Modbus address {args.address}")
    print(f"   Protocol: Modbus RTU")
    print(f"   Baud: {args.modbus_baud}")
    print(f"   Format: 8N2 (8 data bits, no parity, 2 stop bits)")


# ─────────────────────────── Main entry point ────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="DLT645 to Modbus converter — CLI tool for Chint DDSU666/DTSU666 meters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available serial ports
  %(prog)s list

  # Convert DLT645 to Modbus (station address: 200322016690)
  %(prog)s convert --port /dev/ttyUSB0 --station 200322016690

  # Scan for Modbus device
  %(prog)s scan --port /dev/ttyUSB0

  # Change single-phase meter address from 1 to 10
  %(prog)s change --port /dev/ttyUSB0 --current 1 --new 10 --type 1phase

  # Change three-phase meter address from 1 to 100
  %(prog)s change --port /dev/ttyUSB0 --current 1 --new 100 --type 3phase

  # Full process for single-phase meter: convert + scan + set to address 10
  %(prog)s full --port /dev/ttyUSB0 --station 200322016690 --address 10 --type 1phase

  # Full process for three-phase meter: convert + scan + set to address 100
  %(prog)s full --port /dev/ttyUSB0 --station 200322016690 --address 100 --type 3phase
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # List ports command
    subparsers.add_parser('list', help='List available serial ports')

    # Convert command
    p_convert = subparsers.add_parser('convert', help='Convert DLT645 to Modbus')
    p_convert.add_argument('--port', required=True, help='Serial port (e.g., /dev/ttyUSB0)')
    p_convert.add_argument('--station', required=True, help='12-digit DLT645 station address')
    p_convert.add_argument('--baudrate', type=int, default=2400, help='DLT645 baud rate (default: 2400)')
    p_convert.add_argument('--reverse', action='store_true', help='Reverse address bytes')

    # Scan command
    p_scan = subparsers.add_parser('scan', help='Scan for Modbus device')
    p_scan.add_argument('--port', required=True, help='Serial port (e.g., /dev/ttyUSB0)')
    p_scan.add_argument('--baudrate', type=int, default=9600, help='Modbus baud rate (default: 9600)')
    p_scan.add_argument('--start', type=int, default=1, help='Start address (default: 1)')
    p_scan.add_argument('--end', type=int, default=247, help='End address (default: 247)')
    p_scan.add_argument('--timeout', type=float, default=0.3, help='Timeout per address (default: 0.3s)')

    # Change address command
    p_change = subparsers.add_parser('change', help='Change Modbus address')
    p_change.add_argument('--port', required=True, help='Serial port (e.g., /dev/ttyUSB0)')
    p_change.add_argument('--baudrate', type=int, default=9600, help='Modbus baud rate (default: 9600)')
    p_change.add_argument('--current', type=int, required=True, help='Current Modbus address')
    p_change.add_argument('--new', type=int, required=True, help='New Modbus address')
    p_change.add_argument('--type', choices=['1phase', '3phase'], default='1phase',
                         help='Meter type: 1phase (DDSU666) or 3phase (DTSU666) (default: 1phase)')

    # Full process command
    p_full = subparsers.add_parser('full', help='Full process: convert + scan + change address')
    p_full.add_argument('--port', required=True, help='Serial port (e.g., /dev/ttyUSB0)')
    p_full.add_argument('--station', required=True, help='12-digit DLT645 station address')
    p_full.add_argument('--address', type=int, required=True, help='Target Modbus address')
    p_full.add_argument('--dlt-baud', type=int, default=2400, help='DLT645 baud rate (default: 2400)')
    p_full.add_argument('--modbus-baud', type=int, default=9600, help='Modbus baud rate (default: 9600)')
    p_full.add_argument('--reverse', action='store_true', help='Reverse address bytes')
    p_full.add_argument('--type', choices=['1phase', '3phase'], default='1phase',
                       help='Meter type: 1phase (DDSU666) or 3phase (DTSU666) (default: 1phase)')

    args = parser.parse_args()

    # Execute command
    if args.command == 'list':
        cmd_list_ports()
    elif args.command == 'convert':
        cmd_convert(args)
    elif args.command == 'scan':
        cmd_scan(args)
    elif args.command == 'change':
        cmd_change(args)
    elif args.command == 'full':
        cmd_full(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
