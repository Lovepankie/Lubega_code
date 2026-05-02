#!/usr/bin/env python3
"""Generate user guide PDF for Pi connection, meter testing and data collection."""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, ListFlowable, ListItem
)

BASE_DIR   = os.path.join(os.path.dirname(__file__), '..')
OUTPUT_PDF = os.path.join(BASE_DIR, 'docs', 'Pi_User_Guide.pdf')
os.makedirs(os.path.join(BASE_DIR, 'docs'), exist_ok=True)

W, H = A4
CONTENT_W = W - 4*cm

doc = SimpleDocTemplate(OUTPUT_PDF, pagesize=A4,
    rightMargin=2*cm, leftMargin=2*cm,
    topMargin=2.5*cm, bottomMargin=2*cm,
    title="NFE Pi User Guide")

styles = getSampleStyleSheet()

# ── Styles ────────────────────────────────────────────────────────────────────
cover_title = ParagraphStyle('CT', parent=styles['Title'],
    fontSize=26, textColor=colors.HexColor('#1a237e'),
    spaceAfter=8, alignment=TA_CENTER)
cover_sub = ParagraphStyle('CS', parent=styles['Normal'],
    fontSize=13, textColor=colors.HexColor('#37474f'),
    spaceAfter=4, alignment=TA_CENTER)
h1 = ParagraphStyle('H1', parent=styles['Heading1'],
    fontSize=16, spaceBefore=16, spaceAfter=6,
    textColor=colors.white,
    backColor=colors.HexColor('#1a237e'),
    borderPad=6)
h2 = ParagraphStyle('H2', parent=styles['Heading2'],
    fontSize=13, spaceBefore=12, spaceAfter=4,
    textColor=colors.HexColor('#1565c0'))
h3 = ParagraphStyle('H3', parent=styles['Heading3'],
    fontSize=11, spaceBefore=8, spaceAfter=3,
    textColor=colors.HexColor('#283593'))
body = ParagraphStyle('B', parent=styles['Normal'],
    fontSize=10, leading=16, spaceAfter=6, alignment=TA_JUSTIFY)
body_left = ParagraphStyle('BL', parent=styles['Normal'],
    fontSize=10, leading=16, spaceAfter=6)
step = ParagraphStyle('ST', parent=styles['Normal'],
    fontSize=10, leading=16, spaceAfter=4,
    leftIndent=12)
code_style = ParagraphStyle('CD', parent=styles['Normal'],
    fontSize=9.5, leading=14, spaceAfter=4,
    fontName='Courier',
    backColor=colors.HexColor('#263238'),
    textColor=colors.HexColor('#80cbc4'),
    borderPad=8, leftIndent=0)
note = ParagraphStyle('NT', parent=styles['Normal'],
    fontSize=9.5, leading=14, spaceAfter=6,
    backColor=colors.HexColor('#e8f5e9'),
    borderColor=colors.HexColor('#2e7d32'),
    borderWidth=1, borderPad=6)
warn = ParagraphStyle('WN', parent=styles['Normal'],
    fontSize=9.5, leading=14, spaceAfter=6,
    backColor=colors.HexColor('#fff8e1'),
    borderColor=colors.HexColor('#f57f17'),
    borderWidth=1, borderPad=6)
tip = ParagraphStyle('TP', parent=styles['Normal'],
    fontSize=9.5, leading=14, spaceAfter=6,
    backColor=colors.HexColor('#e3f2fd'),
    borderColor=colors.HexColor('#1565c0'),
    borderWidth=1, borderPad=6)
caption = ParagraphStyle('CAP', parent=styles['Normal'],
    fontSize=8, textColor=colors.HexColor('#78909c'),
    spaceAfter=6, alignment=TA_CENTER)

def step_table(steps):
    """Render numbered steps as a clean table."""
    data = []
    for i, s in enumerate(steps, 1):
        data.append([
            Paragraph(f"<b>{i}</b>", ParagraphStyle('N', parent=styles['Normal'],
                fontSize=11, textColor=colors.white, alignment=TA_CENTER)),
            Paragraph(s, body_left)
        ])
    t = Table(data, colWidths=[0.8*cm, CONTENT_W-0.8*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0,0),(0,-1), colors.HexColor('#1565c0')),
        ('VALIGN',       (0,0),(-1,-1), 'TOP'),
        ('TOPPADDING',   (0,0),(-1,-1), 6),
        ('BOTTOMPADDING',(0,0),(-1,-1), 6),
        ('LEFTPADDING',  (0,0),(-1,-1), 8),
        ('ROWBACKGROUNDS',(1,0),(1,-1), [colors.HexColor('#f5f5f5'), colors.white]),
        ('GRID',         (0,0),(-1,-1), 0.3, colors.HexColor('#bdbdbd')),
    ]))
    return t

