#!/usr/bin/env python3
"""
DLT645 to Modbus Converter — Standalone
No local imports required. Converts to exe with PyInstaller:
    pyinstaller --onefile --windowed converter.py
"""

import time
import struct
import threading
import sys
import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext


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
                               current_address: int, new_address: int) -> None:
    """Write Modbus FC-16 to register 0x0006 to change slave address."""
    client = serial.Serial(
        port,
        baudrate=baudrate,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_TWO,
        timeout=1,
    )
    try:
        fc = 0x10
        start_reg = 0x0006
        reg_count = 0x0001
        byte_count = 0x02
        request = struct.pack(
            ">B B H H B H",
            current_address, fc, start_reg, reg_count, byte_count, new_address,
        )
        crc = _calculate_crc(request)
        request += struct.pack("BB", crc & 0xFF, (crc >> 8) & 0xFF)
        client.write(request)
        time.sleep(0.3)
    finally:
        client.close()


def _probe_modbus_address(port: str, baudrate: int,
                           scan_range: range = range(1, 248),
                           timeout: float = 0.3) -> int | None:
    """Scan Modbus addresses and return the first one that responds.
    Sends FC-04 (Read Input Registers) to each address.
    Returns the responding address, or None if nothing found.
    """
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
                return addr
        return None
    finally:
        client.close()


# ─────────────────────────── DLT645 helpers ──────────────────────────────────

def _calculate_checksum(data: bytes) -> int:
    return sum(data) % 256


def _construct_frame(station_addr: str, reverse: bool = False) -> bytes:
    """Build a DL/T 645 protocol-switch frame."""
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


