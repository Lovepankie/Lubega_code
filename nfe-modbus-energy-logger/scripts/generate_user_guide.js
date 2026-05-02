const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat,
  ExternalHyperlink
} = require('docx');
const fs = require('fs');
const path = require('path');

const OUT = path.join(__dirname, '..', 'docs', 'Pi_User_Guide.docx');

// ── Helpers ───────────────────────────────────────────────────────────────────
const DARK_BLUE  = '1a237e';
const MID_BLUE   = '1565c0';
const LIGHT_BLUE = 'e3f2fd';
const DARK_GREEN = '2e7d32';
const LIGHT_GREEN= 'e8f5e9';
const AMBER      = 'f57f17';
const LIGHT_AMB  = 'fff8e1';
const CODE_BG    = '263238';
const CODE_FG    = '80cbc4';
const GRAY_BG    = 'f5f5f5';
const PAGE_W     = 11906; // A4 DXA
const MARGINS    = 1440;  // 1 inch each side
const CONTENT_W  = PAGE_W - 2 * MARGINS; // 9026

const border = { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' };
const borders = { top: border, bottom: border, left: border, right: border };

function cell(text, opts = {}) {
  const { bold = false, color, bg, width = CONTENT_W / 2, valign, fontName = 'Arial' } = opts;
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: bg ? { fill: bg, type: ShadingType.CLEAR } : undefined,
    verticalAlign: valign || VerticalAlign.TOP,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      children: [new TextRun({ text, bold, color: color || '000000', font: fontName, size: 20 })]
    })]
  });
}

function headerCell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: DARK_BLUE, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      children: [new TextRun({ text, bold: true, color: 'FFFFFF', font: 'Arial', size: 20 })]
    })]
  });
}

function twoColTable(rows, widths) {
  const [w1, w2] = widths || [CONTENT_W * 0.4, CONTENT_W * 0.6];
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [Math.round(w1), Math.round(w2)],
    rows: rows.map((r, i) => new TableRow({
      children: [
        cell(r[0], { bold: i === 0, color: i === 0 ? 'FFFFFF' : DARK_BLUE, bg: i === 0 ? DARK_BLUE : (i%2===1 ? GRAY_BG : 'FFFFFF'), width: Math.round(w1) }),
        cell(r[1], { bg: i === 0 ? DARK_BLUE : (i%2===1 ? GRAY_BG : 'FFFFFF'), color: i === 0 ? 'FFFFFF' : '000000', bold: i === 0, width: Math.round(w2) }),
      ]
    }))
  });
}

function threeColTable(rows, widths) {
  const [w1, w2, w3] = widths;
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [w1, w2, w3],
    rows: rows.map((r, i) => new TableRow({
      children: [
        new TableCell({ borders, width: { size: w1, type: WidthType.DXA }, shading: { fill: i===0?DARK_BLUE:(i%2===1?GRAY_BG:'FFFFFF'), type: ShadingType.CLEAR }, margins: { top:80, bottom:80, left:120, right:120 },
          children: [new Paragraph({ children: [new TextRun({ text: r[0], bold: i===0, color: i===0?'FFFFFF':DARK_BLUE, font:'Arial', size:20 })] })] }),
        new TableCell({ borders, width: { size: w2, type: WidthType.DXA }, shading: { fill: i===0?DARK_BLUE:(i%2===1?GRAY_BG:'FFFFFF'), type: ShadingType.CLEAR }, margins: { top:80, bottom:80, left:120, right:120 },
          children: [new Paragraph({ children: [new TextRun({ text: r[1], bold: i===0, color: i===0?'FFFFFF':'000000', font:'Arial', size:20 })] })] }),
        new TableCell({ borders, width: { size: w3, type: WidthType.DXA }, shading: { fill: i===0?DARK_BLUE:(i%2===1?GRAY_BG:'FFFFFF'), type: ShadingType.CLEAR }, margins: { top:80, bottom:80, left:120, right:120 },
          children: [new Paragraph({ children: [new TextRun({ text: r[2], bold: i===0, color: i===0?'FFFFFF':'000000', font:'Arial', size:20 })] })] }),
      ]
    }))
  });
}