def code_block(text):
    return Paragraph(text, code_style)

def section_header(text, icon=''):
    return Paragraph(f"  {icon}  {text}" if icon else f"  {text}", h1)

story = []

# ═══════════════════════════════════════════════════════════════════════════════
# COVER PAGE
# ═══════════════════════════════════════════════════════════════════════════════
story.append(Spacer(1, 2*cm))
story.append(Paragraph("NFE Electricity Theft Detection", cover_sub))
story.append(Paragraph("Raspberry Pi — Complete User Guide", cover_title))
story.append(Spacer(1, 0.3*cm))
story.append(HRFlowable(width=CONTENT_W, thickness=3, color=colors.HexColor('#1a237e')))
story.append(Spacer(1, 0.5*cm))

cover_info = [
    ["Document:", "Pi Connection, Meter Testing & Data Collection Guide"],
    ["Meter:", "CHINT DTSU666 Three-Phase Energy Meter"],
    ["Pi:", "Raspberry Pi 4 — hostname: nfetestpi2"],
    ["Version:", "1.0"],
    ["Date:", datetime.now().strftime("%d %B %Y")],
    ["Audience:", "Any user — no technical background required"],
]
ct = Table(cover_info, colWidths=[3*cm, CONTENT_W-3*cm])
ct.setStyle(TableStyle([
    ('FONTNAME',    (0,0),(0,-1), 'Helvetica-Bold'),
    ('TEXTCOLOR',   (0,0),(0,-1), colors.HexColor('#1a237e')),
    ('FONTSIZE',    (0,0),(-1,-1), 10),
    ('ROWBACKGROUNDS',(0,0),(-1,-1), [colors.HexColor('#f0f4ff'), colors.white]),
    ('GRID',        (0,0),(-1,-1), 0.4, colors.HexColor('#e0e0e0')),
    ('TOPPADDING',  (0,0),(-1,-1), 6),
    ('BOTTOMPADDING',(0,0),(-1,-1), 6),
    ('LEFTPADDING', (0,0),(-1,-1), 8),
]))
story.append(ct)
story.append(Spacer(1, 1*cm))

# Table of Contents
story.append(Paragraph("<b>Contents</b>", h2))
toc = [
    ["1.", "Connecting to the Pi via Ethernet (direct cable)", "2"],
    ["2.", "Connecting to the Pi via Shared WiFi", "3"],
    ["3.", "Connecting to the Pi via Raspberry Pi Connect (anywhere)", "4"],
    ["4.", "Testing the Connection to the Energy Meter", "5"],
    ["5.", "Collecting & Saving Meter Data on the Pi", "6"],
    ["6.", "Transferring Data from the Pi to Your PC", "8"],
    ["7.", "Quick Reference — Key Details", "9"],
]
toc_t = Table(toc, colWidths=[0.8*cm, CONTENT_W-1.8*cm, 1*cm])
toc_t.setStyle(TableStyle([
    ('FONTSIZE',    (0,0),(-1,-1), 10),
    ('FONTNAME',    (0,0),(0,-1), 'Helvetica-Bold'),
    ('TEXTCOLOR',   (0,0),(0,-1), colors.HexColor('#1a237e')),
    ('ALIGN',       (2,0),(2,-1), 'RIGHT'),
    ('ROWBACKGROUNDS',(0,0),(-1,-1), [colors.HexColor('#f5f5f5'), colors.white]),
    ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#e0e0e0')),
    ('TOPPADDING',  (0,0),(-1,-1), 5),
    ('BOTTOMPADDING',(0,0),(-1,-1), 5),
    ('LEFTPADDING', (0,0),(-1,-1), 8),
]))
story.append(toc_t)
story.append(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — ETHERNET
# ═══════════════════════════════════════════════════════════════════════════════
story.append(section_header("1. Connecting via Ethernet (Direct Cable)", ""))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "This method uses a network cable plugged directly between your laptop and the Pi. "
    "It is the fastest and most reliable connection — use it whenever you are sitting next to the Pi.",
    body))