# ─────────────────────────── GUI Application ─────────────────────────────────

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("DLT645 → Modbus Converter")
        self.root.resizable(True, True)
        self.ser: serial.Serial | None = None
        self._action_btns: list[ttk.Button] = []   # must exist before _build_ui
        self._build_ui()
        self._refresh_ports()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(4, weight=1)

        # ── Serial config ────────────────────────────────────────────────────
        sf = ttk.LabelFrame(self.root, text="Serial Port", padding=8)
        sf.grid(row=0, column=0, sticky="ew", **pad)
        sf.columnconfigure(1, weight=1)

        ttk.Label(sf, text="Port:").grid(row=0, column=0, sticky="w")
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(sf, textvariable=self.port_var,
                                       state="readonly", width=22)
        self.port_combo.grid(row=0, column=1, sticky="ew", padx=(4, 4))

        ttk.Button(sf, text="⟳ Refresh", command=self._refresh_ports,
                   width=10).grid(row=0, column=2)

        ttk.Label(sf, text="Baud:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.baud_var = tk.StringVar(value="2400")
        ttk.Combobox(
            sf, textvariable=self.baud_var, width=10,
            values=["1200", "2400", "4800", "9600", "19200"], state="readonly",
        ).grid(row=1, column=1, sticky="w", padx=(4, 0), pady=(6, 0))

        self._status_lbl = ttk.Label(sf, text="● Disconnected", foreground="red")
        self._status_lbl.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self._conn_btn = ttk.Button(sf, text="Connect", command=self._toggle_connect)
        self._conn_btn.grid(row=2, column=2, pady=(6, 0))

        # ── Device config ────────────────────────────────────────────────────
        df = ttk.LabelFrame(self.root, text="Device Configuration", padding=8)
        df.grid(row=1, column=0, sticky="ew", **pad)
        df.columnconfigure(1, weight=1)

        ttk.Label(df, text="DLT645 Station Address:").grid(row=0, column=0, sticky="w")
        self.station_var = tk.StringVar(value="200322016690")
        ttk.Entry(df, textvariable=self.station_var, width=20).grid(
            row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Label(df, text="12-digit meter address",
                  foreground="gray").grid(row=1, column=1, sticky="w")

        # Current Modbus address (before change)
        ttk.Label(df, text="Current Modbus Address:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        cur_frame = ttk.Frame(df)
        cur_frame.grid(row=2, column=1, sticky="w", padx=(6, 0), pady=(8, 0))
        self.current_modbus_var = tk.StringVar(value="1")
        ttk.Entry(cur_frame, textvariable=self.current_modbus_var, width=10).pack(side=tk.LEFT)
        self._scan_btn = ttk.Button(cur_frame, text="🔍 Scan",
                                    command=self._do_scan, state="disabled")
        self._scan_btn.pack(side=tk.LEFT, padx=(6, 0))
        self._action_btns.append(self._scan_btn)
        ttk.Label(df, text="Address meter currently responds to",
                  foreground="gray").grid(row=3, column=1, sticky="w")

        # Target / new Modbus address
        ttk.Label(df, text="Target Modbus Address:").grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.modbus_var = tk.StringVar(value="1")
        ttk.Entry(df, textvariable=self.modbus_var, width=10).grid(
            row=4, column=1, sticky="w", padx=(6, 0), pady=(8, 0))
        ttk.Label(df, text="1 – 247  (new address to assign)",
                  foreground="gray").grid(row=5, column=1, sticky="w")

        self.reverse_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(df, text="Reverse address bytes",
                        variable=self.reverse_var).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))

        # ── Action buttons ───────────────────────────────────────────────────
        bf = ttk.Frame(self.root)
        bf.grid(row=2, column=0, **pad)

        def _btn(label, cmd):
            b = ttk.Button(bf, text=label, command=cmd, state="disabled")
            b.pack(side=tk.LEFT, padx=4)
            self._action_btns.append(b)
            return b

        self._conv_btn   = _btn("Convert Protocol",    self._do_convert)
        self._addr_btn   = _btn("Change Modbus Addr",  self._do_change_addr)
        self._full_btn   = _btn("▶ Full Process",      self._do_full_process)

        # ── Log ──────────────────────────────────────────────────────────────
        lf = ttk.LabelFrame(self.root, text="Log", padding=8)
        lf.grid(row=4, column=0, sticky="nsew", **pad)
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(0, weight=1)
        self.root.rowconfigure(4, weight=1)

        self._log = scrolledtext.ScrolledText(lf, height=18, state="disabled")
        self._log.grid(row=0, column=0, sticky="nsew")
        ttk.Button(lf, text="Clear", command=self._clear_log).grid(
            row=1, column=0, sticky="e", pady=(4, 0))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log_msg(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self._log.config(state="normal")
        self._log.insert(tk.END, f"[{ts}] {msg}\n")
        self._log.see(tk.END)
        self._log.config(state="disabled")
        self.root.update_idletasks()

    def _clear_log(self):
        self._log.config(state="normal")
        self._log.delete("1.0", tk.END)
        self._log.config(state="disabled")

    def _refresh_ports(self):
        ports = list_serial_ports()
        self.port_combo["values"] = ports
        if ports:
            if self.port_var.get() not in ports:
                self.port_var.set(ports[0])
            self._log_msg(f"Found {len(ports)} port(s): {', '.join(ports)}")
        else:
            self.port_var.set("")
            self._log_msg("No serial ports detected.")

    def _set_btns(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for b in self._action_btns:
            b.config(state=state)

    # ── Connection ────────────────────────────────────────────────────────────

    def _toggle_connect(self):
        if self.ser and self.ser.is_open:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self.port_var.get()
        if not port:
            messagebox.showerror("Error", "No port selected. Click ⟳ Refresh first.")
            return
        try:
            baud = int(self.baud_var.get())
            self.ser = serial.Serial(
                port, baudrate=baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                timeout=2,
            )
            self._status_lbl.config(text="● Connected", foreground="green")
            self._conn_btn.config(text="Disconnect")
            self._set_btns(True)
            self._log_msg(f"Connected → {port} @ {baud} baud")
        except serial.SerialException as e:
            messagebox.showerror("Connection Error", str(e))

    def _disconnect(self):
        if self.ser:
            self.ser.close()
        self._status_lbl.config(text="● Disconnected", foreground="red")
        self._conn_btn.config(text="Connect")
        self._set_btns(False)
        self._log_msg("Disconnected.")

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate_station(self) -> str | None:
        addr = self.station_var.get().strip()
        if len(addr) != 12 or not addr.isdigit():
            messagebox.showerror("Validation", "Station address must be exactly 12 digits.")
            return None
        return addr

    def _validate_modbus(self) -> int | None:
        try:
            addr = int(self.modbus_var.get())
            if not 1 <= addr <= 247:
                raise ValueError
            return addr
        except ValueError:
            messagebox.showerror("Validation", "Modbus address must be an integer 1–247.")
            return None

    # ── DLT645 protocol conversion ────────────────────────────────────────────

    def _attempt_conversion(self, station_addr: str, reverse: bool,
                             wait: float = 2.0) -> bool:
        frame = _construct_frame(station_addr, reverse)
        self._log_msg(f"TX: {frame.hex()}")
        self.ser.write(frame)
        time.sleep(wait)
        waiting = self.ser.in_waiting
        if waiting:
            resp = self.ser.read(waiting)
            self._log_msg(f"RX: {resp.hex()}")
            return True
        self._log_msg("No response.")
        return False

    def _do_convert(self):
        station = self._validate_station()
        if not station:
            return
        reverse = self.reverse_var.get()

        def run():
            self._log_msg(f"Converting protocol — station={station}, reverse={reverse}")
            # Flush buffer
            if self.ser.in_waiting:
                stale = self.ser.read(self.ser.in_waiting)
                self._log_msg(f"Flushed {len(stale)} stale bytes.")

            ok = self._attempt_conversion(station, reverse)
            if not ok:
                self._log_msg("Retrying with reversed flag toggled…")
                ok = self._attempt_conversion(station, not reverse)
            if not ok:
                self._log_msg("Retrying with extended timing (5 s)…")
                ok = self._attempt_conversion(station, reverse, wait=5.0)

            if ok:
                self._log_msg("✓ Protocol conversion done.")
            else:
                self._log_msg("✗ No response — check wiring / address / baud rate.")

        threading.Thread(target=run, daemon=True).start()

    # ── Modbus address change ─────────────────────────────────────────────────

    def _validate_current_modbus(self) -> int | None:
        try:
            addr = int(self.current_modbus_var.get())
            if not 1 <= addr <= 247:
                raise ValueError
            return addr
        except ValueError:
            messagebox.showerror("Validation", "Current Modbus address must be an integer 1–247.")
            return None

    def _do_scan(self):
        """Scan all Modbus addresses and populate 'Current Modbus Address' when found."""
        if not self.ser or not self.ser.is_open:
            messagebox.showerror("Error", "Connect to the serial port first.")
            return

        def run():
            port = self.ser.port
            baud = self.ser.baudrate
            self._log_msg("Scanning Modbus addresses 1–247 (this may take a moment)…")
            found = _probe_modbus_address(port, baud)
            if found is not None:
                self.current_modbus_var.set(str(found))
                self._log_msg(f"✓ Meter found at Modbus address {found}. 'Current Modbus Address' updated.")
            else:
                self._log_msg("✗ No Modbus device responded on addresses 1–247.")
                self._log_msg("  → Device may still be in DLT645 mode. Run 'Convert Protocol' first.")

        threading.Thread(target=run, daemon=True).start()

    def _do_change_addr(self):
        cur_addr = self._validate_current_modbus()
        new_addr = self._validate_modbus()
        if cur_addr is None or new_addr is None:
            return

        def run():
            port = self.ser.port
            baud = self.ser.baudrate
            self._log_msg(f"Changing Modbus address: {cur_addr} → {new_addr}")
            try:
                _raw_change_slave_address(port, baud, cur_addr, new_addr)
                self._log_msg(f"✓ Address changed to {new_addr}.")
                self.current_modbus_var.set(str(new_addr))
            except Exception as e:
                self._log_msg(f"✗ Address change failed: {e}")

        threading.Thread(target=run, daemon=True).start()

    # ── Clear meter ───────────────────────────────────────────────────────────

    # ── Full process ──────────────────────────────────────────────────────────

    def _do_full_process(self):
        station = self._validate_station()
        new_addr = self._validate_modbus()
        if not station or new_addr is None:
            return
        reverse = self.reverse_var.get()

        def run():
            self._log_msg("═══ Full Process Started ═══")

            # Step 1: convert protocol
            self._log_msg(f"[1/2] Converting protocol — station={station}")
            if self.ser.in_waiting:
                stale = self.ser.read(self.ser.in_waiting)
                self._log_msg(f"Flushed {len(stale)} stale bytes.")

            ok = self._attempt_conversion(station, reverse)
            if not ok:
                ok = self._attempt_conversion(station, not reverse)
            if not ok:
                ok = self._attempt_conversion(station, reverse, wait=5.0)

            if ok:
                self._log_msg("✓ Protocol conversion done.")
            else:
                self._log_msg("⚠ Conversion uncertain — proceeding anyway.")

            time.sleep(1)

            # Step 2: change address
            cur_addr_str = self.current_modbus_var.get().strip()
            cur_addr = int(cur_addr_str) if cur_addr_str.isdigit() else 1
            self._log_msg(f"[2/2] Changing Modbus address: {cur_addr} → {new_addr}")
            port = self.ser.port
            baud = self.ser.baudrate
            try:
                _raw_change_slave_address(port, baud, cur_addr, new_addr)
                self._log_msg(f"✓ Address set to {new_addr}.")
                self.current_modbus_var.set(str(new_addr))
            except Exception as e:
                self._log_msg(f"✗ Address change error: {e}")

            self._log_msg("═══ Full Process Complete ═══")

        threading.Thread(target=run, daemon=True).start()

    # ── Window close ──────────────────────────────────────────────────────────

    def _on_close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.root.destroy()


# ─────────────────────────── Entry point ─────────────────────────────────────

def main():
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app._on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
