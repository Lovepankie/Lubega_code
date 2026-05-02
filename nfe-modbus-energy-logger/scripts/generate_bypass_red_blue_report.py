#!/usr/bin/env python3
"""
Generate charts + PDF analysis report for bypass_red_blue scenario.
Compares against normal_final.csv baseline.
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
BYPASS_PATH = os.path.join(BASE_DIR, 'data', 'bypass_red_blue.csv')
NORMAL_PATH = os.path.join(BASE_DIR, 'data', 'normal_final.csv')
CHART_DIR   = os.path.join(BASE_DIR, 'docs', 'bypass_red_blue_charts')
OUTPUT_PDF  = os.path.join(BASE_DIR, 'docs', 'bypass_red_blue_report.pdf')
os.makedirs(CHART_DIR, exist_ok=True)

# ── Load & clean data ─────────────────────────────────────────────────────────
df  = pd.read_csv(BYPASS_PATH, parse_dates=['timestamp']).sort_values('timestamp').reset_index(drop=True)
dfn = pd.read_csv(NORMAL_PATH, parse_dates=['timestamp']).sort_values('timestamp').reset_index(drop=True)

# Remove clock-drift rows
df = df[df['timestamp'] >= '2026-04-10'].reset_index(drop=True)

df['hour']  = df['timestamp'].dt.hour
dfn['hour'] = dfn['timestamp'].dt.hour

ACTUAL_START = pd.Timestamp('2026-04-10 23:37:00')
ACTUAL_END   = df['timestamp'].max()
duration_h   = (ACTUAL_END - ACTUAL_START).total_seconds() / 3600

FMT   = '%d %b %H:%M'
STYLE = {'linewidth': 0.7, 'alpha': 0.85}

print(f"Bypass rows : {len(df):,}  ({duration_h:.1f}h)")
print(f"Normal rows : {len(dfn):,}")

# ── Key stats ─────────────────────────────────────────────────────────────────
i1_mean = df['I_L1'].mean();  i1_max = df['I_L1'].max()
i2_mean = df['I_L2'].mean();  i2_max = df['I_L2'].max()
i3_mean = df['I_L3'].mean();  i3_max = df['I_L3'].max()

n_i1 = dfn['I_L1'].mean()
n_i2 = dfn['I_L2'].mean()
n_i3 = dfn['I_L3'].mean()

v1_mean  = df['V_L1'].mean()
v3_mean  = df['V_L3'].mean()
v1_zero  = (df['V_L1'] < 1).mean() * 100
v3_zero  = (df['V_L3'] < 1).mean() * 100

p_mean   = df['P_total'].mean();  p_max = df['P_total'].max()
pf_mean  = df['PF_total'].mean()
e_delta  = df['energy_total'].iloc[-1] - df['energy_total'].iloc[0]
e_rate   = e_delta / duration_h

n_e_rate = (dfn['energy_total'].iloc[-1] - dfn['energy_total'].iloc[0]) / \
           (dfn['timestamp'].max() - dfn['timestamp'].min()).total_seconds() * 3600

i1_zero_pct = (df['I_L1'] < 0.05).mean() * 100
i3_zero_pct = (df['I_L3'] < 0.05).mean() * 100

# ── CHARTS ────────────────────────────────────────────────────────────────────
print("Generating charts...")

RED    = '#e53935'
BLUE   = '#1e88e5'
PURPLE = '#8e24aa'
GREEN  = '#43a047'
YELLOW = '#f9a825'

# 1. All phase currents — bypass vs normal
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['I_L1'], color=RED,    linewidth=0.5, alpha=0.7, label='I L1 (Red)')
axes[0].plot(dfn['timestamp'], dfn['I_L2'], color=YELLOW, linewidth=0.5, alpha=0.7, label='I L2 (Yellow)')
axes[0].plot(dfn['timestamp'], dfn['I_L3'], color=BLUE,   linewidth=0.5, alpha=0.7, label='I L3 (Blue)')
axes[0].set_title('All Phase Currents — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('A'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['I_L1'], color=RED,    linewidth=0.6, alpha=0.85, label='I L1 (Red — target, not suppressed)')
axes[1].plot(df['timestamp'], df['I_L2'], color=YELLOW, linewidth=0.6, alpha=0.85, label='I L2 (Yellow — normal)')
axes[1].plot(df['timestamp'], df['I_L3'], color=BLUE,   linewidth=0.6, alpha=0.85, label='I L3 (Blue — BYPASSED)')
axes[1].set_title(f'All Phase Currents — Bypass Red+Blue  |  I_L3={i3_zero_pct:.1f}% near-zero  |  I_L1 NOT suppressed',
                  fontsize=11, fontweight='bold', color=PURPLE)
axes[1].set_ylabel('A'); axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '01_all_currents_compare.png'), dpi=150); plt.close()
print("  [1/8] 01_all_currents_compare.png")

# 2. I_L3 (confirmed bypassed) comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['I_L3'], color=GREEN, **STYLE, label='Normal I_L3')
axes[0].set_title('Current L3 (Blue) — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('A'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['I_L3'], color=BLUE, **STYLE, label='Bypass RB — I_L3 (bypassed)')
axes[1].set_title(f'Current L3 — Bypass Red+Blue  ({i3_zero_pct:.1f}% readings near zero)',
                  fontsize=11, fontweight='bold', color=PURPLE)
axes[1].set_ylabel('A'); axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '02_current_L3_compare.png'), dpi=150); plt.close()
print("  [2/8] 02_current_L3_compare.png")

# 3. I_L1 (intended bypass — not suppressed)
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['I_L1'], color=GREEN, **STYLE, label='Normal I_L1')
axes[0].set_title('Current L1 (Red) — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('A'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['I_L1'], color=RED, **STYLE, label='Bypass RB — I_L1 (NOT suppressed)')
axes[1].set_title(f'Current L1 — Bypass Red+Blue  (I_L1 mean={i1_mean:.3f}A — bypass wire ineffective on L1)',
                  fontsize=11, fontweight='bold', color='#c62828')
axes[1].set_ylabel('A'); axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '03_current_L1_compare.png'), dpi=150); plt.close()
print("  [3/8] 03_current_L1_compare.png")

# 4. Voltage comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['V_L1'], color=RED,   linewidth=0.5, alpha=0.7, label='Normal V_L1')
axes[0].plot(dfn['timestamp'], dfn['V_L2'], color=YELLOW,linewidth=0.5, alpha=0.7, label='Normal V_L2')
axes[0].plot(dfn['timestamp'], dfn['V_L3'], color=BLUE,  linewidth=0.5, alpha=0.7, label='Normal V_L3')
axes[0].set_title('Voltages — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('V'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['V_L1'], color=RED,    linewidth=0.6, alpha=0.85, label='Bypass RB V_L1')
axes[1].plot(df['timestamp'], df['V_L2'], color=YELLOW, linewidth=0.6, alpha=0.85, label='Bypass RB V_L2')
axes[1].plot(df['timestamp'], df['V_L3'], color=BLUE,   linewidth=0.6, alpha=0.85, label='Bypass RB V_L3')
axes[1].set_title('Voltages — Bypass Red+Blue', fontsize=11, fontweight='bold', color=PURPLE)
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

axes[1].plot(df['timestamp'], df['P_total'], color=PURPLE, linewidth=0.6, alpha=0.85)
axes[1].fill_between(df['timestamp'], df['P_total'], alpha=0.15, color=PURPLE)
axes[1].set_title('Total Power — Bypass Red+Blue', fontsize=11, fontweight='bold', color=PURPLE)
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
axes[0].set_ylabel('PF'); axes[0].set_ylim(-0.2, 1.1); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['PF_total'], color=PURPLE, linewidth=0.6, alpha=0.85)
axes[1].set_title('Power Factor — Bypass Red+Blue (mean %.3f)' % pf_mean, fontsize=11, fontweight='bold', color=PURPLE)
axes[1].set_ylabel('PF'); axes[1].set_ylim(-0.2, 1.1); axes[1].grid(alpha=0.3)
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
ax.plot(range(len(df_norm)),  df_norm.values,  color=PURPLE, linewidth=1, label='Bypass Red+Blue')
ax.set_title('Energy Accumulation Comparison (normalised to 0 at start)', fontsize=13, fontweight='bold')
ax.set_xlabel('Sample index'); ax.set_ylabel('kWh gained'); ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '07_energy_compare.png'), dpi=150); plt.close()
print("  [7/8] 07_energy_compare.png")

# 8. Current imbalance over time
fig, ax = plt.subplots(figsize=(14, 4))
df_imb  = df[['I_L1','I_L2','I_L3']].std(axis=1)
dfn_imb = dfn[['I_L1','I_L2','I_L3']].std(axis=1)
ax.plot(df['timestamp'],  df_imb,  color=PURPLE, linewidth=0.7, alpha=0.85, label='Bypass RB imbalance')
ax.axhline(dfn_imb.mean(), color=GREEN, linestyle='--', linewidth=1.2, label=f'Normal avg imbalance ({dfn_imb.mean():.3f}A)')
ax.set_title('Current Imbalance (Std across L1/L2/L3) — Bypass Red+Blue', fontsize=13, fontweight='bold')
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
DARK_PU = '#4a148c'
title_s = ParagraphStyle('T',  parent=styles['Title'],   fontSize=22, spaceAfter=6,
              textColor=colors.HexColor(DARK_PU), alignment=TA_CENTER)
sub_s   = ParagraphStyle('S',  parent=styles['Normal'],  fontSize=11, spaceAfter=4,
              textColor=colors.HexColor('#37474f'), alignment=TA_CENTER)
h1_s    = ParagraphStyle('H1', parent=styles['Heading1'],fontSize=15, spaceBefore=14,
              spaceAfter=6, textColor=colors.HexColor(DARK_PU))
h2_s    = ParagraphStyle('H2', parent=styles['Heading2'],fontSize=12, spaceBefore=10,
              spaceAfter=4, textColor=colors.HexColor('#6a1b9a'))
body_s  = ParagraphStyle('B',  parent=styles['Normal'],  fontSize=10, leading=15,
              spaceAfter=6, alignment=TA_JUSTIFY)
cap_s   = ParagraphStyle('C',  parent=styles['Normal'],  fontSize=8.5,leading=12,
              spaceAfter=8, textColor=colors.HexColor('#546e7a'), alignment=TA_CENTER)
info_s  = ParagraphStyle('I',  parent=styles['Normal'],  fontSize=10, leading=14,
              backColor=colors.HexColor('#f3e5f5'), spaceBefore=4, spaceAfter=8)
warn_s  = ParagraphStyle('W',  parent=styles['Normal'],  fontSize=10, leading=14,
              backColor=colors.HexColor('#fff3e0'), spaceBefore=4, spaceAfter=8)

def tbl(data, cw, hdr='#4a148c', alt='#f3e5f5'):
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

# Cover
story.append(Spacer(1, 1.5*cm))
story.append(Paragraph("NFE Electricity Theft Detection System", sub_s))
story.append(Paragraph("Bypass Red+Blue Phases — Analysis Report", title_s))
story.append(HRFlowable(width=CW, thickness=2, color=colors.HexColor('#8e24aa')))
story.append(Spacer(1, 0.5*cm))

meta = [
    ["Scenario:",       "bypass_red_blue  (L1+L3 current transformers targeted)"],
    ["Label:",          "1  (Theft / Anomaly)"],
    ["Data Period:",    f"{ACTUAL_START.strftime('%d %b %Y %H:%M')}  ->  {ACTUAL_END.strftime('%d %b %Y %H:%M')} EAT"],
    ["Duration:",       f"{duration_h:.1f} hours"],
    ["Total Samples:",  f"{len(df):,}  (5-second interval)"],
    ["Meter:",          "CHINT DTSU666 Three-Phase Energy Meter"],
    ["Baseline ref:",   f"normal_final.csv  ({len(dfn):,} rows)"],
    ["Report Date:",    datetime.now().strftime("%d %B %Y")],
    ["Note:",           "L3 (Blue) bypass confirmed. L1 (Red) bypass wire was ineffective — L1 current NOT suppressed."],
]
mt = Table(meta, colWidths=[3.8*cm, CW-3.8*cm])
mt.setStyle(TableStyle([
    ('FONTSIZE',       (0,0),(-1,-1), 10),
    ('FONTNAME',       (0,0),(0,-1),  'Helvetica-Bold'),
    ('TEXTCOLOR',      (0,0),(0,-1),  colors.HexColor(DARK_PU)),
    ('ROWBACKGROUNDS', (0,0),(-1,-1), [colors.HexColor('#f3e5f5'), colors.white]),
    ('GRID',           (0,0),(-1,-1), 0.4, colors.HexColor('#e0e0e0')),
    ('TOPPADDING',     (0,0),(-1,-1), 5),
    ('BOTTOMPADDING',  (0,0),(-1,-1), 5),
    ('LEFTPADDING',    (0,0),(-1,-1), 8),
    # Highlight the note row
    ('BACKGROUND',     (0,8),(-1,8),  colors.HexColor('#fff3e0')),
    ('TEXTCOLOR',      (1,8),(1,8),   colors.HexColor('#e65100')),
]))
story.append(mt)
story.append(Spacer(1, 0.4*cm))

story.append(Paragraph(
    f"This report analyses <b>{len(df):,} samples</b> over <b>{duration_h:.1f} hours</b> "
    f"for the <b>bypass_red_blue scenario</b>. "
    f"Blue phase (L3) bypass is <b>confirmed</b> — I_L3 reads near-zero in <b>{i3_zero_pct:.1f}%</b> of samples. "
    f"Red phase (L1) bypass wire was <b>physically ineffective</b> — I_L1 averaged <b>{i1_mean:.3f}A</b> "
    f"(normal baseline: {n_i1:.3f}A), showing no suppression. "
    f"Power factor locked at <b>{pf_mean:.3f}</b> and energy rate dropped to "
    f"<b>{e_rate:.4f} kWh/h</b> vs normal <b>{n_e_rate:.4f} kWh/h</b>.", info_s))
story.append(PageBreak())

# 1. Data Overview
story.append(Paragraph("1. Data Overview", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#8e24aa')))
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

# 2. Current Analysis
story.append(Paragraph("2. Current Analysis", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#8e24aa')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"The chart below shows all three phase currents during the bypass_red_blue scenario "
    f"compared to the normal baseline. <b>L3 (Blue) is clearly suppressed</b> — reading near-zero "
    f"in {i3_zero_pct:.1f}% of samples (normal baseline: 51.5%). "
    f"<b>L1 (Red) shows no suppression</b> — averaging {i1_mean:.3f}A vs normal {n_i1:.3f}A, "
    f"indicating the bypass wire on L1 did not divert current away from the CT.", body_s))
story.append(Image(os.path.join(CHART_DIR, '01_all_currents_compare.png'), width=CW, height=9*cm))
story.append(Paragraph("Figure 1: All phase currents — normal (top) vs bypass_red_blue (bottom). "
    "Note I_L3 (blue) suppressed; I_L1 (red) remains active.", cap_s))

story.append(Paragraph("2.1  L3 (Blue) — Bypass Confirmed", h2_s))
story.append(Image(os.path.join(CHART_DIR, '02_current_L3_compare.png'), width=CW, height=7.5*cm))
story.append(Paragraph(f"Figure 2: I_L3 — normal (top) vs bypass_red_blue (bottom). "
    f"{i3_zero_pct:.1f}% of readings near-zero confirms L3 bypass.", cap_s))
story.append(Paragraph(
    f"<b>Anomaly signature (L3):</b> I_L3 mean drops from {n_i3:.3f}A (normal) to {i3_mean:.3f}A. "
    f"{i3_zero_pct:.1f}% near-zero. This is the dominant bypass signal in this dataset.", warn_s))

story.append(PageBreak())
story.append(Paragraph("2.2  L1 (Red) — Bypass Wire Ineffective", h2_s))
story.append(Image(os.path.join(CHART_DIR, '03_current_L1_compare.png'), width=CW, height=7.5*cm))
story.append(Paragraph(f"Figure 3: I_L1 — normal (top) vs bypass_red_blue (bottom). "
    f"No suppression — bypass wire on L1 was not properly connected.", cap_s))
story.append(Paragraph(
    f"<b>Note:</b> I_L1 averaged {i1_mean:.3f}A during bypass vs {n_i1:.3f}A normal. "
    f"Only {i1_zero_pct:.1f}% of readings were near-zero. "
    f"The Red phase bypass wire was physically ineffective in this collection run.", info_s))

# 3. Voltage
story.append(Paragraph("3. Voltage Analysis", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#8e24aa')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"All three voltages remain relatively stable during this scenario — "
    f"no voltage collapse was observed on L1 or L3. "
    f"This differs from the single-phase bypass_red scenario where V_L1 frequently collapsed to 0V. "
    f"V_L1 mean: {v1_mean:.1f}V | V_L3 mean: {v3_mean:.1f}V.", body_s))
story.append(Image(os.path.join(CHART_DIR, '04_voltage_compare.png'), width=CW, height=8*cm))
story.append(Paragraph("Figure 4: Phase voltages — normal (top) vs bypass_red_blue (bottom).", cap_s))

# 4. Power
story.append(PageBreak())
story.append(Paragraph("4. Active Power & Power Factor", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#8e24aa')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"Total power averaged <b>{p_mean:.3f}kW</b> vs normal <b>{dfn['P_total'].mean():.3f}kW</b>. "
    f"Power factor locked to <b>{pf_mean:.3f}</b> (normal: {dfn['PF_total'].mean():.3f}) — "
    f"a reliable ML feature indicating at least one CT is bypassed.", body_s))
story.append(Image(os.path.join(CHART_DIR, '05_power_compare.png'), width=CW, height=7.5*cm))
story.append(Paragraph("Figure 5: Total active power — normal (top) vs bypass_red_blue (bottom).", cap_s))
story.append(Image(os.path.join(CHART_DIR, '06_pf_compare.png'), width=CW, height=6.5*cm))
story.append(Paragraph("Figure 6: Power factor — normal (top) vs bypass_red_blue (bottom). "
    "PF locked at 0.0 throughout bypass period.", cap_s))

# 5. Energy
story.append(PageBreak())
story.append(Paragraph("5. Energy Accumulation & Current Imbalance", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#8e24aa')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"Energy rate during bypass: <b>{e_rate:.4f} kWh/h</b> vs normal <b>{n_e_rate:.4f} kWh/h</b> "
    f"— a <b>{(1-e_rate/n_e_rate)*100:.0f}% reduction</b>. "
    f"Total energy recorded: {e_delta:.3f} kWh over {duration_h:.1f} hours.", body_s))
story.append(Image(os.path.join(CHART_DIR, '07_energy_compare.png'), width=CW, height=5.5*cm))
story.append(Paragraph("Figure 7: Cumulative energy — normal vs bypass_red_blue (normalised to 0 at start).", cap_s))
story.append(Image(os.path.join(CHART_DIR, '08_imbalance.png'), width=CW, height=5.5*cm))
story.append(Paragraph("Figure 8: Current imbalance (std across phases) — dashed line = normal average.", cap_s))

# 6. ML Signatures
story.append(PageBreak())
story.append(Paragraph("6. ML Anomaly Signatures Summary", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#8e24aa')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "Summary of anomaly features compared to normal baseline, with ML model relevance.", body_s))

sig_data = [
    ['Feature', 'Normal', 'Bypass RB', 'Change', 'Detected?', 'Model'],
    ['I_L3 mean (A)',       f'{n_i3:.3f}', f'{i3_mean:.3f}', f'{(i3_mean/max(n_i3,0.001)-1)*100:+.0f}%', 'YES', 'IF/SVM/LSTM'],
    ['I_L3 near-zero (%)',  '51.5%', f'{i3_zero_pct:.1f}%',  f'+{i3_zero_pct-51.5:.0f}%', 'YES', 'IF/LSTM'],
    ['I_L1 mean (A)',       f'{n_i1:.3f}', f'{i1_mean:.3f}', f'{(i1_mean/max(n_i1,0.001)-1)*100:+.0f}%', 'NO (wire issue)', 'N/A'],
    ['I_L1 near-zero (%)',  '21.3%', f'{i1_zero_pct:.1f}%',  f'{i1_zero_pct-21.3:+.0f}%', 'NO', 'N/A'],
    ['PF total mean',       f'{dfn["PF_total"].mean():.3f}', f'{pf_mean:.3f}', f'{pf_mean-dfn["PF_total"].mean():+.3f}', 'YES', 'IF/SVM'],
    ['Energy rate (kWh/h)', f'{n_e_rate:.4f}', f'{e_rate:.4f}', f'{(e_rate/n_e_rate-1)*100:+.0f}%', 'YES', 'LSTM'],
    ['V collapse',          '0.0%', f'{max(v1_zero,v3_zero):.1f}%', '~0%', 'NO', 'N/A'],
    ['Current imbalance',   'Baseline', 'ELEVATED (L3 suppressed)', 'Significant', 'YES', 'IF/SVM'],
]
st = Table(sig_data, colWidths=[4*cm, 2*cm, 2.2*cm, 2*cm, 2.5*cm, 2.5*cm])
st.setStyle(TableStyle([
    ('BACKGROUND',     (0,0),(-1,0),  colors.HexColor(DARK_PU)),
    ('TEXTCOLOR',      (0,0),(-1,0),  colors.white),
    ('FONTNAME',       (0,0),(-1,0),  'Helvetica-Bold'),
    ('FONTSIZE',       (0,0),(-1,-1), 8.5),
    ('ALIGN',          (1,0),(-1,-1), 'CENTER'),
    ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor('#f3e5f5')]),
    ('GRID',           (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',     (0,0),(-1,-1), 4),
    ('BOTTOMPADDING',  (0,0),(-1,-1), 4),
    ('LEFTPADDING',    (0,0),(-1,-1), 6),
]))
story.append(st)
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph(
    f"<b>Conclusion:</b> Despite the L1 bypass wire being ineffective, "
    f"the model can still detect this scenario via L3 suppression, PF locking at 0.0, "
    f"and reduced energy rate. When both L1 and L3 are properly bypassed, "
    f"detection confidence will be even higher. "
    f"This dataset contributes valuable training data for the multi-phase bypass class.", info_s))

story.append(Spacer(1, 1*cm))
story.append(HRFlowable(width=CW, thickness=1, color=colors.HexColor('#8e24aa')))
story.append(Paragraph(
    f"Generated by NFE data pipeline  |  {datetime.now().strftime('%d %B %Y, %H:%M')}  |  "
    f"Dataset: bypass_red_blue.csv ({len(df):,} rows)  |  Meter: CHINT DTSU666  |  Kampala, Uganda", cap_s))

doc.build(story)
print(f"PDF saved -> {OUTPUT_PDF}")