story.append(Paragraph("What you need:", h3))
items = ["A standard Ethernet / LAN cable (RJ45)", "Your laptop with an Ethernet port (or USB-to-Ethernet adapter)"]
for item in items:
    story.append(Paragraph(f"  • {item}", body_left))

story.append(Paragraph("Steps:", h3))
story.append(step_table([
    "Plug one end of the Ethernet cable into your <b>laptop's Ethernet port</b> and the other end into the <b>Pi's Ethernet port</b>.",
    "Power on the Pi — wait about <b>30 seconds</b> for it to fully boot.",
    "Open a <b>terminal</b> on your laptop:<br/>"
    "  • <b>Windows:</b> Press <b>Win + R</b>, type <b>cmd</b>, press Enter.<br/>"
    "  • <b>Mac/Linux:</b> Open Terminal.",
    "Type the following command and press <b>Enter</b>:",
]))
story.append(code_block("ssh nfetestpi2@192.168.10.2"))
story.append(step_table([
    "When asked <i>\"Are you sure you want to continue connecting?\"</i> — type <b>yes</b> and press Enter.",
    "Enter the password: <b>nfetestpi2</b> (you will not see it being typed — that is normal).",
    "You are now connected. You should see the Pi command prompt.",
]))
story.append(Paragraph(
    "NOTE: Your laptop's Ethernet must be set to static IP 192.168.10.1 for this to work. "
    "This was already configured. If it stops working, check your Network Adapter settings.",
    note))
story.append(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — WIFI
# ═══════════════════════════════════════════════════════════════════════════════
story.append(section_header("2. Connecting via Shared WiFi", ""))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "This method uses your home WiFi network (your home WiFi network). Both your laptop and the Pi must be "
    "connected to the same WiFi network. No cable is needed.",
    body))

story.append(Paragraph("What you need:", h3))
story.append(Paragraph("  • Laptop connected to the <b>your home WiFi network</b> WiFi network", body_left))
story.append(Paragraph("  • Pi powered on and within WiFi range", body_left))

story.append(Paragraph("Steps:", h3))
story.append(step_table([
    "Make sure your laptop is connected to the <b>your home WiFi network</b> WiFi network.",
    "Power on the Pi — wait about <b>30 seconds</b> for it to fully boot and connect to WiFi.",
    "Open a <b>terminal</b> on your laptop (Win + R → cmd → Enter).",
    "Type the following command and press <b>Enter</b>:",
]))
story.append(code_block("ssh nfetestpi2@192.168.100.11"))
story.append(step_table([
    "Enter the password: <b>nfetestpi2</b>",
    "You are now connected to the Pi over WiFi.",
]))
story.append(Paragraph(
    "TIP: If the connection fails, the Pi may have been given a different IP address by the router. "
    "Open Command Prompt and run: arp -a  — look for a device at an address starting with 192.168.100.xx",
    tip))
story.append(Paragraph(
    "NOTE: This method only works when you are physically at home on the your home WiFi network network. "
    "For remote access from anywhere, use Section 3 (Raspberry Pi Connect).",
    note))
story.append(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — PI CONNECT
# ═══════════════════════════════════════════════════════════════════════════════
story.append(section_header("3. Connecting via Raspberry Pi Connect (Anywhere)", ""))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "Raspberry Pi Connect lets you access your Pi from <b>anywhere in the world</b> using just a web browser — "
    "no cable, no VPN, no special setup. You need an internet connection on the device you are using.",
    body))

story.append(Paragraph("What you need:", h3))
story.append(Paragraph("  • Any device with a web browser (laptop, phone, tablet)", body_left))
story.append(Paragraph("  • Internet connection on that device", body_left))
story.append(Paragraph("  • Your <b>Raspberry Pi ID</b> login credentials", body_left))
story.append(Paragraph("  • Pi must be powered on and connected to WiFi (your home WiFi network)", body_left))

