#!/usr/bin/env python3
"""Regenerate all 8 analysis charts from normal_final.csv"""
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

BASE_DIR  = os.path.join(os.path.dirname(__file__), '..')
DATA_PATH = os.path.join(BASE_DIR, 'data', 'normal_final.csv')
OUT_DIR   = os.path.join(BASE_DIR, 'docs', 'charts')
os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(DATA_PATH, parse_dates=['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
df['hour'] = df['timestamp'].dt.hour

print(f"Loaded {len(df):,} rows  |  {df['timestamp'].min()} -> {df['timestamp'].max()}")

FMT = '%d %b %H:%M'
STYLE = {'linewidth': 0.7, 'alpha': 0.85}

# ── 1. Voltage ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(df['timestamp'], df['V_L1'], label='L1', color='#e53935', **STYLE)
ax.plot(df['timestamp'], df['V_L2'], label='L2', color='#1e88e5', **STYLE)
ax.plot(df['timestamp'], df['V_L3'], label='L3', color='#43a047', **STYLE)
ax.axhline(180, color='red', linestyle='--', linewidth=1, label='180V threshold')
ax.axhline(240, color='gray', linestyle=':', linewidth=0.8, label='240V nominal')
ax.set_title('Three-Phase Voltage Over Time', fontsize=13, fontweight='bold')
ax.set_ylabel('Voltage (V)'); ax.legend(loc='upper right'); ax.grid(alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter(FMT)); plt.xticks(rotation=30)
plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, '01_voltage.png'), dpi=150); plt.close()
print("  [1/8] 01_voltage.png")

# ── 2. Current ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(df['timestamp'], df['I_L1'], label='L1', color='#e53935', **STYLE)
ax.plot(df['timestamp'], df['I_L2'], label='L2', color='#1e88e5', **STYLE)
ax.plot(df['timestamp'], df['I_L3'], label='L3', color='#43a047', **STYLE)
ax.set_title('Three-Phase Current Over Time', fontsize=13, fontweight='bold')
ax.set_ylabel('Current (A)'); ax.legend(loc='upper right'); ax.grid(alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter(FMT)); plt.xticks(rotation=30)
plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, '02_current.png'), dpi=150); plt.close()
print("  [2/8] 02_current.png")

# ── 3. Total Power ────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(df['timestamp'], df['P_total'], color='#7b1fa2', **STYLE)
ax.fill_between(df['timestamp'], df['P_total'], alpha=0.15, color='#7b1fa2')
ax.set_title('Total Active Power Over Time', fontsize=13, fontweight='bold')
ax.set_ylabel('Power (kW)'); ax.grid(alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter(FMT)); plt.xticks(rotation=30)
plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, '03_power.png'), dpi=150); plt.close()
print("  [3/8] 03_power.png")

# ── 4. Hourly Average Power ───────────────────────────────────────────────────
hourly = df.groupby('hour')['P_total'].mean()
fig, ax = plt.subplots(figsize=(12, 4))
bars = ax.bar(hourly.index, hourly.values, color='#0288d1', edgecolor='white', width=0.7)
ax.bar_label(bars, fmt='%.3f', fontsize=7, padding=2)
ax.set_title('Average Active Power by Hour of Day', fontsize=13, fontweight='bold')
ax.set_xlabel('Hour'); ax.set_ylabel('Avg Power (kW)'); ax.grid(axis='y', alpha=0.3)
ax.set_xticks(range(24))
plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, '04_hourly_power.png'), dpi=150); plt.close()
print("  [4/8] 04_hourly_power.png")

# ── 5. Frequency ──────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 3.5))
ax.plot(df['timestamp'], df['frequency'], color='#00838f', **STYLE)
ax.axhline(50.0, color='green', linestyle='--', linewidth=1, label='50 Hz nominal')
ax.axhline(49.0, color='red',   linestyle=':', linewidth=0.8, label='49 Hz lower')
ax.axhline(51.0, color='red',   linestyle=':', linewidth=0.8, label='51 Hz upper')
ax.set_title('Grid Frequency Over Time', fontsize=13, fontweight='bold')
ax.set_ylabel('Frequency (Hz)'); ax.legend(); ax.grid(alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter(FMT)); plt.xticks(rotation=30)
plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, '05_frequency.png'), dpi=150); plt.close()
print("  [5/8] 05_frequency.png")

# ── 6. Cumulative Energy ──────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(df['timestamp'], df['energy_total'], color='#f57c00', linewidth=1.2)
ax.fill_between(df['timestamp'], df['energy_total'], alpha=0.15, color='#f57c00')
ax.set_title('Cumulative Energy Consumption', fontsize=13, fontweight='bold')
ax.set_ylabel('Energy (kWh)'); ax.grid(alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter(FMT)); plt.xticks(rotation=30)
plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, '06_energy.png'), dpi=150); plt.close()
print("  [6/8] 06_energy.png")

# ── 7. Current Histogram ──────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 4))
ax.hist(df['I_L1'], bins=60, alpha=0.7, label='L1', color='#e53935')
ax.hist(df['I_L2'], bins=60, alpha=0.7, label='L2', color='#1e88e5')
ax.hist(df['I_L3'], bins=60, alpha=0.7, label='L3', color='#43a047')
ax.set_title('Current Distribution by Phase', fontsize=13, fontweight='bold')
ax.set_xlabel('Current (A)'); ax.set_ylabel('Count'); ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, '07_current_hist.png'), dpi=150); plt.close()
print("  [7/8] 07_current_hist.png")

# ── 8. Per-Phase Power ────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(df['timestamp'], df['P_L1'], label='P L1', color='#e53935', **STYLE)
ax.plot(df['timestamp'], df['P_L2'], label='P L2', color='#1e88e5', **STYLE)
ax.plot(df['timestamp'], df['P_L3'], label='P L3', color='#43a047', **STYLE)
ax.set_title('Per-Phase Active Power Over Time', fontsize=13, fontweight='bold')
ax.set_ylabel('Power (kW)'); ax.legend(); ax.grid(alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter(FMT)); plt.xticks(rotation=30)
plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, '08_phase_power.png'), dpi=150); plt.close()
print("  [8/8] 08_phase_power.png")

print("\nAll charts saved to:", OUT_DIR)
