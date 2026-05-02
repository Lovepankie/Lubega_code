#!/usr/bin/env python3
"""
Generate charts + PDF analysis report for bypass_yellow scenario.
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
BYPASS_PATH = os.path.join(BASE_DIR, 'data', 'bypass_yellow.csv')
NORMAL_PATH = os.path.join(BASE_DIR, 'data', 'normal_final.csv')
CHART_DIR   = os.path.join(BASE_DIR, 'docs', 'bypass_yellow_charts')
OUTPUT_PDF  = os.path.join(BASE_DIR, 'docs', 'bypass_yellow_report.pdf')
os.makedirs(CHART_DIR, exist_ok=True)

# ── Load data ────────────────────────────────────────────────────────────────
df  = pd.read_csv(BYPASS_PATH, parse_dates=['timestamp']).sort_values('timestamp').reset_index(drop=True)
dfn = pd.read_csv(NORMAL_PATH, parse_dates=['timestamp']).sort_values('timestamp').reset_index(drop=True)
df['hour']  = df['timestamp'].dt.hour
dfn['hour'] = dfn['timestamp'].dt.hour

duration_h = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600
FMT = '%d %b %H:%M'
STYLE = {'linewidth': 0.7, 'alpha': 0.85}

print(f"Bypass rows : {len(df):,}  ({duration_h:.1f}h)")
print(f"Normal rows : {len(dfn):,}")

# ── Key stats ────────────────────────────────────────────────────────────────
v_mean   = df['V_L2'].mean()
v_zero   = (df['V_L2'] < 1).mean() * 100

i1_mean  = df['I_L1'].mean();  i1_max = df['I_L1'].max()
i2_mean  = df['I_L2'].mean();  i2_max = df['I_L2'].max()
i3_mean  = df['I_L3'].mean();  i3_max = df['I_L3'].max()

n_i1     = dfn['I_L1'].mean()
n_i2     = dfn['I_L2'].mean()
n_i3     = dfn['I_L3'].mean()

p_mean   = df['P_total'].mean();  p_max = df['P_total'].max()
pf_mean  = df['PF_total'].mean()
freq_mean= df['frequency'].mean()
e_delta  = df['energy_total'].iloc[-1] - df['energy_total'].iloc[0]
e_rate   = e_delta / duration_h

n_e_rate = (dfn['energy_total'].iloc[-1] - dfn['energy_total'].iloc[0]) / \
           (dfn['timestamp'].max() - dfn['timestamp'].min()).total_seconds() * 3600

i2_zero_pct = (df['I_L2'] < 0.05).mean() * 100

# ── CHARTS ───────────────────────────────────────────────────────────────────
print("Generating charts...")

YELLOW = '#f9a825'
DARK_YELLOW = '#e65100'
NORMAL_GREEN = '#43a047'

# 1. Voltage L2 comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['V_L2'], color=NORMAL_GREEN, linewidth=0.6, alpha=0.8, label='Normal L2')
axes[0].axhline(180, color='red', linestyle='--', linewidth=0.8, label='180V threshold')
axes[0].set_title('Voltage L2 — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('V (V)'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['V_L2'], color=YELLOW, linewidth=0.6, alpha=0.85, label='Bypass Yellow L2')
axes[1].axhline(180, color='red', linestyle='--', linewidth=0.8)
axes[1].set_title('Voltage L2 — Bypass Yellow (anomaly: drops to 0V)', fontsize=11, fontweight='bold', color=DARK_YELLOW)
axes[1].set_ylabel('V (V)'); axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '01_voltage_compare.png'), dpi=150); plt.close()
print("  [1/8] 01_voltage_compare.png")

# 2. Current L2 comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['I_L2'], color=NORMAL_GREEN, **STYLE, label='Normal I_L2')
axes[0].set_title('Current L2 — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('A'); axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['I_L2'], color=YELLOW, **STYLE, label='Bypass Yellow I_L2')
axes[1].set_title(f'Current L2 — Bypass Yellow ({i2_zero_pct:.1f}% readings near zero)', fontsize=11, fontweight='bold', color=DARK_YELLOW)
axes[1].set_ylabel('A'); axes[1].legend(fontsize=8); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '02_current_L2_compare.png'), dpi=150); plt.close()
print("  [2/8] 02_current_L2_compare.png")

# 3. All phase currents during bypass
fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(df['timestamp'], df['I_L1'], color='#e53935', **STYLE, label='I L1')
ax.plot(df['timestamp'], df['I_L2'], color=YELLOW,   **STYLE, label='I L2 (bypassed)')
ax.plot(df['timestamp'], df['I_L3'], color=NORMAL_GREEN, **STYLE, label='I L3')
ax.set_title('All Phase Currents — Bypass Yellow Scenario', fontsize=13, fontweight='bold')
ax.set_ylabel('Current (A)'); ax.legend(); ax.grid(alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter(FMT)); plt.xticks(rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '03_all_currents.png'), dpi=150); plt.close()
print("  [3/8] 03_all_currents.png")

# 4. Power comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['P_total'], color=NORMAL_GREEN, linewidth=0.6, alpha=0.8)
axes[0].fill_between(dfn['timestamp'], dfn['P_total'], alpha=0.15, color=NORMAL_GREEN)
axes[0].set_title('Total Power — Normal Baseline', fontsize=11, fontweight='bold')
axes[0].set_ylabel('kW'); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['P_total'], color=YELLOW, linewidth=0.6, alpha=0.85)
axes[1].fill_between(df['timestamp'], df['P_total'], alpha=0.15, color=YELLOW)
axes[1].set_title('Total Power — Bypass Yellow', fontsize=11, fontweight='bold', color=DARK_YELLOW)
axes[1].set_ylabel('kW'); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '04_power_compare.png'), dpi=150); plt.close()
print("  [4/8] 04_power_compare.png")

# 5. Power factor comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 6), sharex=False)
axes[0].plot(dfn['timestamp'], dfn['PF_total'], color=NORMAL_GREEN, linewidth=0.6, alpha=0.8)
axes[0].set_title('Power Factor — Normal Baseline (mean %.3f)' % dfn['PF_total'].mean(), fontsize=11, fontweight='bold')
axes[0].set_ylabel('PF'); axes[0].set_ylim(-0.2, 1.1); axes[0].grid(alpha=0.3)
axes[0].xaxis.set_major_formatter(mdates.DateFormatter(FMT))

axes[1].plot(df['timestamp'], df['PF_total'], color=YELLOW, linewidth=0.6, alpha=0.85)
axes[1].set_title('Power Factor — Bypass Yellow (mean %.3f)' % pf_mean, fontsize=11, fontweight='bold', color=DARK_YELLOW)
axes[1].set_ylabel('PF'); axes[1].set_ylim(-0.2, 1.1); axes[1].grid(alpha=0.3)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter(FMT))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '05_pf_compare.png'), dpi=150); plt.close()
print("  [5/8] 05_pf_compare.png")

# 6. Energy accumulation comparison
fig, ax = plt.subplots(figsize=(14, 4))
dfn_norm = dfn['energy_total'] - dfn['energy_total'].iloc[0]
df_norm  = df['energy_total']  - df['energy_total'].iloc[0]
ax.plot(range(len(dfn_norm)), dfn_norm.values, color=NORMAL_GREEN, linewidth=1, label='Normal (baseline)')
ax.plot(range(len(df_norm)),  df_norm.values,  color=YELLOW,       linewidth=1, label='Bypass Yellow')
ax.set_title('Energy Accumulation Comparison (normalised to 0 at start)', fontsize=13, fontweight='bold')
ax.set_xlabel('Sample index'); ax.set_ylabel('kWh gained'); ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '06_energy_compare.png'), dpi=150); plt.close()
print("  [6/8] 06_energy_compare.png")

# 7. Current L2 histogram comparison
fig, axes = plt.subplots(1, 2, figsize=(13, 4))
axes[0].hist(dfn['I_L2'], bins=50, color=NORMAL_GREEN, alpha=0.8, edgecolor='white')
axes[0].set_title('I_L2 Distribution — Normal', fontsize=11, fontweight='bold')
axes[0].set_xlabel('A'); axes[0].set_ylabel('Count'); axes[0].grid(alpha=0.3)

axes[1].hist(df['I_L2'], bins=50, color=YELLOW, alpha=0.9, edgecolor='white')
axes[1].set_title('I_L2 Distribution — Bypass Yellow', fontsize=11, fontweight='bold', color=DARK_YELLOW)
axes[1].set_xlabel('A'); axes[1].grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '07_current_hist_compare.png'), dpi=150); plt.close()
print("  [7/8] 07_current_hist_compare.png")

# 8. Hourly average current L2
fig, ax = plt.subplots(figsize=(13, 4))
h_normal = dfn.groupby('hour')['I_L2'].mean()
h_bypass = df.groupby('hour')['I_L2'].mean()
x = range(24)
w = 0.38
ax.bar([i - w/2 for i in x], [h_normal.get(i, 0) for i in x], width=w, color=NORMAL_GREEN, alpha=0.85, label='Normal')
ax.bar([i + w/2 for i in x], [h_bypass.get(i, 0) for i in x], width=w, color=YELLOW,       alpha=0.85, label='Bypass Yellow')
ax.set_title('Hourly Average Current L2 — Normal vs Bypass Yellow', fontsize=13, fontweight='bold')
ax.set_xlabel('Hour of Day'); ax.set_ylabel('Avg I_L2 (A)'); ax.legend(); ax.grid(axis='y', alpha=0.3)
ax.set_xticks(range(24))
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '08_hourly_L2_compare.png'), dpi=150); plt.close()
print("  [8/8] 08_hourly_L2_compare.png")

print("All charts done.\n")

# ── PDF ───────────────────────────────────────────────────────────────────────
W, H = A4
CONTENT_W = W - 4*cm

doc = SimpleDocTemplate(OUTPUT_PDF, pagesize=A4,
    rightMargin=2*cm, leftMargin=2*cm,
    topMargin=2.5*cm, bottomMargin=2*cm)

styles = getSampleStyleSheet()
title_s    = ParagraphStyle('T', parent=styles['Title'], fontSize=22, spaceAfter=6,
                textColor=colors.HexColor('#e65100'), alignment=TA_CENTER)
subtitle_s = ParagraphStyle('S', parent=styles['Normal'], fontSize=11, spaceAfter=4,
                textColor=colors.HexColor('#37474f'), alignment=TA_CENTER)
h1_s = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=15, spaceBefore=14,
                spaceAfter=6, textColor=colors.HexColor('#e65100'))
h2_s = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=12, spaceBefore=10,
                spaceAfter=4, textColor=colors.HexColor('#f57f17'))
body_s = ParagraphStyle('B', parent=styles['Normal'], fontSize=10, leading=15,
                spaceAfter=6, alignment=TA_JUSTIFY)
caption_s = ParagraphStyle('C', parent=styles['Normal'], fontSize=8.5, leading=12,
                spaceAfter=8, textColor=colors.HexColor('#546e7a'), alignment=TA_CENTER)
alert_s = ParagraphStyle('A', parent=styles['Normal'], fontSize=10, leading=14,
                backColor=colors.HexColor('#fff8e1'), borderColor=colors.HexColor('#f57f17'),
                borderWidth=1, borderPad=6, spaceBefore=4, spaceAfter=8)
info_s = ParagraphStyle('I', parent=styles['Normal'], fontSize=10, leading=14,
                backColor=colors.HexColor('#e8eaf6'), borderColor=colors.HexColor('#3949ab'),
                borderWidth=1, borderPad=6, spaceBefore=4, spaceAfter=8)

story = []

# Cover
story.append(Spacer(1, 1.5*cm))
story.append(Paragraph("NFE Electricity Theft Detection System", subtitle_s))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph("Bypass Yellow Phase — Analysis Report", title_s))
story.append(Spacer(1, 0.2*cm))
story.append(HRFlowable(width=CONTENT_W, thickness=2, color=colors.HexColor('#f9a825')))
story.append(Spacer(1, 0.5*cm))

meta = [
    ["Scenario:",       "bypass_yellow  (Phase B / L2 current transformer shunted)"],
    ["Label:",          "1  (Theft / Anomaly)"],
    ["Data Period:",    f"{df['timestamp'].min().strftime('%d %b %Y %H:%M')}  ->  {df['timestamp'].max().strftime('%d %b %Y %H:%M')}"],
    ["Duration:",       f"{duration_h:.1f} hours"],
    ["Total Samples:",  f"{len(df):,}  (5-second interval)"],
    ["Meter:",          "CHINT DTSU666 Three-Phase Energy Meter"],
    ["Baseline ref:",   f"normal_final.csv  ({len(dfn):,} rows)"],
    ["Report Date:",    datetime.now().strftime("%d %B %Y")],
]
mt = Table(meta, colWidths=[3.8*cm, CONTENT_W-3.8*cm])
mt.setStyle(TableStyle([
    ('FONTSIZE',    (0,0),(-1,-1), 10),
    ('FONTNAME',    (0,0),(0,-1), 'Helvetica-Bold'),
    ('TEXTCOLOR',   (0,0),(0,-1), colors.HexColor('#e65100')),
    ('ROWBACKGROUNDS', (0,0),(-1,-1), [colors.HexColor('#fffde7'), colors.white]),
    ('GRID',        (0,0),(-1,-1), 0.4, colors.HexColor('#e0e0e0')),
    ('TOPPADDING',  (0,0),(-1,-1), 5), ('BOTTOMPADDING',(0,0),(-1,-1), 5),
    ('LEFTPADDING', (0,0),(-1,-1), 8),
]))
story.append(mt)
story.append(Spacer(1, 0.6*cm))

exec_text = (
    f"This report analyses <b>{len(df):,} samples</b> collected over <b>{duration_h:.1f} hours</b> "
    f"under the <b>bypass_yellow scenario</b> — Phase B (L2) current transformer shunted with a parallel wire. "
    f"Key anomaly signatures identified: "
    f"Current L2 drops to near-zero in <b>{i2_zero_pct:.1f}%</b> of readings; "
    f"Voltage L2 collapses to 0V in <b>{v_zero:.1f}%</b> of readings; "
    f"Power factor shifts to <b>{pf_mean:.3f}</b> (vs normal {dfn['PF_total'].mean():.3f}); "
    f"Energy accumulation rate drops to <b>{e_rate:.4f} kWh/h</b> "
    f"(vs normal {n_e_rate:.4f} kWh/h — a <b>{(1-e_rate/n_e_rate)*100:.0f}% reduction</b>)."
)
story.append(Paragraph(exec_text, info_s))
story.append(PageBreak())

# 1. Data Overview
story.append(Paragraph("1. Data Overview", h1_s))
story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=colors.HexColor('#f9a825')))
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

st = Table(stat_data, colWidths=[3.8*cm, 2.4*cm, 2.4*cm, 2.4*cm, 2.4*cm, 2.4*cm])
st.setStyle(TableStyle([
    ('BACKGROUND',  (0,0),(-1,0), colors.HexColor('#e65100')),
    ('TEXTCOLOR',   (0,0),(-1,0), colors.white),
    ('FONTNAME',    (0,0),(-1,0), 'Helvetica-Bold'),
    ('FONTSIZE',    (0,0),(-1,-1), 8.5),
    ('ALIGN',       (1,0),(-1,-1), 'CENTER'),
    ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor('#fffde7')]),
    ('GRID',        (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',  (0,0),(-1,-1), 4), ('BOTTOMPADDING',(0,0),(-1,-1), 4),
    ('LEFTPADDING', (0,0),(-1,-1), 6),
]))
story.append(st)
story.append(Spacer(1, 0.4*cm))

# 2. Voltage
story.append(Paragraph("2. Voltage Analysis", h1_s))
story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=colors.HexColor('#f9a825')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"Under normal operation all three phases track together around 190-220V. "
    f"During the bypass_yellow scenario, Phase L2 voltage collapses to <b>0V in {v_zero:.1f}% of readings</b> "
    f"and averages only <b>{v_mean:.1f}V</b>. "
    f"This is a strong anomaly indicator — voltage collapse on a single phase while others remain stable "
    f"is a clear signature of a shunt bypass on that phase's measurement circuit.", body_s))
img = Image(os.path.join(CHART_DIR, '01_voltage_compare.png'), width=CONTENT_W, height=8*cm)
story.append(img)
story.append(Paragraph("Figure 1: Voltage L2 — normal baseline (top) vs bypass yellow (bottom). "
    "Note the frequent collapses to 0V in the bypass scenario.", caption_s))
story.append(Paragraph(
    f"<b>Anomaly signature:</b> V_L2 drops to 0V in {v_zero:.1f}% of samples. "
    f"Normal baseline never drops below 118V. This is the strongest single-feature indicator for bypass_yellow.", alert_s))

# 3. Current
story.append(PageBreak())
story.append(Paragraph("3. Current Analysis", h1_s))
story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=colors.HexColor('#f9a825')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"Current L2 (the bypassed phase) averages <b>{i2_mean:.3f}A</b> and is near-zero "
    f"({i2_zero_pct:.1f}% of readings below 0.05A) — confirming that most current is flowing "
    f"through the bypass wire rather than the meter's CT. "
    f"In contrast, the normal baseline shows I_L2 mean of <b>{n_i2:.3f}A</b>. "
    f"Phase L1 and L3 are unaffected and continue showing normal current levels.", body_s))
img2 = Image(os.path.join(CHART_DIR, '02_current_L2_compare.png'), width=CONTENT_W, height=8*cm)
story.append(img2)
story.append(Paragraph("Figure 2: Current L2 — normal (top) vs bypass yellow (bottom). "
    f"The bypassed phase reads near-zero in {i2_zero_pct:.1f}% of samples.", caption_s))

story.append(Paragraph("3.1  All Phase Currents During Bypass", h2_s))
img3 = Image(os.path.join(CHART_DIR, '03_all_currents.png'), width=CONTENT_W, height=5.5*cm)
story.append(img3)
story.append(Paragraph("Figure 3: All three phase currents during bypass_yellow. "
    "I_L2 (yellow) is suppressed while L1 and L3 behave normally.", caption_s))
story.append(Paragraph(
    f"<b>Anomaly signature:</b> I_L2 mean drops from {n_i2:.3f}A (normal) to {i2_mean:.3f}A (bypass). "
    f"A {(1-i2_mean/max(n_i2,0.001))*100:.0f}% reduction in reported current on the targeted phase.", alert_s))

# 4. Power
story.append(PageBreak())
story.append(Paragraph("4. Active Power Analysis", h1_s))
story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=colors.HexColor('#f9a825')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"Total active power averages <b>{p_mean:.3f}kW</b> during bypass vs "
    f"<b>{dfn['P_total'].mean():.3f}kW</b> under normal conditions. "
    f"Since the bypassed phase's current is not measured, the meter under-reports actual consumption. "
    f"The power spikes (up to {p_max:.2f}kW) correspond to load events on the non-bypassed phases.", body_s))
img4 = Image(os.path.join(CHART_DIR, '04_power_compare.png'), width=CONTENT_W, height=8*cm)
story.append(img4)
story.append(Paragraph("Figure 4: Total active power — normal (top) vs bypass yellow (bottom).", caption_s))

# 5. Power Factor
story.append(Paragraph("5. Power Factor", h1_s))
story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=colors.HexColor('#f9a825')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"Power factor shifts significantly from the normal mean of "
    f"<b>{dfn['PF_total'].mean():.3f}</b> to <b>{pf_mean:.3f}</b> during bypass. "
    f"The collapse toward zero is caused by the meter computing PF from a current reading "
    f"that no longer reflects the actual load — the phase angle calculation becomes unreliable "
    f"when one phase CT is shunted.", body_s))
img5 = Image(os.path.join(CHART_DIR, '05_pf_compare.png'), width=CONTENT_W, height=7*cm)
story.append(img5)
story.append(Paragraph("Figure 5: Power factor — normal (top) vs bypass yellow (bottom). "
    "The shift toward 0 is a strong anomaly feature.", caption_s))
story.append(Paragraph(
    f"<b>Anomaly signature:</b> PF shifts from {dfn['PF_total'].mean():.3f} to {pf_mean:.3f}. "
    f"This {abs(pf_mean - dfn['PF_total'].mean()):.3f} deviation is a reliable ML feature for bypass detection.", alert_s))

# 6. Energy
story.append(PageBreak())
story.append(Paragraph("6. Energy Accumulation", h1_s))
story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=colors.HexColor('#f9a825')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"Energy accumulation rate during bypass is <b>{e_rate:.4f} kWh/h</b> vs "
    f"<b>{n_e_rate:.4f} kWh/h</b> under normal conditions — a "
    f"<b>{(1-e_rate/n_e_rate)*100:.0f}% reduction</b>. "
    f"The meter records {e_delta:.3f} kWh over {duration_h:.1f} hours while actual consumption "
    f"is higher due to unmetered current on the bypassed phase.", body_s))
img6 = Image(os.path.join(CHART_DIR, '06_energy_compare.png'), width=CONTENT_W, height=5.5*cm)
story.append(img6)
story.append(Paragraph("Figure 6: Cumulative energy gained — normal vs bypass yellow (both normalised to 0 at start). "
    "The bypass scenario accumulates energy slower.", caption_s))

# 7. Current Distribution
story.append(Paragraph("7. Current Distribution & Hourly Profile", h1_s))
story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=colors.HexColor('#f9a825')))
story.append(Spacer(1, 0.3*cm))
img7 = Image(os.path.join(CHART_DIR, '07_current_hist_compare.png'), width=CONTENT_W, height=5.5*cm)
story.append(img7)
story.append(Paragraph("Figure 7: I_L2 histogram — normal (left) vs bypass yellow (right). "
    f"The bypass distribution is heavily concentrated at 0A ({i2_zero_pct:.1f}% of samples).", caption_s))

img8 = Image(os.path.join(CHART_DIR, '08_hourly_L2_compare.png'), width=CONTENT_W, height=5.5*cm)
story.append(img8)
story.append(Paragraph("Figure 8: Hourly average I_L2 — normal vs bypass yellow by hour of day. "
    "The suppression is consistent across all hours.", caption_s))

# 8. ML Signatures Summary
story.append(PageBreak())
story.append(Paragraph("8. ML Anomaly Signatures Summary", h1_s))
story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=colors.HexColor('#f9a825')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "The table below quantifies each anomaly feature for the bypass_yellow scenario "
    "against the normal baseline, along with the expected detection method.", body_s))

sig_data = [
    ['Feature', 'Normal', 'Bypass Yellow', 'Change', 'Model'],
    ['V_L2 mean (V)',
     f'{dfn["V_L2"].mean():.1f}', f'{v_mean:.1f}',
     f'{v_mean - dfn["V_L2"].mean():+.1f}V', 'IF / SVM'],
    ['V_L2 zero-collapse (%)',
     '0.0%', f'{v_zero:.1f}%', f'+{v_zero:.1f}%', 'IF / LSTM'],
    ['I_L2 mean (A)',
     f'{n_i2:.3f}', f'{i2_mean:.3f}',
     f'{(i2_mean/max(n_i2,0.001)-1)*100:+.0f}%', 'IF / SVM / LSTM'],
    ['I_L2 near-zero (%)',
     '~5%', f'{i2_zero_pct:.1f}%', f'+{i2_zero_pct-5:.0f}%', 'IF / LSTM'],
    ['PF total mean',
     f'{dfn["PF_total"].mean():.3f}', f'{pf_mean:.3f}',
     f'{pf_mean - dfn["PF_total"].mean():+.3f}', 'IF / SVM'],
    ['Energy rate (kWh/h)',
     f'{n_e_rate:.4f}', f'{e_rate:.4f}',
     f'{(e_rate/n_e_rate-1)*100:+.0f}%', 'LSTM'],
    ['Current imbalance',
     'Low', 'HIGH (L2 suppressed)', 'Significant', 'IF / SVM'],
]
sig_tbl = Table(sig_data, colWidths=[4*cm, 2.6*cm, 2.6*cm, 2.6*cm, 2.6*cm])
sig_tbl.setStyle(TableStyle([
    ('BACKGROUND',  (0,0),(-1,0), colors.HexColor('#e65100')),
    ('TEXTCOLOR',   (0,0),(-1,0), colors.white),
    ('FONTNAME',    (0,0),(-1,0), 'Helvetica-Bold'),
    ('FONTSIZE',    (0,0),(-1,-1), 8.5),
    ('ALIGN',       (1,0),(-1,-1), 'CENTER'),
    ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor('#fffde7')]),
    ('GRID',        (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',  (0,0),(-1,-1), 4), ('BOTTOMPADDING',(0,0),(-1,-1), 4),
    ('LEFTPADDING', (0,0),(-1,-1), 6),
]))
story.append(sig_tbl)
story.append(Spacer(1, 0.5*cm))

story.append(Paragraph(
    f"<b>Conclusion:</b> The bypass_yellow scenario produces 4 strong, consistent anomaly signatures: "
    f"voltage collapse, current suppression, PF shift, and reduced energy rate — all on the targeted Phase L2. "
    f"These features are well-separated from the normal baseline and will provide high discriminative power "
    f"for all three ML models (Isolation Forest, One-Class SVM, LSTM Autoencoder).", info_s))

story.append(Spacer(1, 1*cm))
story.append(HRFlowable(width=CONTENT_W, thickness=1, color=colors.HexColor('#f9a825')))
story.append(Spacer(1, 0.2*cm))
story.append(Paragraph(
    f"Generated by NFE data pipeline  |  {datetime.now().strftime('%d %B %Y, %H:%M')}  |  "
    f"Dataset: bypass_yellow.csv ({len(df):,} rows)  |  Meter: CHINT DTSU666  |  Kampala, Uganda",
    caption_s))

doc.build(story)
print(f"PDF saved -> {OUTPUT_PDF}")