story.append(Paragraph("Steps:", h3))
story.append(step_table([
    "Open your web browser and go to:",
]))
story.append(code_block("https://connect.raspberrypi.com"))
story.append(step_table([
    "Click <b>Sign In</b> and enter your Raspberry Pi ID email and password.",
    "You will see a list of your devices. Look for <b>NFE-TheftDetection-Pi</b> (or the name you gave it).",
    "Click on the device name.",
    "Click <b>Remote Shell</b> — this opens a terminal directly in your browser.",
    "You are now connected to the Pi. You can run any command just like in a normal terminal.",
]))
story.append(Paragraph(
    "TIP: Bookmark https://connect.raspberrypi.com for quick access. "
    "You can also use it from your phone when you are away from home.",
    tip))
story.append(Paragraph(
    "NOTE: The Pi must be powered on and connected to WiFi for Raspberry Pi Connect to work. "
    "If the device shows as Offline, check that the Pi has power and is connected to your home WiFi network.",
    note))
story.append(Paragraph(
    "WARNING: Raspberry Pi Connect requires internet on the Pi (via your home WiFi network WiFi). "
    "If the home internet is down, this method will not work — use Ethernet (Section 1) instead.",
    warn))
story.append(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — METER TEST
# ═══════════════════════════════════════════════════════════════════════════════
story.append(section_header("4. Testing the Connection to the Energy Meter", ""))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "Before collecting data, you should verify that the Pi can communicate with the CHINT DTSU666 "
    "energy meter via the RS485/Modbus connection. This script reads live values from the meter "
    "and tells you whether everything is working correctly.",
    body))

story.append(Paragraph("Before you start:", h3))
story.append(Paragraph("  • RS485-to-USB adapter must be plugged into the Pi's USB port", body_left))
story.append(Paragraph("  • RS485 cable must be connected from the adapter to the meter terminals (A+, B-)", body_left))
story.append(Paragraph("  • Meter must be powered on", body_left))

story.append(Paragraph("Steps:", h3))
story.append(step_table([
    "Connect to the Pi using any of the three methods in Sections 1, 2, or 3.",
    "Navigate to the project folder:",
]))
story.append(code_block("cd ~/iot_meter"))
story.append(step_table([
    "Run the meter test script:",
]))
story.append(code_block("python3 scripts/modbus_test.py"))
story.append(step_table([
    "Wait a few seconds. The script will try to read from the meter and display the results.",
]))

story.append(Paragraph("What a SUCCESSFUL result looks like:", h3))
success_data = [
    ["Parameter", "Example Value"],
    ["Voltage A / B / C", "220.5 V  /  220.3 V  /  220.7 V"],
    ["Current A / B / C", "1.04 A  /  2.30 A  /  0.00 A"],
    ["Power Total", "0.54 kW"],
    ["Power Factor", "0.99"],
    ["Frequency", "50.1 Hz"],
    ["Sanity Checks", "ALL PASS"],
]
st = Table(success_data, colWidths=[5*cm, CONTENT_W-5*cm])
st.setStyle(TableStyle([
    ('BACKGROUND',   (0,0),(-1,0), colors.HexColor('#1a237e')),
    ('TEXTCOLOR',    (0,0),(-1,0), colors.white),
    ('FONTNAME',     (0,0),(-1,0), 'Helvetica-Bold'),
    ('FONTSIZE',     (0,0),(-1,-1), 10),
    ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, colors.HexColor('#f5f5f5')]),
    ('GRID',         (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',   (0,0),(-1,-1), 5),
    ('BOTTOMPADDING',(0,0),(-1,-1), 5),
    ('LEFTPADDING',  (0,0),(-1,-1), 8),
]))
story.append(st)
story.append(Spacer(1, 0.3*cm))

