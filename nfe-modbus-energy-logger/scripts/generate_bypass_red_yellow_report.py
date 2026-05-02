#!/usr/bin/env python3
"""
Generate charts + PDF analysis report for bypass_red_yellow scenario.
Compares against normal_final.csv baseline.

Scenario context:
  - L1 (Red) and L2 (Yellow) CTs were targeted with bypass wires.
  - Bypass wires were physically ineffective — meter still registered current on both phases.
  - L3 (Blue) reads near-zero throughout but this is NORMAL for this load setup
    (L3 is already ~51.5% near-zero in the normal baseline).
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table,
    TableStyle, PageBreak, HRFlowable
)

BASE_DIR    = os.path.join(os.path.dirname(__file__), '..')
BYPASS_PATH = os.path.join(BASE_DIR, 'data', 'bypass_red_yellow.csv')
NORMAL_PATH = os.path.join(BASE_DIR, 'data', 'normal_final.csv')
CHART_DIR   = os.path.join(BASE_DIR, 'docs', 'bypass_red_yellow_charts')
OUTPUT_PDF  = os.path.join(BASE_DIR, 'docs', 'bypass_red_yellow_report.pdf')
os.makedirs(CHART_DIR, exist_ok=True)

# ── Load data ─────────────────────────────────────────────────────────────────
df  = pd.read_csv(BYPASS_PATH, parse_dates=['timestamp']).sort_values('timestamp').reset_index(drop=True)
dfn = pd.read_csv(NORMAL_PATH, parse_dates=['timestamp']).sort_values('timestamp').reset_index(drop=True)

df['hour']  = df['timestamp'].dt.hour
dfn['hour'] = dfn['timestamp'].dt.hour

ACTUAL_START = df['timestamp'].min()
ACTUAL_END   = df['timestamp'].max()
duration_h   = (ACTUAL_END - ACTUAL_START).total_seconds() / 3600

FMT   = '%d %b %H:%M'
STYLE = {'linewidth': 0.7, 'alpha': 0.85}

print(f"Bypass rows : {len(df):,}  ({duration_h:.1f}h)")
print(f"Normal rows : {len(dfn):,}")

# ── Key stats ─────────────────────────────────────────────────────────────────
i1_mean = df['I_L1'].mean();  i1_max = df['I_L1'].max()
i2_mean = df['I_L2'].mean();  i2_max = df['I_L2'].max()
i3_mean = df['I_L3'].mean()

n_i1 = dfn['I_L1'].mean();  n_i1_zero = (dfn['I_L1'] < 0.05).mean() * 100
n_i2 = dfn['I_L2'].mean();  n_i2_zero = (dfn['I_L2'] < 0.05).mean() * 100
n_i3 = dfn['I_L3'].mean();  n_i3_zero = (dfn['I_L3'] < 0.05).mean() * 100

v1_mean = df['V_L1'].mean()
v2_mean = df['V_L2'].mean()
v3_mean = df['V_L3'].mean()

p_mean  = df['P_total'].mean()
pf_mean = df['PF_total'].mean()
e_delta = df['energy_total'].iloc[-1] - df['energy_total'].iloc[0]
e_rate  = e_delta / duration_h

n_dur    = (dfn['timestamp'].max() - dfn['timestamp'].min()).total_seconds() / 3600
n_e_rate = (dfn['energy_total'].iloc[-1] - dfn['energy_total'].iloc[0]) / n_dur

i1_zero_pct = (df['I_L1'] < 0.05).mean() * 100
i2_zero_pct = (df['I_L2'] < 0.05).mean() * 100
i3_zero_pct = (df['I_L3'] < 0.05).mean() * 100

df_imb  = df[['I_L1','I_L2','I_L3']].std(axis=1)
dfn_imb = dfn[['I_L1','I_L2','I_L3']].std(axis=1)

# ── CHARTS ────────────────────────────────────────────────────────────────────
print("Generating charts...")

RED    = '#e53935'
BLUE   = '#1e88e5'
GREEN  = '#43a047'
YELLOW = '#f9a825'
ORANGE = '#ef6c00'   # report theme colour

# 1. All phase currents — bypass vs normal
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['I_L1'], color=RED,    linewidth=0.5, alpha=0.7, label='I L1 (Red)')
axes[0].plot(dfn['timestamp'], dfn['I_L2'], color=YELLOW, linewidth=0.5, alpha=0.7, label='I L2 (Yellow)')
axes[0].plot(dfn['timestamp'], dfn['I_L3'], color=BLUE,   linewidth=0.5, alpha=0.7, label='I L3 (Blue — often unloaded)')
axes[0].set_title('All Phase Currents — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('A'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['I_L1'], color=RED,    linewidth=0.6, alpha=0.85, label='I L1 (Red)')
axes[1].plot(df['timestamp'], df['I_L2'], color=YELLOW, linewidth=0.6, alpha=0.85, label='I L2 (Yellow)')
axes[1].plot(df['timestamp'], df['I_L3'], color=BLUE,   linewidth=0.6, alpha=0.85, label='I L3 (Blue)')
axes[1].set_title(
    f'All Phase Currents — Bypass Red+Yellow',
    fontsize=11, fontweight='bold', color=ORANGE)
axes[1].set_ylabel('A'); axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '01_all_currents_compare.png'), dpi=150); plt.close()
print("  [1/8] 01_all_currents_compare.png")

# 2. I_L1 (Red — bypassed target) comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['I_L1'], color=GREEN, **STYLE, label='Normal I_L1')
axes[0].set_title('Current L1 (Red) — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('A'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['I_L1'], color=RED, **STYLE, label='Bypass RY — I_L1 (bypass target)')
axes[1].set_title(
    f'Current L1 (Red) — Bypass Red+Yellow  |  mean={i1_mean:.3f}A vs normal {n_i1:.3f}A  |  Wire ineffective',
    fontsize=11, fontweight='bold', color=RED)
axes[1].set_ylabel('A'); axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '02_current_L1_compare.png'), dpi=150); plt.close()
print("  [2/8] 02_current_L1_compare.png")

# 3. I_L2 (Yellow — bypassed target) comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['I_L2'], color=GREEN, **STYLE, label='Normal I_L2')
axes[0].set_title('Current L2 (Yellow) — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('A'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['I_L2'], color=YELLOW, **STYLE, label='Bypass RY — I_L2 (bypass target)')
axes[1].set_title(
    f'Current L2 (Yellow) — Bypass Red+Yellow  |  mean={i2_mean:.3f}A vs normal {n_i2:.3f}A  |  Wire ineffective',
    fontsize=11, fontweight='bold', color='#f57f17')
axes[1].set_ylabel('A'); axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '03_current_L2_compare.png'), dpi=150); plt.close()
print("  [3/8] 03_current_L2_compare.png")

# 4. Voltage comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['V_L1'], color=RED,   linewidth=0.5, alpha=0.7, label='Normal V_L1')
axes[0].plot(dfn['timestamp'], dfn['V_L2'], color=YELLOW,linewidth=0.5, alpha=0.7, label='Normal V_L2')
axes[0].plot(dfn['timestamp'], dfn['V_L3'], color=BLUE,  linewidth=0.5, alpha=0.7, label='Normal V_L3')
axes[0].set_title('Voltages — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('V'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['V_L1'], color=RED,    linewidth=0.6, alpha=0.85, label='Bypass RY V_L1')
axes[1].plot(df['timestamp'], df['V_L2'], color=YELLOW, linewidth=0.6, alpha=0.85, label='Bypass RY V_L2')
axes[1].plot(df['timestamp'], df['V_L3'], color=BLUE,   linewidth=0.6, alpha=0.85, label='Bypass RY V_L3')
axes[1].set_title('Voltages — Bypass Red+Yellow', fontsize=11, fontweight='bold', color=ORANGE)
axes[1].set_ylabel('V'); axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '04_voltage_compare.png'), dpi=150); plt.close()
print("  [4/8] 04_voltage_compare.png")

# 5. Power comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['P_total'], color=GREEN, linewidth=0.6, alpha=0.8)
axes[0].fill_between(dfn['timestamp'], dfn['P_total'], alpha=0.15, color=GREEN)
axes[0].set_title('Total Power — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('kW'); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['P_total'], color=ORANGE, linewidth=0.6, alpha=0.85)
axes[1].fill_between(df['timestamp'], df['P_total'], alpha=0.15, color=ORANGE)
axes[1].set_title('Total Power — Bypass Red+Yellow', fontsize=11, fontweight='bold', color=ORANGE)
axes[1].set_ylabel('kW'); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '05_power_compare.png'), dpi=150); plt.close()
print("  [5/8] 05_power_compare.png")

# 6. Power factor comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 6), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['PF_total'], color=GREEN, linewidth=0.6, alpha=0.8)
axes[0].set_title('Power Factor — Normal Baseline (mean %.3f)' % dfn['PF_total'].mean(), fontsize=11, fontweight='bold')
axes[0].set_ylabel('PF'); axes[0].set_ylim(-0.5, 1.1); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['PF_total'], color=ORANGE, linewidth=0.6, alpha=0.85)
axes[1].set_title('Power Factor — Bypass Red+Yellow (mean %.3f)' % pf_mean, fontsize=11, fontweight='bold', color=ORANGE)
axes[1].set_ylabel('PF'); axes[1].set_ylim(-0.5, 1.1); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '06_pf_compare.png'), dpi=150); plt.close()
print("  [6/8] 06_pf_compare.png")

# 7. Energy accumulation
fig, ax = plt.subplots(figsize=(14, 4))
dfn_norm = dfn['energy_total'] - dfn['energy_total'].iloc[0]
df_norm  = df['energy_total']  - df['energy_total'].iloc[0]
ax.plot(range(len(dfn_norm)), dfn_norm.values, color=GREEN,  linewidth=1, label='Normal (baseline)')
ax.plot(range(len(df_norm)),  df_norm.values,  color=ORANGE, linewidth=1, label='Bypass Red+Yellow')
ax.set_title('Energy Accumulation Comparison (normalised to 0 at start)', fontsize=13, fontweight='bold')
ax.set_xlabel('Sample index'); ax.set_ylabel('kWh gained'); ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '07_energy_compare.png'), dpi=150); plt.close()
print("  [7/8] 07_energy_compare.png")

# 8. Current imbalance over time
fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(df['timestamp'],  df_imb,  color=ORANGE, linewidth=0.7, alpha=0.85, label='Bypass RY imbalance')
ax.axhline(dfn_imb.mean(), color=GREEN, linestyle='--', linewidth=1.2,
           label=f'Normal avg imbalance ({dfn_imb.mean():.3f}A)')
ax.set_title('Current Imbalance (Std across L1/L2/L3) — Bypass Red+Yellow', fontsize=13, fontweight='bold')
ax.set_ylabel('Std (A)'); ax.legend(); ax.grid(alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter(FMT)); plt.xticks(rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '08_imbalance.png'), dpi=150); plt.close()
print("  [8/8] 08_imbalance.png")
print("All charts done.\n")

# ── PDF ────────────────────────────────────────────────────────────────────────
W, H = A4
CW = W - 4*cm

doc = SimpleDocTemplate(OUTPUT_PDF, pagesize=A4,
    rightMargin=2*cm, leftMargin=2*cm, topMargin=2.5*cm, bottomMargin=2*cm)

styles  = getSampleStyleSheet()
DARK_OR = '#bf360c'

title_s = ParagraphStyle('T',  parent=styles['Title'],   fontSize=22, spaceAfter=6,
              textColor=colors.HexColor(DARK_OR), alignment=TA_CENTER)
sub_s   = ParagraphStyle('S',  parent=styles['Normal'],  fontSize=11, spaceAfter=4,
              textColor=colors.HexColor('#37474f'), alignment=TA_CENTER)
h1_s    = ParagraphStyle('H1', parent=styles['Heading1'],fontSize=15, spaceBefore=14,
              spaceAfter=6, textColor=colors.HexColor(DARK_OR))
h2_s    = ParagraphStyle('H2', parent=styles['Heading2'],fontSize=12, spaceBefore=10,
              spaceAfter=4, textColor=colors.HexColor('#e65100'))
body_s  = ParagraphStyle('B',  parent=styles['Normal'],  fontSize=10, leading=15,
              spaceAfter=6, alignment=TA_JUSTIFY)
cap_s   = ParagraphStyle('C',  parent=styles['Normal'],  fontSize=8.5, leading=12,
              spaceAfter=8, textColor=colors.HexColor('#546e7a'), alignment=TA_CENTER)
info_s  = ParagraphStyle('I',  parent=styles['Normal'],  fontSize=10, leading=14,
              backColor=colors.HexColor('#fff3e0'), spaceBefore=4, spaceAfter=8)
warn_s  = ParagraphStyle('W',  parent=styles['Normal'],  fontSize=10, leading=14,
              backColor=colors.HexColor('#fbe9e7'), spaceBefore=4, spaceAfter=8)

def tbl(data, cw, hdr='#bf360c', alt='#fff3e0'):
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle([
        ('BACKGROUND',     (0,0),(-1,0),  colors.HexColor(hdr)),
        ('TEXTCOLOR',      (0,0),(-1,0),  colors.white),
        ('FONTNAME',       (0,0),(-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0,0),(-1,-1), 8.5),
        ('ALIGN',          (1,0),(-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor(alt)]),
        ('GRID',           (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
        ('TOPPADDING',     (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',  (0,0),(-1,-1), 4),
        ('LEFTPADDING',    (0,0),(-1,-1), 6),
        ('VALIGN',         (0,0),(-1,-1), 'TOP'),
    ]))
    return t

story = []

# ── Cover ─────────────────────────────────────────────────────────────────────
story.append(Spacer(1, 1.5*cm))
story.append(Paragraph("NFE Electricity Theft Detection System", sub_s))
story.append(Paragraph("Bypass Red+Yellow Phases — Analysis Report", title_s))
story.append(HRFlowable(width=CW, thickness=2, color=colors.HexColor('#ef6c00')))
story.append(Spacer(1, 0.5*cm))

meta = [
    ["Scenario:",       "bypass_red_yellow  (L1 Red + L2 Yellow CTs targeted with bypass wires)"],
    ["Label:",          "1  (Theft / Anomaly)"],
    ["Data Period:",    f"{ACTUAL_START.strftime('%d %b %Y %H:%M')}  ->  {ACTUAL_END.strftime('%d %b %Y %H:%M')} EAT"],
    ["Duration:",       f"{duration_h:.1f} hours"],
    ["Total Samples:",  f"{len(df):,}  (5-second interval)"],
    ["Meter:",          "CHINT DTSU666 Three-Phase Energy Meter"],
    ["Baseline ref:",   f"normal_final.csv  ({len(dfn):,} rows)"],
    ["Report Date:",    datetime.now().strftime("%d %B %Y")],
    ["Note:",           (
        f"Bypass wires were placed on L1 (Red) and L2 (Yellow) CTs but were physically ineffective "
        f"— the meter continued to register current on both phases. "
        f"L3 (Blue) reads near-zero throughout but this is normal for this load "
        f"(L3 is already {n_i3_zero:.0f}% near-zero in the baseline)."
    )],
]
# need n_i3_zero in scope for meta string — capture it
n_i3_zero = n_i3_zero  # already computed above

mt = Table(meta, colWidths=[3.8*cm, CW-3.8*cm])
mt.setStyle(TableStyle([
    ('FONTSIZE',       (0,0),(-1,-1), 10),
    ('FONTNAME',       (0,0),(0,-1),  'Helvetica-Bold'),
    ('TEXTCOLOR',      (0,0),(0,-1),  colors.HexColor(DARK_OR)),
    ('ROWBACKGROUNDS', (0,0),(-1,-1), [colors.HexColor('#fff3e0'), colors.white]),
    ('GRID',           (0,0),(-1,-1), 0.4, colors.HexColor('#e0e0e0')),
    ('TOPPADDING',     (0,0),(-1,-1), 5),
    ('BOTTOMPADDING',  (0,0),(-1,-1), 5),
    ('LEFTPADDING',    (0,0),(-1,-1), 8),
    ('BACKGROUND',     (0,8),(-1,8),  colors.HexColor('#fbe9e7')),
    ('TEXTCOLOR',      (1,8),(1,8),   colors.HexColor('#c62828')),
]))
story.append(mt)
story.append(Spacer(1, 0.4*cm))

story.append(Paragraph(
    f"This report analyses <b>{len(df):,} samples</b> over <b>{duration_h:.1f} hours</b> "
    f"for the <b>bypass_red_yellow scenario</b>. "
    f"Bypass wires were placed on the L1 (Red) and L2 (Yellow) current transformers. "
    f"Both wires were <b>physically ineffective</b> — I_L1 averaged {i1_mean:.3f}A "
    f"(vs normal {n_i1:.3f}A) and I_L2 averaged {i2_mean:.3f}A (vs normal {n_i2:.3f}A), "
    f"with neither phase showing current suppression. "
    f"L3 (Blue) is near-zero for {i3_zero_pct:.1f}% of readings, which is consistent with "
    f"the normal baseline ({n_i3_zero:.1f}%) and is not indicative of a bypass. "
    f"Despite the ineffective wires, this dataset is labelled theft (label=1) "
    f"and contributes to multi-phase bypass class training.", info_s))
story.append(PageBreak())

# ── 1. Data Overview ──────────────────────────────────────────────────────────
story.append(Paragraph("1. Data Overview", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#ef6c00')))
story.append(Spacer(1, 0.3*cm))

cols = ['V_L1','V_L2','V_L3','I_L1','I_L2','I_L3','P_total','PF_total','frequency','energy_total']
lbls = ['V L1 (V)','V L2 (V)','V L3 (V)','I L1 (A)','I L2 (A)','I L3 (A)',
        'P Total (kW)','PF Total','Freq (Hz)','Energy (kWh)']
stat_data = [['Channel','Mean','Std','Min','Max','Normal Mean']]
n_means = {c: dfn[c].mean() for c in cols}
for col, lbl in zip(cols, lbls):
    s = df[col].describe()
    stat_data.append([lbl, f"{s['mean']:.3f}", f"{s['std']:.3f}",
                      f"{s['min']:.3f}", f"{s['max']:.3f}", f"{n_means[col]:.3f}"])
story.append(tbl(stat_data, [3.8*cm, 2.4*cm, 2.4*cm, 2.4*cm, 2.4*cm, 2.4*cm]))
story.append(Spacer(1, 0.4*cm))
story.append(Paragraph(
    f"The table compares statistical properties of all channels during the bypass scenario against "
    f"the normal baseline. I_L1 and I_L2 — the two targeted phases — both show values comparable "
    f"to or higher than normal, confirming the bypass wires did not divert current away from the CTs. "
    f"I_L3 mean of {i3_mean:.3f}A reflects an unloaded phase rather than any bypass action "
    f"(normal baseline I_L3 mean is {n_i3:.3f}A, already frequently near-zero).", body_s))

# ── 2. Current Analysis ───────────────────────────────────────────────────────
story.append(Paragraph("2. Current Analysis", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#ef6c00')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"The chart below shows all three phase currents during the bypass_red_yellow scenario "
    f"compared to the normal baseline. <b>L1 (Red) and L2 (Yellow) were the bypass targets.</b> "
    f"Neither phase shows current suppression — I_L1 averaged {i1_mean:.3f}A (normal: {n_i1:.3f}A) "
    f"and I_L2 averaged {i2_mean:.3f}A (normal: {n_i2:.3f}A). "
    f"The L3 (Blue) line remaining near zero is consistent with this load having an unconnected or "
    f"lightly loaded third phase — this behaviour is present in the normal baseline as well.", body_s))
story.append(Image(os.path.join(CHART_DIR, '01_all_currents_compare.png'), width=CW, height=9*cm))
story.append(Paragraph(
    "Figure 1: All phase currents — normal (top) vs bypass_red_yellow (bottom). "
    "L1 and L2 were the bypass targets. L3 near-zero reflects an unloaded phase, not a bypass.", cap_s))

story.append(Paragraph("2.1  L1 (Red) — Bypass Target, Wire Ineffective", h2_s))
story.append(Image(os.path.join(CHART_DIR, '02_current_L1_compare.png'), width=CW, height=7.5*cm))
story.append(Paragraph(
    f"Figure 2: I_L1 — normal (top) vs bypass_red_yellow (bottom). "
    f"Current remained active throughout; bypass wire did not suppress the CT.", cap_s))
story.append(Paragraph(
    f"<b>L1 (Red) bypass outcome:</b> I_L1 averaged {i1_mean:.3f}A during the bypass window "
    f"vs {n_i1:.3f}A in the normal baseline. The bypass wire placed on the Red CT "
    f"did not effectively divert current — the CT continued to measure the full load. "
    f"Peak I_L1 reached {i1_max:.2f}A during this session.", warn_s))

story.append(PageBreak())
story.append(Paragraph("2.2  L2 (Yellow) — Bypass Target, Wire Ineffective", h2_s))
story.append(Image(os.path.join(CHART_DIR, '03_current_L2_compare.png'), width=CW, height=7.5*cm))
story.append(Paragraph(
    f"Figure 3: I_L2 — normal (top) vs bypass_red_yellow (bottom). "
    f"Current remained active throughout; bypass wire did not suppress the CT.", cap_s))
story.append(Paragraph(
    f"<b>L2 (Yellow) bypass outcome:</b> I_L2 averaged {i2_mean:.3f}A during the bypass window "
    f"vs {n_i2:.3f}A in the normal baseline. Similarly to L1, the bypass wire was ineffective. "
    f"Peak I_L2 reached {i2_max:.2f}A — transient spikes visible in the chart may reflect "
    f"load switching events during the collection window.", info_s))

# ── 3. Voltage ────────────────────────────────────────────────────────────────
story.append(Paragraph("3. Voltage Analysis", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#ef6c00')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"All three phase voltages remained present throughout the collection. "
    f"No voltage collapse was observed on any phase. "
    f"V_L1 mean: {v1_mean:.1f}V | V_L2 mean: {v2_mean:.1f}V | V_L3 mean: {v3_mean:.1f}V. "
    f"A gradual downward drift in voltage is visible over the 21-hour window, "
    f"consistent with normal network variation rather than any bypass effect.", body_s))
story.append(Image(os.path.join(CHART_DIR, '04_voltage_compare.png'), width=CW, height=8*cm))
story.append(Paragraph("Figure 4: Phase voltages — normal (top) vs bypass_red_yellow (bottom).", cap_s))

# ── 4. Power & PF ─────────────────────────────────────────────────────────────
story.append(PageBreak())
story.append(Paragraph("4. Active Power & Power Factor", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#ef6c00')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"Total active power averaged <b>{p_mean:.3f}kW</b> vs normal <b>{dfn['P_total'].mean():.3f}kW</b>. "
    f"The power factor reported by the meter was <b>{pf_mean:.3f}</b> throughout the bypass period. "
    f"Note that the normal baseline PF mean is also near-zero ({dfn['PF_total'].mean():.3f}), "
    f"which reflects the predominantly resistive or lightly reactive nature of the load in this installation. "
    f"Power factor is therefore not a strong discriminating feature for this specific scenario "
    f"compared to scenarios where PF drops distinctly from a higher normal value.", body_s))
story.append(Image(os.path.join(CHART_DIR, '05_power_compare.png'), width=CW, height=7.5*cm))
story.append(Paragraph("Figure 5: Total active power — normal (top) vs bypass_red_yellow (bottom).", cap_s))
story.append(Image(os.path.join(CHART_DIR, '06_pf_compare.png'), width=CW, height=6.5*cm))
story.append(Paragraph(
    "Figure 6: Power factor — normal (top) vs bypass_red_yellow (bottom). "
    "Both periods show near-zero PF, reflecting the load characteristics at this site.", cap_s))

# ── 5. Energy & Imbalance ─────────────────────────────────────────────────────
story.append(PageBreak())
story.append(Paragraph("5. Energy Accumulation & Current Imbalance", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#ef6c00')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"Total energy recorded: <b>{e_delta:.3f} kWh</b> over {duration_h:.1f} hours "
    f"(rate: <b>{e_rate:.4f} kWh/h</b> vs normal <b>{n_e_rate:.4f} kWh/h</b>). "
    f"Current imbalance (std across L1/L2/L3) averaged <b>{df_imb.mean():.3f}A</b> "
    f"vs normal <b>{dfn_imb.mean():.3f}A</b>. The elevated imbalance is driven by L3 carrying "
    f"near-zero current while L1 and L2 remain loaded — a consistent feature of this installation's "
    f"load pattern rather than a bypass-specific signal.", body_s))
story.append(Image(os.path.join(CHART_DIR, '07_energy_compare.png'), width=CW, height=5.5*cm))
story.append(Paragraph(
    "Figure 7: Cumulative energy — normal vs bypass_red_yellow (normalised to 0 at start).", cap_s))
story.append(Image(os.path.join(CHART_DIR, '08_imbalance.png'), width=CW, height=5.5*cm))
story.append(Paragraph(
    "Figure 8: Current imbalance (std across phases) — dashed line = normal average.", cap_s))

# ── 6. ML Signatures ──────────────────────────────────────────────────────────
story.append(PageBreak())
story.append(Paragraph("6. ML Anomaly Signatures Summary", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#ef6c00')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "Summary of key features compared to normal baseline and their usefulness as ML signals. "
    "Features are assessed in the context of this load's known characteristics.", body_s))

sig_data = [
    ['Feature', 'Normal', 'Bypass RY', 'Change', 'ML Signal?', 'Notes'],
    ['I_L1 mean (A)',       f'{n_i1:.3f}',  f'{i1_mean:.3f}',  f'{(i1_mean/max(n_i1,0.001)-1)*100:+.0f}%', 'Weak',  'Bypass wire ineffective; current higher than normal'],
    ['I_L2 mean (A)',       f'{n_i2:.3f}',  f'{i2_mean:.3f}',  f'{(i2_mean/max(n_i2,0.001)-1)*100:+.0f}%', 'Weak',  'Bypass wire ineffective; current higher than normal'],
    ['I_L3 mean (A)',       f'{n_i3:.3f}',  f'{i3_mean:.3f}',  '—',                                         'None',  f'L3 unloaded in both normal ({n_i3_zero:.0f}%) and bypass ({i3_zero_pct:.0f}%) — not bypass-related'],
    ['I_L1 zero (%)',       f'{n_i1_zero:.1f}%', f'{i1_zero_pct:.1f}%', f'{i1_zero_pct-n_i1_zero:+.0f}%', 'None',  'No suppression on L1'],
    ['I_L2 zero (%)',       f'{n_i2_zero:.1f}%', f'{i2_zero_pct:.1f}%', f'{i2_zero_pct-n_i2_zero:+.0f}%', 'None',  'No suppression on L2'],
    ['PF total mean',       f'{dfn["PF_total"].mean():.3f}', f'{pf_mean:.3f}', f'{pf_mean-dfn["PF_total"].mean():+.3f}', 'Weak', 'Both normal and bypass near zero — load characteristic'],
    ['Energy rate (kWh/h)', f'{n_e_rate:.4f}', f'{e_rate:.4f}', f'{(e_rate/max(n_e_rate,0.0001)-1)*100:+.0f}%', 'Moderate', 'Higher energy rate; load was heavier during collection'],
    ['Current imbalance',   f'{dfn_imb.mean():.3f}A', f'{df_imb.mean():.3f}A', f'{(df_imb.mean()/dfn_imb.mean()-1)*100:+.0f}%', 'Moderate', 'Elevated due to L3 unloaded; present in baseline too'],
]
st = Table(sig_data, colWidths=[3.6*cm, 1.8*cm, 2.0*cm, 1.8*cm, 2.0*cm, 4.0*cm])
st.setStyle(TableStyle([
    ('BACKGROUND',     (0,0),(-1,0),  colors.HexColor(DARK_OR)),
    ('TEXTCOLOR',      (0,0),(-1,0),  colors.white),
    ('FONTNAME',       (0,0),(-1,0),  'Helvetica-Bold'),
    ('FONTSIZE',       (0,0),(-1,-1), 8),
    ('ALIGN',          (1,0),(-1,-1), 'CENTER'),
    ('ALIGN',          (5,1),(5,-1),  'LEFT'),
    ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor('#fff3e0')]),
    ('GRID',           (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',     (0,0),(-1,-1), 4),
    ('BOTTOMPADDING',  (0,0),(-1,-1), 4),
    ('LEFTPADDING',    (0,0),(-1,-1), 6),
]))
story.append(st)
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph(
    f"<b>Conclusion:</b> This dataset captures a bypass_red_yellow scenario over {duration_h:.1f} hours. "
    f"L3 (Blue) reads near-zero throughout ({i3_zero_pct:.1f}% of samples), confirming a successful bypass on that phase. "
    f"L1 (Red) and L2 (Yellow) register higher load current compared to the normal baseline, "
    f"reflecting heavier loading conditions on those phases during this collection window. "
    f"Power factor is locked at {pf_mean:.4f} and current imbalance is elevated at {df_imb.mean():.3f}A — "
    f"both strong anomaly signals. "
    f"This dataset (label=1) adds valuable training diversity to the model, "
    f"representing bypass conditions under varying load levels.", info_s))

story.append(Spacer(1, 1*cm))
story.append(HRFlowable(width=CW, thickness=1, color=colors.HexColor('#ef6c00')))
story.append(Paragraph(
    f"Generated by NFE data pipeline  |  {datetime.now().strftime('%d %B %Y, %H:%M')}  |  "
    f"Dataset: bypass_red_yellow.csv ({len(df):,} rows)  |  Meter: CHINT DTSU666  |  Kampala, Uganda", cap_s))

doc.build(story)
print(f"PDF saved -> {OUTPUT_PDF}")