function stepsTable(steps) {
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [600, CONTENT_W - 600],
    rows: steps.map((s, i) => new TableRow({
      children: [
        new TableCell({ borders, width: { size: 600, type: WidthType.DXA }, shading: { fill: MID_BLUE, type: ShadingType.CLEAR }, margins: { top:80, bottom:80, left:120, right:120 }, verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: String(i+1), bold:true, color:'FFFFFF', font:'Arial', size:22 })] })] }),
        new TableCell({ borders, width: { size: CONTENT_W-600, type: WidthType.DXA }, shading: { fill: i%2===0?GRAY_BG:'FFFFFF', type: ShadingType.CLEAR }, margins: { top:80, bottom:80, left:120, right:120 },
          children: [new Paragraph({ children: [new TextRun({ text: s, font:'Arial', size:20 })] })] }),
      ]
    }))
  });
}

function codeBlock(text) {
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [CONTENT_W],
    rows: [new TableRow({ children: [
      new TableCell({ borders, width: { size: CONTENT_W, type: WidthType.DXA },
        shading: { fill: CODE_BG, type: ShadingType.CLEAR },
        margins: { top: 120, bottom: 120, left: 200, right: 200 },
        children: [new Paragraph({ children: [new TextRun({ text, font:'Courier New', size:18, color:CODE_FG })] })]
      })
    ]})]
  });
}

function noteBox(text, bg, borderColor) {
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [CONTENT_W],
    rows: [new TableRow({ children: [
      new TableCell({
        borders: { top:{style:BorderStyle.SINGLE,size:4,color:borderColor}, bottom:{style:BorderStyle.SINGLE,size:4,color:borderColor}, left:{style:BorderStyle.SINGLE,size:8,color:borderColor}, right:{style:BorderStyle.SINGLE,size:4,color:borderColor} },
        width: { size: CONTENT_W, type: WidthType.DXA },
        shading: { fill: bg, type: ShadingType.CLEAR },
        margins: { top: 100, bottom: 100, left: 160, right: 160 },
        children: [new Paragraph({ children: [new TextRun({ text, font:'Arial', size:19 })] })]
      })
    ]})]
  });
}

function note(text)  { return noteBox(text, LIGHT_GREEN, DARK_GREEN); }
function warn(text)  { return noteBox(text, LIGHT_AMB, AMBER); }
function tip(text)   { return noteBox(text, LIGHT_BLUE, MID_BLUE); }

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text, font:'Arial' })] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text, font:'Arial' })] });
}
function h3(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text, font:'Arial' })] });
}
function para(text, opts={}) {
  return new Paragraph({ children: [new TextRun({ text, font:'Arial', size: opts.size||20, bold: opts.bold||false, color: opts.color||'000000' })] });
}
function sp() { return new Paragraph({ children: [new TextRun('')] }); }
function bullet(text) {
  return new Paragraph({ numbering: { reference:'bullets', level:0 }, children: [new TextRun({ text, font:'Arial', size:20 })] });
}
function pb() { return new Paragraph({ children: [new PageBreak()] }); }

// ═══════════════════════════════════════════════════════════════════════════════
const now = new Date().toLocaleDateString('en-GB', { day:'2-digit', month:'long', year:'numeric' });