story.append(Paragraph("What to do if it FAILS:", h3))
fail_data = [
    ["Error Message", "Likely Cause", "Fix"],
    ["Timeout / No response", "RS485 cable not connected or meter off", "Check cable connections and meter power"],
    ["Port /dev/ttyUSB0 not found", "USB adapter not plugged in", "Plug in the RS485-USB adapter"],
    ["Port is busy", "Another script is using the port", "Stop any running collection service first"],
    ["Wrong values (e.g. 0V)", "Wiring issue on A+/B- terminals", "Swap the A and B wires on the meter"],
]
ft = Table(fail_data, colWidths=[4.5*cm, 4.5*cm, CONTENT_W-9*cm])
ft.setStyle(TableStyle([
    ('BACKGROUND',   (0,0),(-1,0), colors.HexColor('#b71c1c')),
    ('TEXTCOLOR',    (0,0),(-1,0), colors.white),
    ('FONTNAME',     (0,0),(-1,0), 'Helvetica-Bold'),
    ('FONTSIZE',     (0,0),(-1,-1), 9),
    ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, colors.HexColor('#fff5f5')]),
    ('GRID',         (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',   (0,0),(-1,-1), 5),
    ('BOTTOMPADDING',(0,0),(-1,-1), 5),
    ('LEFTPADDING',  (0,0),(-1,-1), 6),
    ('VALIGN',       (0,0),(-1,-1), 'TOP'),
]))
story.append(ft)
story.append(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — DATA COLLECTION
# ═══════════════════════════════════════════════════════════════════════════════
story.append(section_header("5. Collecting and Saving Meter Data on the Pi", ""))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "Data is collected using a Python script that reads the meter every 5 seconds and saves "
    "each reading to a CSV file on the Pi. There are two ways to run it: "
    "manually (for a quick test) or as a background service (recommended for long collections).",
    body))

story.append(Paragraph("5.1  Manual Collection (for short tests)", h2))
story.append(step_table([
    "Connect to the Pi and navigate to the project folder:",
]))
story.append(code_block("cd ~/iot_meter"))
story.append(step_table([
    "Run the collection script. Replace <b>LABEL</b> with your scenario name and <b>SECONDS</b> with how long to collect:",
]))
story.append(code_block("python3 scripts/collect_data.py --label normal --duration 900"))
story.append(Paragraph(
    "Example values for --label:  normal  |  bypass_red  |  bypass_yellow  |  bypass_blue  |  bypass_all",
    tip))
story.append(Paragraph(
    "Example values for --duration:  900 = 15 minutes  |  3600 = 1 hour  |  86400 = 24 hours",
    tip))
story.append(step_table([
    "The script will print each reading to the screen. When done, it saves the data to <b>data/&lt;label&gt;.csv</b>",
    "To stop early, press <b>Ctrl + C</b>",
]))

story.append(Paragraph("5.2  Background Service (recommended for long collections)", h2))
story.append(Paragraph(
    "For collections that run for many hours or overnight, use a background service. "
    "This keeps collecting even if you close the terminal, disconnect SSH, or the Pi loses power and reboots.",
    body))

story.append(Paragraph("Starting a new collection service:", h3))
story.append(step_table([
    "Connect to the Pi and run this command (replace <b>SCENARIO</b> with your label, e.g. bypass_red):",
]))
story.append(code_block(
    "sudo systemctl start bypass-yellow-collection.service"))
story.append(Paragraph("Or to start any scenario, create a new service (Claude Code will do this for you automatically).", body_left))

story.append(Paragraph("Checking if collection is running:", h3))
story.append(code_block("systemctl status bypass-yellow-collection.service"))
story.append(Paragraph("Look for <b>Active: active (running)</b> — this means data is being collected.", body_left))

story.append(Paragraph("Watching live data as it is collected:", h3))
story.append(code_block("tail -f ~/iot_meter/data/bypass_yellow.csv"))
story.append(Paragraph("Press <b>Ctrl + C</b> to stop watching (does not stop collection).", body_left))

story.append(Paragraph("Checking how many rows have been collected:", h3))
story.append(code_block("wc -l ~/iot_meter/data/bypass_yellow.csv"))

story.append(Paragraph("Stopping the collection early:", h3))
story.append(code_block(
    "sudo systemctl stop bypass-yellow-collection.service\n"
    "sudo systemctl disable bypass-yellow-collection.service"))

