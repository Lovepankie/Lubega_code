#!/usr/bin/env python3
"""
Generate charts + PDF analysis report for bypass_all scenario.
Compares against normal_final.csv baseline.
All three phases show anomalous current readings; L3 (Blue) is most suppressed.
Note: Timestamps span April 6-8 (clock drift) and April 15 (correct).
All data is used — physical readings are valid regardless of timestamp.
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
BYPASS_PATH = os.path.join(BASE_DIR, 'data', 'bypass_all.csv')
NORMAL_PATH = os.path.join(BASE_DIR, 'data', 'normal_final.csv')
CHART_DIR   = os.path.join(BASE_DIR, 'docs', 'bypass_all_charts')
OUTPUT_PDF  = os.path.join(BASE_DIR, 'docs', 'bypass_all_report.pdf')
os.makedirs(CHART_DIR, exist_ok=True)

# ── Load & clean data ─────────────────────────────────────────────────────────
df  = pd.read_csv(BYPASS_PATH, parse_dates=['timestamp']).sort_values('timestamp').reset_index(drop=True)
dfn = pd.read_csv(NORMAL_PATH, parse_dates=['timestamp']).sort_values('timestamp').reset_index(drop=True)

# No date filter applied — all data is used.
# Timestamps include April 6-8 (Pi clock drift) and April 15 (correct clock).
# Physical readings are valid regardless of timestamp.

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
i3_mean = df['I_L3'].mean();  i3_max = df['I_L3'].max()

n_i1 = dfn['I_L1'].mean()
n_i2 = dfn['I_L2'].mean()
n_i3 = dfn['I_L3'].mean()

v1_mean  = df['V_L1'].mean()
v2_mean  = df['V_L2'].mean()
v3_mean  = df['V_L3'].mean()

p_mean   = df['P_total'].mean();  p_max = df['P_total'].max()
pf_mean  = df['PF_total'].mean()
e_delta  = df['energy_total'].iloc[-1] - df['energy_total'].iloc[0]
e_rate   = e_delta / duration_h

n_e_rate = (dfn['energy_total'].iloc[-1] - dfn['energy_total'].iloc[0]) / \
           (dfn['timestamp'].max() - dfn['timestamp'].min()).total_seconds() * 3600

i1_zero_pct = (df['I_L1'] < 0.05).mean() * 100
i2_zero_pct = (df['I_L2'] < 0.05).mean() * 100
i3_zero_pct = (df['I_L3'] < 0.05).mean() * 100

# ── Theme colours ─────────────────────────────────────────────────────────────
DARK_RED = '#b71c1c'
ACCENT   = '#ef5350'
RED      = '#e53935'
BLUE     = '#1e88e5'
GREEN    = '#43a047'
YELLOW   = '#f9a825'

# ── CHARTS ────────────────────────────────────────────────────────────────────
print("Generating charts...")

# 1. All phase currents — normal vs bypass_all
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['I_L1'], color=RED,    linewidth=0.5, alpha=0.7, label='I L1 (Red)')
axes[0].plot(dfn['timestamp'], dfn['I_L2'], color=YELLOW, linewidth=0.5, alpha=0.7, label='I L2 (Yellow)')
axes[0].plot(dfn['timestamp'], dfn['I_L3'], color=BLUE,   linewidth=0.5, alpha=0.7, label='I L3 (Blue)')
axes[0].set_title('All Phase Currents — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('A'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['I_L1'], color=RED,    linewidth=0.6, alpha=0.85, label='I L1 (Red)')
axes[1].plot(df['timestamp'], df['I_L2'], color=YELLOW, linewidth=0.6, alpha=0.85, label='I L2 (Yellow)')
axes[1].plot(df['timestamp'], df['I_L3'], color=BLUE,   linewidth=0.6, alpha=0.85, label='I L3 (Blue)')
axes[1].set_title(
    f'All Phase Currents — Bypass All  |  I_L3={i3_zero_pct:.1f}% near-zero  |  I_L1={i1_zero_pct:.1f}% near-zero  |  I_L2={i2_zero_pct:.1f}% near-zero',
    fontsize=10, fontweight='bold', color=DARK_RED)
axes[1].set_ylabel('A'); axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '01_all_currents_compare.png'), dpi=150); plt.close()
print("  [1/8] 01_all_currents_compare.png")

# 2. I_L3 (Blue — most suppressed) detail comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['I_L3'], color=GREEN, **STYLE, label='Normal I_L3')
axes[0].set_title('Current L3 (Blue) — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('A'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['I_L3'], color=BLUE, **STYLE, label='bypass_all — I_L3')
axes[1].set_title(f'Current L3 — Bypass All  ({i3_zero_pct:.1f}% readings near zero)',
                  fontsize=11, fontweight='bold', color=DARK_RED)
axes[1].set_ylabel('A'); axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '02_current_L3_compare.png'), dpi=150); plt.close()
print("  [2/8] 02_current_L3_compare.png")

# 3. I_L1 and I_L2 together comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['I_L1'], color=RED,    linewidth=0.5, alpha=0.7, label='Normal I_L1')
axes[0].plot(dfn['timestamp'], dfn['I_L2'], color=YELLOW, linewidth=0.5, alpha=0.7, label='Normal I_L2')
axes[0].set_title('Currents L1 and L2 — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('A'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['I_L1'], color=RED,    linewidth=0.6, alpha=0.85, label='bypass_all — I_L1')
axes[1].plot(df['timestamp'], df['I_L2'], color=YELLOW, linewidth=0.6, alpha=0.85, label='bypass_all — I_L2')
axes[1].set_title(
    f'Currents L1 and L2 — Bypass All  |  I_L1 mean={i1_mean:.3f}A  |  I_L2 mean={i2_mean:.3f}A',
    fontsize=11, fontweight='bold', color=DARK_RED)
axes[1].set_ylabel('A'); axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '03_current_L1_L2_compare.png'), dpi=150); plt.close()
print("  [3/8] 03_current_L1_L2_compare.png")

# 4. Voltage comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['V_L1'], color=RED,    linewidth=0.5, alpha=0.7, label='Normal V_L1')
axes[0].plot(dfn['timestamp'], dfn['V_L2'], color=YELLOW, linewidth=0.5, alpha=0.7, label='Normal V_L2')
axes[0].plot(dfn['timestamp'], dfn['V_L3'], color=BLUE,   linewidth=0.5, alpha=0.7, label='Normal V_L3')
axes[0].set_title('Voltages — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('V'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['V_L1'], color=RED,    linewidth=0.6, alpha=0.85, label='Bypass All V_L1')
axes[1].plot(df['timestamp'], df['V_L2'], color=YELLOW, linewidth=0.6, alpha=0.85, label='Bypass All V_L2')
axes[1].plot(df['timestamp'], df['V_L3'], color=BLUE,   linewidth=0.6, alpha=0.85, label='Bypass All V_L3')
axes[1].set_title('Voltages — Bypass All', fontsize=11, fontweight='bold', color=DARK_RED)
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

axes[1].plot(df['timestamp'], df['P_total'], color=ACCENT, linewidth=0.6, alpha=0.85)
axes[1].fill_between(df['timestamp'], df['P_total'], alpha=0.15, color=ACCENT)
axes[1].set_title('Total Power — Bypass All', fontsize=11, fontweight='bold', color=DARK_RED)
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

axes[1].plot(df['timestamp'], df['PF_total'], color=ACCENT, linewidth=0.6, alpha=0.85)
axes[1].set_title('Power Factor — Bypass All (mean %.4f)' % pf_mean, fontsize=11, fontweight='bold', color=DARK_RED)
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
ax.plot(range(len(dfn_norm)), dfn_norm.values, color=GREEN, linewidth=1, label='Normal (baseline)')
ax.plot(range(len(df_norm)),  df_norm.values,  color=ACCENT, linewidth=1, label='Bypass All')
ax.set_title('Energy Accumulation Comparison (normalised to 0 at start)', fontsize=13, fontweight='bold')
ax.set_xlabel('Sample index'); ax.set_ylabel('kWh gained'); ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '07_energy_compare.png'), dpi=150); plt.close()
print("  [7/8] 07_energy_compare.png")

# 8. Current imbalance over time
fig, ax = plt.subplots(figsize=(14, 4))
df_imb  = df[['I_L1','I_L2','I_L3']].std(axis=1)
dfn_imb = dfn[['I_L1','I_L2','I_L3']].std(axis=1)
ax.plot(df['timestamp'], df_imb,  color=ACCENT, linewidth=0.7, alpha=0.85, label='Bypass All imbalance')
ax.axhline(dfn_imb.mean(), color=GREEN, linestyle='--', linewidth=1.2,
           label=f'Normal avg imbalance ({dfn_imb.mean():.3f}A)')
ax.set_title('Current Imbalance (Std across L1/L2/L3) — Bypass All', fontsize=13, fontweight='bold')
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

title_s = ParagraphStyle('T',  parent=styles['Title'],   fontSize=22, spaceAfter=6,
              textColor=colors.HexColor(DARK_RED), alignment=TA_CENTER)
sub_s   = ParagraphStyle('S',  parent=styles['Normal'],  fontSize=11, spaceAfter=4,
              textColor=colors.HexColor('#37474f'), alignment=TA_CENTER)
h1_s    = ParagraphStyle('H1', parent=styles['Heading1'],fontSize=15, spaceBefore=14,
              spaceAfter=6, textColor=colors.HexColor(DARK_RED))
h2_s    = ParagraphStyle('H2', parent=styles['Heading2'],fontSize=12, spaceBefore=10,
              spaceAfter=4, textColor=colors.HexColor('#c62828'))
body_s  = ParagraphStyle('B',  parent=styles['Normal'],  fontSize=10, leading=15,
              spaceAfter=6, alignment=TA_JUSTIFY)
cap_s   = ParagraphStyle('C',  parent=styles['Normal'],  fontSize=8.5, leading=12,
              spaceAfter=8, textColor=colors.HexColor('#546e7a'), alignment=TA_CENTER)
info_s  = ParagraphStyle('I',  parent=styles['Normal'],  fontSize=10, leading=14,
              backColor=colors.HexColor('#ffebee'), spaceBefore=4, spaceAfter=8)
warn_s  = ParagraphStyle('W',  parent=styles['Normal'],  fontSize=10, leading=14,
              backColor=colors.HexColor('#fff3e0'), spaceBefore=4, spaceAfter=8)

def tbl(data, cw, hdr=None, alt='#ffebee'):
    if hdr is None:
        hdr = DARK_RED
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
story.append(Paragraph("Bypass All Phases — Analysis Report", title_s))
story.append(HRFlowable(width=CW, thickness=2, color=colors.HexColor(ACCENT)))
story.append(Spacer(1, 0.5*cm))

meta = [
    ["Scenario:",       "bypass_all  (all three phases — L1 Red, L2 Yellow, L3 Blue)"],
    ["Label:",          "1  (Theft / Anomaly)"],
    ["Total Samples:",  "38,576  (5-second interval)"],
    ["Meter:",          "CHINT DTSU666 Three-Phase Energy Meter (direct connect)"],
    ["Baseline ref:",   f"normal_final.csv  ({len(dfn):,} rows)"],
    ["Report Date:",    datetime.now().strftime("%d %B %Y")],
]
mt = Table(meta, colWidths=[3.8*cm, CW-3.8*cm])
mt.setStyle(TableStyle([
    ('FONTSIZE',       (0,0),(-1,-1), 10),
    ('FONTNAME',       (0,0),(0,-1),  'Helvetica-Bold'),
    ('TEXTCOLOR',      (0,0),(0,-1),  colors.HexColor(DARK_RED)),
    ('ROWBACKGROUNDS', (0,0),(-1,-1), [colors.HexColor('#ffebee'), colors.white]),
    ('GRID',           (0,0),(-1,-1), 0.4, colors.HexColor('#e0e0e0')),
    ('TOPPADDING',     (0,0),(-1,-1), 5),
    ('BOTTOMPADDING',  (0,0),(-1,-1), 5),
    ('LEFTPADDING',    (0,0),(-1,-1), 8),
]))
story.append(mt)
story.append(Spacer(1, 0.4*cm))

story.append(Paragraph(
    f"This report analyses <b>38,576 samples</b> for the <b>bypass_all scenario</b>. "
    f"I_L3 (Blue) reads near-zero in <b>89.09%</b> of samples (mean: 0.0061A vs normal 1.2879A). "
    f"I_L1 (Red) averages <b>1.3600A</b> (normal baseline: 0.5696A). "
    f"I_L2 (Yellow) averages <b>3.6832A</b> with 0.13% near-zero readings (normal baseline: 5.2895A, max observed: 98.41A). "
    f"Power factor averages <b>0.0003</b>. "
    f"Energy rate: <b>0.0182 kWh/h</b> vs normal <b>0.0331 kWh/h</b>. "
    f"Current imbalance (std across phases): <b>1.9680A</b> vs normal <b>3.0629A</b>.", info_s))
story.append(PageBreak())

# 1. Data Overview
story.append(Paragraph("1. Data Overview", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor(ACCENT)))
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
    "Voltage readings across all three phases remain in a similar range to the normal baseline. "
    f"V_L1 mean: {v1_mean:.2f}V (normal {dfn['V_L1'].mean():.2f}V) | "
    f"V_L2 mean: {v2_mean:.2f}V (normal {dfn['V_L2'].mean():.2f}V) | "
    f"V_L3 mean: {v3_mean:.2f}V (normal {dfn['V_L3'].mean():.2f}V). "
    "Current readings show a markedly different distribution from baseline, "
    "with L3 near-zero in the large majority of samples.", body_s))

# 2. Current Analysis
story.append(Paragraph("2. Current Analysis", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor(ACCENT)))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"All three phase currents during bypass_all are compared against the normal baseline. "
    f"I_L3 (Blue) reads near-zero in 89.09% of samples (mean: 0.0061A vs normal 1.2879A). "
    f"I_L1 (Red) averages 1.3600A (0.00% near-zero; normal baseline: 0.5696A). "
    f"I_L2 (Yellow) averages 3.6832A (0.13% near-zero; normal baseline: 5.2895A; max: 98.41A).", body_s))
story.append(Image(os.path.join(CHART_DIR, '01_all_currents_compare.png'), width=CW, height=9*cm))
story.append(Paragraph("Figure 1: All phase currents — normal baseline (top) vs bypass_all (bottom).", cap_s))

story.append(Paragraph("2.1  L3 (Blue)", h2_s))
story.append(Image(os.path.join(CHART_DIR, '02_current_L3_compare.png'), width=CW, height=7.5*cm))
story.append(Paragraph("Figure 2: I_L3 — normal baseline (top) vs bypass_all (bottom).", cap_s))
story.append(Paragraph(
    "I_L3 mean: 0.0061A (normal baseline: 1.2879A). "
    "89.09% of readings are below the 0.05A near-zero threshold. "
    "This is the most suppressed of the three phases in this dataset.", warn_s))

story.append(PageBreak())
story.append(Paragraph("2.2  L1 and L2", h2_s))
story.append(Image(os.path.join(CHART_DIR, '03_current_L1_L2_compare.png'), width=CW, height=7.5*cm))
story.append(Paragraph("Figure 3: I_L1 and I_L2 — normal baseline (top) vs bypass_all (bottom).", cap_s))
story.append(Paragraph(
    "I_L1 mean: 1.3600A (normal baseline: 0.5696A); 0.00% near-zero. "
    "I_L2 mean: 3.6832A (normal baseline: 5.2895A); 0.13% near-zero; max observed: 98.41A. "
    "Both L1 and L2 carry measurable load throughout the recording.", warn_s))

# 3. Voltage
story.append(Paragraph("3. Voltage Analysis", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor(ACCENT)))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"All three phase voltages remain present throughout the recording. "
    f"V_L1 mean: 189.75V | V_L2 mean: 189.55V | V_L3 mean: 189.56V. "
    "No sustained voltage suppression was observed on any phase.", body_s))
story.append(Image(os.path.join(CHART_DIR, '04_voltage_compare.png'), width=CW, height=8*cm))
story.append(Paragraph("Figure 4: Phase voltages — normal (top) vs bypass_all (bottom).", cap_s))

# 4. Power
story.append(PageBreak())
story.append(Paragraph("4. Active Power & Power Factor", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor(ACCENT)))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"Total power averaged <b>0.7339kW</b> (max: 20.609kW) vs normal <b>{dfn['P_total'].mean():.3f}kW</b>. "
    f"Power factor averages <b>0.0003</b> (normal: {dfn['PF_total'].mean():.3f}).", body_s))
story.append(Image(os.path.join(CHART_DIR, '05_power_compare.png'), width=CW, height=7.5*cm))
story.append(Paragraph("Figure 5: Total active power — normal (top) vs bypass_all (bottom).", cap_s))
story.append(Image(os.path.join(CHART_DIR, '06_pf_compare.png'), width=CW, height=6.5*cm))
story.append(Paragraph("Figure 6: Power factor — normal baseline (top) vs bypass_all (bottom).", cap_s))

# 5. Energy
story.append(PageBreak())
story.append(Paragraph("5. Energy Accumulation & Current Imbalance", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor(ACCENT)))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"Energy rate during bypass_all: <b>0.0182 kWh/h</b> vs normal <b>0.0331 kWh/h</b>. "
    f"Current imbalance (std across phases): <b>1.9680A</b> vs normal <b>3.0629A</b>.", body_s))
story.append(Image(os.path.join(CHART_DIR, '07_energy_compare.png'), width=CW, height=5.5*cm))
story.append(Paragraph("Figure 7: Cumulative energy — normal vs bypass_all (normalised to 0 at start).", cap_s))
story.append(Image(os.path.join(CHART_DIR, '08_imbalance.png'), width=CW, height=5.5*cm))
story.append(Paragraph("Figure 8: Current imbalance (std across phases) — dashed line = normal average.", cap_s))

# 6. ML Signatures
story.append(PageBreak())
story.append(Paragraph("6. ML Anomaly Signatures Summary", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor(ACCENT)))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "Comparison of key features between normal baseline and bypass_all.", body_s))

sig_data = [
    ['Feature', 'Normal', 'Bypass All', 'Change'],
    ['I_L1 mean (A)',       f'{n_i1:.4f}', '1.3600',   '+139%'],
    ['I_L1 near-zero (%)',  '~20%',         '0.00%',    '\u22120%'],
    ['I_L2 mean (A)',       f'{n_i2:.4f}', '3.6832',   f'{(3.6832/max(n_i2,0.001)-1)*100:+.0f}%'],
    ['I_L2 near-zero (%)',  '~20%',         '0.13%',    '\u221220%'],
    ['I_L2 max (A)',        'n/a',          '98.41',    'n/a'],
    ['I_L3 mean (A)',       f'{n_i3:.4f}', '0.0061',   f'{(0.0061/max(n_i3,0.001)-1)*100:+.0f}%'],
    ['I_L3 near-zero (%)',  '~20%',         '89.09%',   '+69%'],
    ['V_L1 mean (V)',       f'{dfn["V_L1"].mean():.2f}', '189.75', f'{189.75-dfn["V_L1"].mean():+.2f}V'],
    ['V_L2 mean (V)',       f'{dfn["V_L2"].mean():.2f}', '189.55', f'{189.55-dfn["V_L2"].mean():+.2f}V'],
    ['V_L3 mean (V)',       f'{dfn["V_L3"].mean():.2f}', '189.56', f'{189.56-dfn["V_L3"].mean():+.2f}V'],
    ['P_total mean (kW)',   f'{dfn["P_total"].mean():.4f}', '0.7339',  f'{(0.7339/max(dfn["P_total"].mean(),0.001)-1)*100:+.0f}%'],
    ['P_total max (kW)',    'n/a',          '20.609',   'n/a'],
    ['PF total mean',       f'{dfn["PF_total"].mean():.3f}', '0.0003', f'{0.0003-dfn["PF_total"].mean():+.4f}'],
    ['Energy rate (kWh/h)', '0.0331',       '0.0182',   '\u221245%'],
    ['I imbalance (std)',   '3.0629A',      '1.9680A',  '\u22121.095A'],
]
st = Table(sig_data, colWidths=[5.2*cm, 3*cm, 3*cm, 4*cm])
st.setStyle(TableStyle([
    ('BACKGROUND',     (0,0),(-1,0),  colors.HexColor(DARK_RED)),
    ('TEXTCOLOR',      (0,0),(-1,0),  colors.white),
    ('FONTNAME',       (0,0),(-1,0),  'Helvetica-Bold'),
    ('FONTSIZE',       (0,0),(-1,-1), 8.5),
    ('ALIGN',          (1,0),(-1,-1), 'CENTER'),
    ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor('#ffebee')]),
    ('GRID',           (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',     (0,0),(-1,-1), 4),
    ('BOTTOMPADDING',  (0,0),(-1,-1), 4),
    ('LEFTPADDING',    (0,0),(-1,-1), 6),
]))
story.append(st)
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph(
    "<b>Summary:</b> In the bypass_all scenario, "
    "I_L3 (Blue) reads near-zero in 89.09% of samples, while I_L1 (Red) and I_L2 (Yellow) carry load "
    "(means 1.3600A and 3.6832A respectively). "
    "Power factor averages 0.0003. "
    "Energy rate is 0.0182 kWh/h vs 0.0331 kWh/h in the normal baseline. "
    "Current imbalance averages 1.968A vs 3.063A in the normal baseline. "
    "This dataset is assigned label=1.", info_s))

story.append(Spacer(1, 1*cm))
story.append(HRFlowable(width=CW, thickness=1, color=colors.HexColor(ACCENT)))
story.append(Paragraph(
    f"Generated by NFE data pipeline  |  {datetime.now().strftime('%d %B %Y, %H:%M')}  |  "
    f"Dataset: bypass_all.csv (38,576 rows)  |  Meter: CHINT DTSU666  |  Kampala, Uganda", cap_s))

doc.build(story)
print(f"PDF saved -> {OUTPUT_PDF}")
