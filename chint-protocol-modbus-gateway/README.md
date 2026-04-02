# DLT645 → Modbus RTU Converter

A standalone Python tool for converting smart meters from **DL/T645 protocol to Modbus RTU**, with built-in capabilities for device discovery and Modbus configuration.

## 🚀 Features

* 🔄 Convert DL/T645 meters to Modbus RTU
* 🔍 Scan Modbus addresses (1–247)
* ⚙️ Change Modbus slave address (register `0x0006`)
* 🔌 Serial communication (RS485 via USB)
* 🖥️ Desktop GUI (Tkinter)
* 🧪 Debug logging for TX/RX frames

## 🧠 Use Case

This tool is designed for:

* Smart meter commissioning
* Field deployment engineers
* AMI (Advanced Metering Infrastructure) gateways
* Raspberry Pi-based edge systems

## ⚙️ Requirements

* Python 3.10+
* RS485 → USB converter
* Serial access permissions

Install dependencies:

```bash
pip install -r requirements.txt
```

## ▶️ Run

```bash
python src/converter.py
```

## 🧪 Build Executable (Windows)

```bash
pyinstaller --onefile --windowed src/converter.py
```

## 🔌 How It Works

1. Sends DL/T645 frame to switch protocol
2. Confirms response from meter
3. Scans Modbus address
4. Writes new address via Modbus register `0x0006`

## 🏗️ Architecture (Simplified)

DLT645 Meter → Converter → Modbus RTU → AMI System

## 📦 Future Roadmap

* MQTT integration for telemetry publishing
* Headless (CLI/service) mode for Raspberry Pi
* Integration with OpenEMS / backend systems
* Batch provisioning for multiple meters

## 📄 License

MIT License