story.append(Paragraph("5.3  What the data looks like", h2))
story.append(Paragraph("Each row in the CSV file contains one 5-second reading:", body_left))
cols_data = [
    ["Column", "Description", "Example"],
    ["timestamp", "Date and time of reading", "2026-04-06T12:00:00"],
    ["scenario", "Label name you gave", "bypass_yellow"],
    ["label", "0 = normal, 1 = theft", "1"],
    ["V_L1 / V_L2 / V_L3", "Voltage on each phase (Volts)", "213.1"],
    ["I_L1 / I_L2 / I_L3", "Current on each phase (Amps)", "19.1"],
    ["P_total", "Total active power (kW)", "4.226"],
    ["P_L1 / P_L2 / P_L3", "Power per phase (kW)", "3.681"],
    ["PF_total", "Power factor", "0.99"],
    ["frequency", "Grid frequency (Hz)", "50.12"],
    ["energy_total", "Cumulative energy (kWh)", "17.77"],
]
colt = Table(cols_data, colWidths=[4*cm, 5.5*cm, CONTENT_W-9.5*cm])
colt.setStyle(TableStyle([
    ('BACKGROUND',   (0,0),(-1,0), colors.HexColor('#1a237e')),
    ('TEXTCOLOR',    (0,0),(-1,0), colors.white),
    ('FONTNAME',     (0,0),(-1,0), 'Helvetica-Bold'),
    ('FONTSIZE',     (0,0),(-1,-1), 9),
    ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, colors.HexColor('#f0f4ff')]),
    ('GRID',         (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',   (0,0),(-1,-1), 4),
    ('BOTTOMPADDING',(0,0),(-1,-1), 4),
    ('LEFTPADDING',  (0,0),(-1,-1), 6),
    ('VALIGN',       (0,0),(-1,-1), 'TOP'),
]))
story.append(colt)
story.append(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — TRANSFER DATA
# ═══════════════════════════════════════════════════════════════════════════════
story.append(section_header("6. Transferring Data from the Pi to Your PC", ""))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "After data has been collected on the Pi, you need to copy it to your Windows laptop "
    "for analysis and report generation. There are two ways to do this.",
    body))

story.append(Paragraph("Method A — Using SCP (via Command Prompt)", h2))
story.append(Paragraph("SCP copies a file from the Pi directly to your PC over the network.", body_left))
story.append(step_table([
    "Open Command Prompt on your laptop (Win + R, type cmd, press Enter).",
    "Run this command (works on both Ethernet and WiFi):",
]))
story.append(code_block(
    "scp nfetestpi2@192.168.100.11:/home/nfetestpi2/iot_meter/data/bypass_yellow.csv "
    "D:\\Engineering\\Lubega_Project\\CUSTOM_CODE\\Lubega_Project\\nfe-modbus-energy-logger\\data\\bypass_yellow.csv"))
story.append(step_table([
    "Enter the password: <b>nfetestpi2</b> when prompted.",
    "The file will be saved to your local data folder.",
]))
story.append(Paragraph(
    "TIP: Replace bypass_yellow.csv with any filename to transfer a different dataset. "
    "Replace 192.168.100.11 with 192.168.10.2 if using Ethernet cable.",
    tip))

story.append(Paragraph("Method B — View files via Raspberry Pi Connect", h2))
story.append(Paragraph(
    "If you are connected via Raspberry Pi Connect, you can read the data directly "
    "in the browser terminal without copying it to your PC.",
    body_left))
story.append(step_table([
    "Connect via https://connect.raspberrypi.com and open Remote Shell.",
    "View the last 10 rows of any dataset:",
]))
story.append(code_block("tail -10 ~/iot_meter/data/bypass_yellow.csv"))
story.append(step_table([
    "Check how many rows have been collected:",
]))
story.append(code_block("wc -l ~/iot_meter/data/bypass_yellow.csv"))