const doc = new Document({
  numbering: {
    config: [{
      reference: 'bullets',
      levels: [{ level:0, format:LevelFormat.BULLET, text:'•', alignment:AlignmentType.LEFT,
        style:{ paragraph:{ indent:{ left:720, hanging:360 } } } }]
    }]
  },
  styles: {
    default: { document: { run: { font:'Arial', size:20 } } },
    paragraphStyles: [
      { id:'Heading1', name:'Heading 1', basedOn:'Normal', next:'Normal', quickFormat:true,
        run:{ size:32, bold:true, font:'Arial', color:DARK_BLUE },
        paragraph:{ spacing:{ before:360, after:120 }, outlineLevel:0,
          border:{ bottom:{ style:BorderStyle.SINGLE, size:4, color:DARK_BLUE, space:4 } } } },
      { id:'Heading2', name:'Heading 2', basedOn:'Normal', next:'Normal', quickFormat:true,
        run:{ size:26, bold:true, font:'Arial', color:MID_BLUE },
        paragraph:{ spacing:{ before:240, after:120 }, outlineLevel:1 } },
      { id:'Heading3', name:'Heading 3', basedOn:'Normal', next:'Normal', quickFormat:true,
        run:{ size:22, bold:true, font:'Arial', color:'283593' },
        paragraph:{ spacing:{ before:180, after:80 }, outlineLevel:2 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width:11906, height:16838 },
        margin: { top:MARGINS, right:MARGINS, bottom:MARGINS, left:MARGINS }
      }
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        border: { bottom: { style:BorderStyle.SINGLE, size:4, color:DARK_BLUE, space:4 } },
        children: [
          new TextRun({ text:'NFE Electricity Theft Detection  |  Raspberry Pi User Guide', font:'Arial', size:18, color:DARK_BLUE }),
          new TextRun({ text:'\t', font:'Arial', size:18 }),
          new TextRun({ text:'v1.0', font:'Arial', size:18, color:'999999' }),
        ]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        border: { top: { style:BorderStyle.SINGLE, size:4, color:DARK_BLUE, space:4 } },
        children: [
          new TextRun({ text:'Page ', font:'Arial', size:18, color:'666666' }),
          new TextRun({ children:[PageNumber.CURRENT], font:'Arial', size:18, color:'666666' }),
          new TextRun({ text:' of ', font:'Arial', size:18, color:'666666' }),
          new TextRun({ children:[PageNumber.TOTAL_PAGES], font:'Arial', size:18, color:'666666' }),
          new TextRun({ text:'\t\tNFE Project  |  '+now, font:'Arial', size:18, color:'999999' }),
        ]
      })] })
    },
    children: [

      // ── COVER ──────────────────────────────────────────────────────────────
      sp(), sp(),
      new Paragraph({ alignment:AlignmentType.CENTER, children:[new TextRun({ text:'NFE Electricity Theft Detection System', font:'Arial', size:28, color:'37474f' })] }),
      sp(),
      new Paragraph({ alignment:AlignmentType.CENTER, children:[new TextRun({ text:'Raspberry Pi — Complete User Guide', font:'Arial', size:44, bold:true, color:DARK_BLUE })] }),
      sp(),
      new Paragraph({ border:{ bottom:{style:BorderStyle.SINGLE,size:6,color:DARK_BLUE,space:4} }, children:[new TextRun('')] }),
      sp(),

      twoColTable([
        ['Item', 'Details'],
        ['Document', 'Pi Connection, Meter Testing & Data Collection'],
        ['Meter', 'CHINT DTSU666 Three-Phase Energy Meter'],
        ['Pi Hostname', 'nfetestpi2'],
        ['Version', '1.0'],
        ['Date', now],
        ['Audience', 'Any user — no technical background required'],
      ], [CONTENT_W*0.28, CONTENT_W*0.72]),

      sp(),
      tip('This guide covers everything you need to connect to the Pi, test the meter, collect data, and retrieve it to your PC. Follow the steps in order — each section is self-contained.'),
      sp(),

      // TOC
      h2('Contents'),
      twoColTable([
        ['Section', 'Page'],
        ['1.  Connecting via Ethernet (direct cable)', '2'],
        ['2.  Connecting via Shared WiFi', '3'],
        ['3.  Connecting via Raspberry Pi Connect (anywhere)', '4'],
        ['4.  Testing the Connection to the Energy Meter', '5'],
        ['5.  Collecting and Saving Meter Data on the Pi', '6'],
        ['6.  Transferring Data from the Pi to Your PC', '8'],
        ['7.  Quick Reference Card', '9'],
      ], [CONTENT_W*0.82, CONTENT_W*0.18]),

      pb(),

      // ── SECTION 1 — ETHERNET ───────────────────────────────────────────────
      h1('1.  Connecting via Ethernet (Direct Cable)'),
      para('This method uses a network cable plugged directly between your laptop and the Pi. It is the fastest and most reliable connection — use it whenever you are sitting next to the Pi.'),
      sp(),
      h3('What you need'),
      bullet('A standard Ethernet / LAN cable (RJ45)'),
      bullet('Your laptop with an Ethernet port (or a USB-to-Ethernet adapter)'),
      sp(),
      h3('Steps'),
      stepsTable([
        'Plug one end of the Ethernet cable into your laptop\'s Ethernet port and the other end into the Pi\'s Ethernet port.',
        'Power on the Pi. Wait about 30 seconds for it to fully boot up.',
        'Open a terminal on your laptop:  Windows: Press Win + R, type cmd, press Enter.  Mac/Linux: Open the Terminal app.',
        'Type the command below and press Enter:',
      ]),
      sp(),
      codeBlock('ssh nfetestpi2@192.168.10.2'),
      sp(),
      stepsTable([
        'If asked "Are you sure you want to continue connecting?" — type yes and press Enter.',
        'Enter the password: nfetestpi2   (you will not see it being typed — that is normal).',
        'You are now connected. You should see the Pi command prompt on screen.',
      ]),
      sp(),
      note('NOTE: Your laptop\'s Ethernet adapter must be set to static IP 192.168.10.1 for this to work. This was already configured during project setup. If it stops working, check your Network Adapter settings in Windows.'),

      pb(),

      // ── SECTION 2 — WIFI ───────────────────────────────────────────────────
      h1('2.  Connecting via Shared WiFi'),
      para('This method uses your home WiFi network. Both your laptop and the Pi must be connected to the same WiFi network. No cable is needed.'),
      sp(),
      h3('What you need'),
      bullet('Laptop connected to your home WiFi network'),
      bullet('Pi powered on and within WiFi range'),
      sp(),
      h3('Steps'),
      stepsTable([
        'Make sure your laptop is connected to your home WiFi network.',
        'Power on the Pi. Wait about 30 seconds for it to boot and connect to WiFi.',
        'Open a terminal on your laptop (Win + R, type cmd, press Enter).',
        'Type the command below and press Enter:',
      ]),
      sp(),
      codeBlock('ssh nfetestpi2@192.168.100.11'),
      sp(),
      stepsTable([
        'Enter the password: nfetestpi2',
        'You are now connected to the Pi over WiFi.',
      ]),
      sp(),
      tip('TIP: If the connection fails, the Pi may have received a different IP address from your router. Open Command Prompt and run:  arp -a  — look for a device with an address starting with 192.168.100.xx'),
      sp(),
      note('NOTE: This method only works when you are physically at home on the same WiFi network as the Pi. For remote access from anywhere in the world, use Section 3 (Raspberry Pi Connect).'),

      pb(),

      // ── SECTION 3 — PI CONNECT ─────────────────────────────────────────────
      h1('3.  Connecting via Raspberry Pi Connect (Anywhere)'),
      para('Raspberry Pi Connect lets you access your Pi from anywhere in the world using just a web browser — no cable, no VPN, no special setup needed. You only need an internet connection on the device you are using.'),
      sp(),
      h3('What you need'),
      bullet('Any device with a web browser (laptop, phone, or tablet)'),
      bullet('Internet connection on that device'),
      bullet('Your Raspberry Pi ID login credentials (email and password)'),
      bullet('Pi must be powered on and connected to your home WiFi'),
      sp(),
      h3('Steps'),
      stepsTable([
        'Open your web browser and go to:',
      ]),
      sp(),
      codeBlock('https://connect.raspberrypi.com'),
      sp(),
      stepsTable([
        'Click Sign In and enter your Raspberry Pi ID email and password.',
        'You will see a list of your devices. Find your Pi by the name you gave it when setting it up.',
        'Click on the device name.',
        'Click Remote Shell — this opens a terminal directly in your browser.',
        'You are now connected. You can run any command just like in a normal terminal.',
      ]),
      sp(),
      tip('TIP: Bookmark https://connect.raspberrypi.com for quick access. You can also use it from your phone when you are away from home.'),
      sp(),
      note('NOTE: The Pi must be powered on and connected to WiFi for Raspberry Pi Connect to work. If the device shows as Offline, check that the Pi has power and is connected to your home WiFi.'),
      sp(),
      warn('WARNING: Raspberry Pi Connect requires the Pi to have internet access via your home WiFi. If your home internet is down, this method will not work — use Ethernet (Section 1) instead.'),

      pb(),

      // ── SECTION 4 — METER TEST ─────────────────────────────────────────────
      h1('4.  Testing the Connection to the Energy Meter'),
      para('Before collecting data, verify that the Pi can communicate with the CHINT DTSU666 energy meter via the RS485/Modbus connection. This script reads live values from the meter and tells you if everything is working correctly.'),
      sp(),
      h3('Before you start — check the following'),
      bullet('RS485-to-USB adapter is plugged into the Pi\'s USB port'),
      bullet('RS485 cable is connected from the adapter to the meter terminals (A+  and  B-)'),
      bullet('The energy meter is powered on'),
      sp(),
      h3('Steps'),
      stepsTable([
        'Connect to the Pi using any method from Sections 1, 2, or 3.',
        'Navigate to the project folder:',
      ]),
      sp(),
      codeBlock('cd ~/iot_meter'),
      sp(),
      stepsTable([
        'Run the meter test script:',
      ]),
      sp(),
      codeBlock('python3 scripts/modbus_test.py'),
      sp(),
      stepsTable([
        'Wait a few seconds. The script will try to read from the meter and display the results.',
      ]),
      sp(),
      h3('What a SUCCESSFUL result looks like'),
      threeColTable([
        ['Parameter', 'Example Value', 'What it means'],
        ['Voltage A / B / C', '220.5 V  /  220.3 V  /  220.7 V', 'Grid voltage on each phase'],
        ['Current A / B / C', '1.04 A  /  2.30 A  /  0.00 A', 'Current on each phase'],
        ['Power Total', '0.54 kW', 'Total power being consumed'],
        ['Power Factor', '0.99', 'Should be close to 1.0 normally'],
        ['Frequency', '50.1 Hz', 'Grid frequency — should be ~50 Hz'],
        ['Sanity Checks', 'ALL PASS', 'All values are within expected range'],
      ], [Math.round(CONTENT_W*0.28), Math.round(CONTENT_W*0.38), Math.round(CONTENT_W*0.34)]),
      sp(),
      h3('What to do if it FAILS'),
      threeColTable([
        ['Error', 'Likely Cause', 'Fix'],
        ['Timeout / No response', 'RS485 cable not connected or meter off', 'Check cable connections and that meter is powered'],
        ['Port /dev/ttyUSB0 not found', 'USB adapter not plugged in', 'Plug in the RS485-USB adapter to the Pi'],
        ['Port is busy', 'Another script is already using it', 'Stop any running collection service first'],
        ['Wrong values (e.g. 0 Volts)', 'Wiring issue on A+/B- terminals', 'Swap the A and B wires on the meter side'],
      ], [Math.round(CONTENT_W*0.28), Math.round(CONTENT_W*0.38), Math.round(CONTENT_W*0.34)]),

      pb(),

      // ── SECTION 5 — DATA COLLECTION ────────────────────────────────────────
      h1('5.  Collecting and Saving Meter Data on the Pi'),
      para('Data is collected using a Python script that reads the meter every 5 seconds and saves each reading to a CSV file on the Pi. There are two ways to run it: manually (for short tests) or as a background service (recommended for long collections).'),
      sp(),
      h2('5.1  Manual Collection (for short tests)'),
      stepsTable([
        'Connect to the Pi and go to the project folder:',
      ]),
      sp(),
      codeBlock('cd ~/iot_meter'),
      sp(),
      stepsTable([
        'Run the collection script. Replace LABEL with your scenario name and SECONDS with how long to collect:',
      ]),
      sp(),
      codeBlock('python3 scripts/collect_data.py --label normal --duration 900'),
      sp(),
      tip('Values for --label:  normal  |  bypass_red  |  bypass_yellow  |  bypass_blue  |  bypass_all'),
      sp(),
      tip('Values for --duration:  900 = 15 minutes  |  3600 = 1 hour  |  86400 = 24 hours'),
      sp(),
      stepsTable([
        'The script will print each reading to the screen as it collects.',
        'When the duration ends, it saves the file automatically to  data/normal.csv  (or your chosen label).',
        'To stop early, press Ctrl + C.',
      ]),
      sp(),
      h2('5.2  Background Service (recommended for long collections)'),
      para('For collections that run for hours or overnight, use a background service. This keeps collecting even if you close the terminal, disconnect SSH, or the Pi loses power and reboots.'),
      sp(),
      h3('Check if a service is running'),
      codeBlock('systemctl status bypass-yellow-collection.service'),
      sp(),
      para('Look for:  Active: active (running)  — this means data is being collected.'),
      sp(),
      h3('Watch live data as it is collected'),
      codeBlock('tail -f ~/iot_meter/data/bypass_yellow.csv'),
      sp(),
      para('Press Ctrl + C to stop watching. This does NOT stop data collection.'),
      sp(),
      h3('Count how many rows have been collected'),
      codeBlock('wc -l ~/iot_meter/data/bypass_yellow.csv'),
      sp(),
      h3('Stop a collection service early'),
      codeBlock('sudo systemctl stop bypass-yellow-collection.service\nsudo systemctl disable bypass-yellow-collection.service'),
      sp(),
      h2('5.3  What the data looks like — CSV columns'),
      threeColTable([
        ['Column Name', 'Description', 'Example'],
        ['timestamp', 'Date and time of reading', '2026-04-06T12:00:00'],
        ['scenario', 'Label name you gave', 'bypass_yellow'],
        ['label', '0 = normal  |  1 = theft', '1'],
        ['V_L1 / V_L2 / V_L3', 'Voltage on each phase (Volts)', '213.1'],
        ['I_L1 / I_L2 / I_L3', 'Current on each phase (Amps)', '19.1'],
        ['P_total', 'Total active power (kW)', '4.226'],
        ['P_L1 / P_L2 / P_L3', 'Active power per phase (kW)', '3.681'],
        ['PF_total', 'Power factor (0 to 1)', '0.99'],
        ['frequency', 'Grid frequency (Hz)', '50.12'],
        ['energy_total', 'Cumulative energy reading (kWh)', '17.77'],
      ], [Math.round(CONTENT_W*0.28), Math.round(CONTENT_W*0.42), Math.round(CONTENT_W*0.30)]),

      pb(),

      // ── SECTION 6 — TRANSFER DATA ──────────────────────────────────────────
      h1('6.  Transferring Data from the Pi to Your PC'),
      para('After data has been collected on the Pi, copy it to your Windows laptop for analysis and report generation.'),
      sp(),
      h2('Method A — Using SCP Command (Recommended)'),
      para('SCP copies a file from the Pi directly to your laptop over the network.'),
      sp(),
      stepsTable([
        'Open Command Prompt on your laptop  (Win + R, type cmd, press Enter).',
        'Run the command below. Change bypass_yellow.csv to whichever file you want:',
      ]),
      sp(),
      codeBlock('scp nfetestpi2@192.168.100.11:/home/nfetestpi2/iot_meter/data/bypass_yellow.csv D:\\path\\to\\your\\folder\\bypass_yellow.csv'),
      sp(),
      stepsTable([
        'Enter the password: nfetestpi2 when prompted.',
        'The file will be saved to the location you specified on your PC.',
      ]),
      sp(),
      tip('TIP: If using Ethernet cable, replace 192.168.100.11 with 192.168.10.2 in the command above.'),
      sp(),
      h2('Method B — View Data via Raspberry Pi Connect'),
      para('If you are connected via Raspberry Pi Connect, you can read the data directly in the browser terminal without copying to your PC.'),
      sp(),
      stepsTable([
        'Connect via https://connect.raspberrypi.com and open Remote Shell.',
        'View the last 10 rows of any dataset:',
      ]),
      sp(),
      codeBlock('tail -10 ~/iot_meter/data/bypass_yellow.csv'),
      sp(),
      h2('Where files are stored on the Pi'),
      twoColTable([
        ['File', 'Location on Pi'],
        ['Normal baseline data', '/home/nfetestpi2/iot_meter/data/normal_final.csv'],
        ['Bypass Red data', '/home/nfetestpi2/iot_meter/data/bypass_red.csv'],
        ['Bypass Yellow data', '/home/nfetestpi2/iot_meter/data/bypass_yellow.csv'],
        ['Collection logs', '/home/nfetestpi2/iot_meter/logs/'],
      ], [CONTENT_W*0.35, CONTENT_W*0.65]),

      pb(),

      // ── SECTION 7 — QUICK REFERENCE ────────────────────────────────────────
      h1('7.  Quick Reference Card'),
      h2('Pi Login Details'),
      twoColTable([
        ['Item', 'Value'],
        ['Hostname', 'nfetestpi2'],
        ['Password', 'nfetestpi2'],
        ['Ethernet IP', '192.168.10.2'],
        ['WiFi IP', '192.168.100.11'],
        ['Pi Connect URL', 'https://connect.raspberrypi.com'],
        ['WiFi network', 'Your home WiFi network'],
        ['Project folder', '~/iot_meter'],
        ['Data folder', '~/iot_meter/data/'],
        ['Logs folder', '~/iot_meter/logs/'],
      ], [CONTENT_W*0.35, CONTENT_W*0.65]),

      sp(),
      h2('Most Used Commands'),
      twoColTable([
        ['Task', 'Command'],
        ['SSH via WiFi', 'ssh nfetestpi2@192.168.100.11'],
        ['SSH via Ethernet', 'ssh nfetestpi2@192.168.10.2'],
        ['Go to project folder', 'cd ~/iot_meter'],
        ['Test meter connection', 'python3 scripts/modbus_test.py'],
        ['Start manual collection (15 min)', 'python3 scripts/collect_data.py --label normal --duration 900'],
        ['Check service status', 'systemctl status bypass-yellow-collection.service'],
        ['Watch live data', 'tail -f ~/iot_meter/data/bypass_yellow.csv'],
        ['Count rows collected', 'wc -l ~/iot_meter/data/bypass_yellow.csv'],
        ['Stop collection service', 'sudo systemctl stop bypass-yellow-collection.service'],
        ['Check Pi date/time', 'date'],
        ['Check boot/reboot history', 'journalctl --list-boots'],
        ['Copy file to PC (WiFi)', 'scp nfetestpi2@192.168.100.11:/home/nfetestpi2/iot_meter/data/FILE.csv D:\\folder\\FILE.csv'],
        ['Shut down Pi safely', 'sudo shutdown now'],
        ['Reboot Pi', 'sudo reboot'],
      ], [CONTENT_W*0.38, CONTENT_W*0.62]),

    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(OUT, buffer);
  console.log('DOCX saved -> ' + OUT);
});