story.append(Paragraph("Where files are stored on the Pi:", h3))
paths_data = [
    ["File", "Location on Pi"],
    ["normal_final.csv", "/home/nfetestpi2/iot_meter/data/normal_final.csv"],
    ["bypass_red.csv", "/home/nfetestpi2/iot_meter/data/bypass_red.csv"],
    ["bypass_yellow.csv", "/home/nfetestpi2/iot_meter/data/bypass_yellow.csv"],
    ["Collection log", "/home/nfetestpi2/iot_meter/logs/"],
]
pt = Table(paths_data, colWidths=[4*cm, CONTENT_W-4*cm])
pt.setStyle(TableStyle([
    ('BACKGROUND',   (0,0),(-1,0), colors.HexColor('#1a237e')),
    ('TEXTCOLOR',    (0,0),(-1,0), colors.white),
    ('FONTNAME',     (0,0),(-1,-1), 'Courier'),
    ('FONTNAME',     (0,0),(-1,0), 'Helvetica-Bold'),
    ('FONTSIZE',     (0,0),(-1,-1), 9),
    ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, colors.HexColor('#f5f5f5')]),
    ('GRID',         (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',   (0,0),(-1,-1), 5),
    ('BOTTOMPADDING',(0,0),(-1,-1), 5),
    ('LEFTPADDING',  (0,0),(-1,-1), 8),
]))
story.append(pt)
story.append(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — QUICK REFERENCE
# ═══════════════════════════════════════════════════════════════════════════════
story.append(section_header("7. Quick Reference Card", ""))
story.append(Spacer(1, 0.3*cm))

story.append(Paragraph("Pi Login Details", h2))
creds = [
    ["Item", "Value"],
    ["Hostname", "nfetestpi2"],
    ["Password", "nfetestpi2"],
    ["Ethernet IP", "192.168.10.2"],
    ["WiFi IP", "192.168.100.11"],
    ["Pi Connect URL", "https://connect.raspberrypi.com"],
    ["WiFi Network", "Your home WiFi (the one the Pi is connected to)"],
    ["Project folder", "~/iot_meter"],
]
crt = Table(creds, colWidths=[4*cm, CONTENT_W-4*cm])
crt.setStyle(TableStyle([
    ('BACKGROUND',   (0,0),(-1,0), colors.HexColor('#1a237e')),
    ('TEXTCOLOR',    (0,0),(-1,0), colors.white),
    ('FONTNAME',     (0,0),(0,-1), 'Helvetica-Bold'),
    ('FONTNAME',     (1,1),(1,-1), 'Courier'),
    ('FONTSIZE',     (0,0),(-1,-1), 10),
    ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, colors.HexColor('#f0f4ff')]),
    ('GRID',         (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',   (0,0),(-1,-1), 6),
    ('BOTTOMPADDING',(0,0),(-1,-1), 6),
    ('LEFTPADDING',  (0,0),(-1,-1), 8),
]))
story.append(crt)
story.append(Spacer(1, 0.5*cm))

story.append(Paragraph("Most Used Commands", h2))
cmds = [
    ["Task", "Command"],
    ["SSH via WiFi", "ssh nfetestpi2@192.168.100.11"],
    ["SSH via Ethernet", "ssh nfetestpi2@192.168.10.2"],
    ["Go to project folder", "cd ~/iot_meter"],
    ["Test meter connection", "python3 scripts/modbus_test.py"],
    ["Start manual collection", "python3 scripts/collect_data.py --label normal --duration 3600"],
    ["Check service status", "systemctl status bypass-yellow-collection.service"],
    ["Watch live data", "tail -f ~/iot_meter/data/bypass_yellow.csv"],
    ["Count rows collected", "wc -l ~/iot_meter/data/bypass_yellow.csv"],
    ["Stop collection service", "sudo systemctl stop bypass-yellow-collection.service"],
    ["Check Pi time", "date"],
    ["Check boot history", "journalctl --list-boots"],
    ["Copy file to PC (WiFi)", "scp nfetestpi2@192.168.100.11:/home/nfetestpi2/iot_meter/data/FILE.csv D:\\path\\FILE.csv"],
    ["Shut down Pi safely", "sudo shutdown now"],
    ["Reboot Pi", "sudo reboot"],
]
cmt = Table(cmds, colWidths=[5*cm, CONTENT_W-5*cm])
cmt.setStyle(TableStyle([
    ('BACKGROUND',   (0,0),(-1,0), colors.HexColor('#1a237e')),
    ('TEXTCOLOR',    (0,0),(-1,0), colors.white),
    ('FONTNAME',     (0,0),(-1,0), 'Helvetica-Bold'),
    ('FONTNAME',     (1,1),(1,-1), 'Courier'),
    ('FONTSIZE',     (0,0),(-1,-1), 8.5),
    ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, colors.HexColor('#f5f5f5')]),
    ('GRID',         (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',   (0,0),(-1,-1), 4),
    ('BOTTOMPADDING',(0,0),(-1,-1), 4),
    ('LEFTPADDING',  (0,0),(-1,-1), 6),
    ('VALIGN',       (0,0),(-1,-1), 'TOP'),
]))
story.append(cmt)

story.append(Spacer(1, 1*cm))
story.append(HRFlowable(width=CONTENT_W, thickness=1, color=colors.HexColor('#1a237e')))
story.append(Spacer(1, 0.2*cm))
story.append(Paragraph(
    f"NFE Electricity Theft Detection Project  |  Raspberry Pi User Guide v1.0  |  "
    f"Generated {datetime.now().strftime('%d %B %Y')}",
    caption))

doc.build(story)
print(f"PDF saved -> {OUTPUT_PDF}")
