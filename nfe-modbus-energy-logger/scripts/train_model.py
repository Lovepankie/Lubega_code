#!/usr/bin/env python3
"""
Electricity Theft Detection — Model Training
Trains Random Forest + XGBoost ensemble on all collected bypass scenarios.
Outputs: model files + evaluation report PDF.
"""
import os
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (classification_report, confusion_matrix,
                             roc_auc_score, roc_curve, ConfusionMatrixDisplay)
from xgboost import XGBClassifier

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                 Table, TableStyle, PageBreak, HRFlowable)
from datetime import datetime

BASE_DIR   = os.path.join(os.path.dirname(__file__), '..')
DATA_DIR   = os.path.join(BASE_DIR, 'data')
MODEL_DIR  = os.path.join(BASE_DIR, 'model')
CHART_DIR  = os.path.join(BASE_DIR, 'docs', 'model_charts')
OUTPUT_PDF = os.path.join(BASE_DIR, 'docs', 'model_report.pdf')
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)

# ── 1. Load & merge all datasets ─────────────────────────────────────────────
print("Loading datasets...")
files = {
    'normal_final.csv': None,
    'bypass_red.csv':   None,
    'bypass_yellow.csv':None,
    'bypass_blue.csv':  None,
    'bypass_red_blue.csv': None,
}

dfs = []
for fname in files:
    path = os.path.join(DATA_DIR, fname)
    df = pd.read_csv(path, parse_dates=['timestamp'])
    # Remove clock-drift rows
    if 'bypass_blue' in fname:
        df = df[df['timestamp'] >= '2026-04-09']
    if 'bypass_red_blue' in fname:
        df = df[df['timestamp'] >= '2026-04-10']
    dfs.append(df)
    print(f"  {fname:30s}: {len(df):,} rows  label={df['label'].iloc[0]}")

master = pd.concat(dfs, ignore_index=True).sort_values('timestamp').reset_index(drop=True)
print(f"\nMaster dataset: {len(master):,} rows")
print(f"  Normal (0): {(master['label']==0).sum():,}")
print(f"  Theft  (1): {(master['label']==1).sum():,}")

# ── 2. Feature Engineering ────────────────────────────────────────────────────
print("\nEngineering features...")

def engineer_features(df):
    f = pd.DataFrame()
    # Raw readings
    f['I_L1']        = df['I_L1']
    f['I_L2']        = df['I_L2']
    f['I_L3']        = df['I_L3']
    f['V_L1']        = df['V_L1']
    f['V_L2']        = df['V_L2']
    f['V_L3']        = df['V_L3']
    f['P_total']     = df['P_total']
    f['PF_total']    = df['PF_total']
    f['frequency']   = df['frequency']
    # Engineered
    f['I_imbalance'] = df[['I_L1','I_L2','I_L3']].std(axis=1)
    f['V_imbalance'] = df[['V_L1','V_L2','V_L3']].std(axis=1)
    f['I_L1_zero']   = (df['I_L1'] < 0.05).astype(int)
    f['I_L2_zero']   = (df['I_L2'] < 0.05).astype(int)
    f['I_L3_zero']   = (df['I_L3'] < 0.05).astype(int)
    f['V_L1_zero']   = (df['V_L1'] < 1.0).astype(int)
    f['V_L2_zero']   = (df['V_L2'] < 1.0).astype(int)
    f['V_L3_zero']   = (df['V_L3'] < 1.0).astype(int)
    f['PF_zero']     = (df['PF_total'].abs() < 0.01).astype(int)
    f['I_total']     = df['I_L1'] + df['I_L2'] + df['I_L3']
    f['P_per_I']     = df['P_total'] / (f['I_total'] + 1e-6)
    return f

X = engineer_features(master)
y = master['label']
FEATURES = list(X.columns)
print(f"  Features: {FEATURES}")

# ── 3. Train/Test Split ───────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

print(f"\nTrain: {len(X_train):,}  |  Test: {len(X_test):,}")

# ── 4. Train Models ───────────────────────────────────────────────────────────
print("\nTraining models...")

rf = RandomForestClassifier(n_estimators=200, max_depth=15,
                             random_state=42, n_jobs=-1, class_weight='balanced')
xgb = XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1,
                     random_state=42, eval_metric='logloss',
                     scale_pos_weight=(y_train==0).sum()/(y_train==1).sum())

rf.fit(X_train_s, y_train)
print("  Random Forest trained")
xgb.fit(X_train_s, y_train)
print("  XGBoost trained")

ensemble = VotingClassifier(
    estimators=[('rf', rf), ('xgb', xgb)],
    voting='soft')
ensemble.fit(X_train_s, y_train)
print("  Ensemble trained")

# ── 5. Evaluate ───────────────────────────────────────────────────────────────
print("\nEvaluating...")

results = {}
for name, model in [('Random Forest', rf), ('XGBoost', xgb), ('Ensemble', ensemble)]:
    y_pred = model.predict(X_test_s)
    y_prob = model.predict_proba(X_test_s)[:,1]
    auc    = roc_auc_score(y_test, y_prob)
    cm     = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=['Normal','Theft'], output_dict=True)
    results[name] = {'pred': y_pred, 'prob': y_prob, 'auc': auc, 'cm': cm, 'report': report}
    print(f"  {name}: AUC={auc:.4f}  Precision={report['Theft']['precision']:.4f}  Recall={report['Theft']['recall']:.4f}  F1={report['Theft']['f1-score']:.4f}")

# Cross-validation on best model
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(ensemble, X_train_s, y_train, cv=cv, scoring='roc_auc')
print(f"\n  5-Fold CV AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")

# ── 6. Charts ─────────────────────────────────────────────────────────────────
print("\nGenerating charts...")

# Chart 1: Confusion matrices
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
for ax, (name, res) in zip(axes, results.items()):
    cm_vals = res['cm']
    im = ax.imshow(cm_vals, interpolation='nearest', cmap='Blues')
    ax.set_xticks([0,1]); ax.set_yticks([0,1])
    ax.set_xticklabels(['Normal','Theft']); ax.set_yticklabels(['Normal','Theft'])
    ax.set_xlabel('Predicted'); ax.set_ylabel('Actual')
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm_vals[i,j]), ha='center', va='center',
                    color='white' if cm_vals[i,j] > cm_vals.max()/2 else 'black', fontsize=12)
    ax.set_title(f'{name}\nAUC={res["auc"]:.4f}', fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '01_confusion_matrices.png'), dpi=150); plt.close()
print("  [1/4] confusion matrices")

# Chart 2: ROC curves
fig, ax = plt.subplots(figsize=(8, 6))
colors_roc = ['#1e88e5', '#e53935', '#43a047']
for (name, res), c in zip(results.items(), colors_roc):
    fpr, tpr, _ = roc_curve(y_test, res['prob'])
    ax.plot(fpr, tpr, color=c, linewidth=2, label=f'{name} (AUC={res["auc"]:.4f})')
ax.plot([0,1],[0,1],'k--', linewidth=1, label='Random')
ax.set_xlabel('False Positive Rate'); ax.set_ylabel('True Positive Rate')
ax.set_title('ROC Curves — All Models', fontweight='bold', fontsize=13)
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '02_roc_curves.png'), dpi=150); plt.close()
print("  [2/4] ROC curves")

# Chart 3: Feature importances (RF)
fi = pd.Series(rf.feature_importances_, index=FEATURES).sort_values(ascending=True)
fig, ax = plt.subplots(figsize=(10, 8))
colors_fi = ['#e53935' if v > fi.median() else '#90a4ae' for v in fi.values]
fi.plot(kind='barh', ax=ax, color=colors_fi)
ax.set_title('Feature Importances — Random Forest', fontweight='bold', fontsize=13)
ax.set_xlabel('Importance'); ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '03_feature_importances.png'), dpi=150); plt.close()
print("  [3/4] feature importances")

# Chart 4: Class distribution
fig, ax = plt.subplots(figsize=(8, 4))
scenario_counts = master['scenario'].value_counts()
colors_sc = ['#43a047','#e53935','#f9a825','#1e88e5','#8e24aa']
bars = ax.bar(scenario_counts.index, scenario_counts.values, color=colors_sc[:len(scenario_counts)], alpha=0.85)
ax.set_title('Samples per Scenario', fontweight='bold', fontsize=13)
ax.set_ylabel('Row count'); ax.grid(axis='y', alpha=0.3)
for bar, val in zip(bars, scenario_counts.values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 200,
            f'{val:,}', ha='center', va='bottom', fontsize=9)
plt.xticks(rotation=20); plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '04_class_distribution.png'), dpi=150); plt.close()
print("  [4/4] class distribution")

# ── 7. Save Models ────────────────────────────────────────────────────────────
joblib.dump(ensemble, os.path.join(MODEL_DIR, 'theft_detector.pkl'))
joblib.dump(scaler,   os.path.join(MODEL_DIR, 'scaler.pkl'))
joblib.dump(FEATURES, os.path.join(MODEL_DIR, 'features.pkl'))
print(f"\nModels saved to {MODEL_DIR}/")

# ── 8. PDF Report ─────────────────────────────────────────────────────────────
print("Generating PDF report...")
W, H = A4
CONTENT_W = W - 4*cm

doc = SimpleDocTemplate(OUTPUT_PDF, pagesize=A4,
    rightMargin=2*cm, leftMargin=2*cm,
    topMargin=2.5*cm, bottomMargin=2*cm)

styles = getSampleStyleSheet()
GREEN = '#1b5e20'
title_s    = ParagraphStyle('T', parent=styles['Title'], fontSize=22, spaceAfter=6,
                textColor=colors.HexColor(GREEN), alignment=TA_CENTER)
subtitle_s = ParagraphStyle('S', parent=styles['Normal'], fontSize=11, spaceAfter=4,
                textColor=colors.HexColor('#37474f'), alignment=TA_CENTER)
h1_s = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=15, spaceBefore=14,
                spaceAfter=6, textColor=colors.HexColor(GREEN))
h2_s = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=12, spaceBefore=10,
                spaceAfter=4, textColor=colors.HexColor('#2e7d32'))
body_s = ParagraphStyle('B', parent=styles['Normal'], fontSize=10, leading=15,
                spaceAfter=6, alignment=TA_JUSTIFY)
caption_s = ParagraphStyle('C', parent=styles['Normal'], fontSize=8.5, leading=12,
                spaceAfter=8, textColor=colors.HexColor('#546e7a'), alignment=TA_CENTER)
info_s = ParagraphStyle('I', parent=styles['Normal'], fontSize=10, leading=14,
                backColor=colors.HexColor('#e8f5e9'),
                spaceBefore=4, spaceAfter=8)
alert_s = ParagraphStyle('A', parent=styles['Normal'], fontSize=10, leading=14,
                backColor=colors.HexColor('#e8eaf6'),
                spaceBefore=4, spaceAfter=8)

story = []
story.append(Spacer(1, 1.5*cm))
story.append(Paragraph("NFE Electricity Theft Detection System", subtitle_s))
story.append(Paragraph("ML Model — Training & Evaluation Report", title_s))
story.append(HRFlowable(width=CONTENT_W, thickness=2, color=colors.HexColor('#43a047')))
story.append(Spacer(1, 0.5*cm))

best = results['Ensemble']
meta = [
    ["Report Date:",     datetime.now().strftime("%d %B %Y %H:%M")],
    ["Total Samples:",   f"{len(master):,}  (Normal: {(master['label']==0).sum():,}  |  Theft: {(master['label']==1).sum():,})"],
    ["Train / Test:",    f"{len(X_train):,} / {len(X_test):,}  (80/20 stratified split)"],
    ["Features:",        f"{len(FEATURES)} engineered features"],
    ["Best Model:",      f"Voting Ensemble (RF + XGBoost)"],
    ["AUC Score:",       f"{best['auc']:.4f}"],
    ["5-Fold CV AUC:",   f"{cv_scores.mean():.4f} ± {cv_scores.std()*2:.4f}"],
    ["Theft Precision:", f"{best['report']['Theft']['precision']:.4f}"],
    ["Theft Recall:",    f"{best['report']['Theft']['recall']:.4f}"],
    ["Theft F1:",        f"{best['report']['Theft']['f1-score']:.4f}"],
]
mt = Table(meta, colWidths=[4.5*cm, CONTENT_W-4.5*cm])
mt.setStyle(TableStyle([
    ('FONTSIZE',    (0,0),(-1,-1), 10),
    ('FONTNAME',    (0,0),(0,-1), 'Helvetica-Bold'),
    ('TEXTCOLOR',   (0,0),(0,-1), colors.HexColor(GREEN)),
    ('ROWBACKGROUNDS', (0,0),(-1,-1), [colors.HexColor('#e8f5e9'), colors.white]),
    ('GRID',        (0,0),(-1,-1), 0.4, colors.HexColor('#e0e0e0')),
    ('TOPPADDING',  (0,0),(-1,-1), 5), ('BOTTOMPADDING',(0,0),(-1,-1), 5),
    ('LEFTPADDING', (0,0),(-1,-1), 8),
]))
story.append(mt)
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph(
    f"The ensemble model achieves <b>AUC={best['auc']:.4f}</b> on the held-out test set and "
    f"<b>{cv_scores.mean():.4f} ± {cv_scores.std()*2:.4f}</b> on 5-fold cross-validation. "
    f"Theft detection recall of <b>{best['report']['Theft']['recall']:.4f}</b> means the model correctly "
    f"identifies {best['report']['Theft']['recall']*100:.1f}% of all theft events. "
    f"Precision of <b>{best['report']['Theft']['precision']:.4f}</b> means {best['report']['Theft']['precision']*100:.1f}% "
    f"of flagged events are true theft.", info_s))

story.append(PageBreak())

# Dataset section
story.append(Paragraph("1. Dataset Summary", h1_s))
story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=colors.HexColor('#43a047')))
story.append(Spacer(1, 0.3*cm))
img = Image(os.path.join(CHART_DIR, '04_class_distribution.png'), width=CONTENT_W, height=6*cm)
story.append(img)
story.append(Paragraph("Figure 1: Sample count per scenario. All bypass scenarios are labelled Theft (1).", caption_s))

ds_data = [['Scenario','Rows','Label','Phase Bypassed']]
for name, df in [('normal_final',master[master['scenario']=='normal']),
                  ('bypass_red',master[master['scenario']=='bypass_red']),
                  ('bypass_yellow',master[master['scenario']=='bypass_yellow']),
                  ('bypass_blue',master[master['scenario']=='bypass_blue']),
                  ('bypass_red_blue',master[master['scenario']=='bypass_red_blue'])]:
    lbl = '0 — Normal' if 'normal' in name else '1 — Theft'
    phase = {'normal_final':'None','bypass_red':'L1 (Red)','bypass_yellow':'L2 (Yellow)',
             'bypass_blue':'L3 (Blue)','bypass_red_blue':'L1+L3 (Red+Blue)'}.get(name,'—')
    ds_data.append([name, f'{len(df):,}', lbl, phase])

dt = Table(ds_data, colWidths=[4.5*cm, 2*cm, 3*cm, CONTENT_W-9.5*cm])
dt.setStyle(TableStyle([
    ('BACKGROUND',  (0,0),(-1,0), colors.HexColor(GREEN)),
    ('TEXTCOLOR',   (0,0),(-1,0), colors.white),
    ('FONTNAME',    (0,0),(-1,0), 'Helvetica-Bold'),
    ('FONTSIZE',    (0,0),(-1,-1), 9),
    ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor('#e8f5e9')]),
    ('GRID',        (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',  (0,0),(-1,-1), 4), ('BOTTOMPADDING',(0,0),(-1,-1), 4),
    ('LEFTPADDING', (0,0),(-1,-1), 6),
]))
story.append(dt)

# Features section
story.append(Paragraph("2. Engineered Features", h1_s))
story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=colors.HexColor('#43a047')))
story.append(Spacer(1, 0.3*cm))
feat_data = [['Feature','Type','Description']]
feat_info = [
    ('I_L1, I_L2, I_L3','Raw','Phase currents in Amperes'),
    ('V_L1, V_L2, V_L3','Raw','Phase voltages in Volts'),
    ('P_total','Raw','Total active power in kW'),
    ('PF_total','Raw','Power factor'),
    ('frequency','Raw','Grid frequency in Hz'),
    ('I_imbalance','Engineered','Std deviation across I_L1/L2/L3 — rises when one phase is suppressed'),
    ('V_imbalance','Engineered','Std deviation across V_L1/L2/L3 — spikes on bypass_red'),
    ('I_L1/2/3_zero','Engineered','Binary flag: 1 if phase current < 0.05A (suppressed)'),
    ('V_L1/2/3_zero','Engineered','Binary flag: 1 if phase voltage < 1V (collapsed)'),
    ('PF_zero','Engineered','Binary flag: 1 if |PF| < 0.01 (locked to 0 on CT bypass)'),
    ('I_total','Engineered','Sum of all phase currents'),
    ('P_per_I','Engineered','Power per unit current — drops when current under-reported'),
]
for row in feat_info:
    feat_data.append(list(row))

ft = Table(feat_data, colWidths=[4*cm, 3*cm, CONTENT_W-7*cm])
ft.setStyle(TableStyle([
    ('BACKGROUND',  (0,0),(-1,0), colors.HexColor(GREEN)),
    ('TEXTCOLOR',   (0,0),(-1,0), colors.white),
    ('FONTNAME',    (0,0),(-1,0), 'Helvetica-Bold'),
    ('FONTSIZE',    (0,0),(-1,-1), 8.5),
    ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor('#e8f5e9')]),
    ('GRID',        (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',  (0,0),(-1,-1), 4), ('BOTTOMPADDING',(0,0),(-1,-1), 4),
    ('LEFTPADDING', (0,0),(-1,-1), 6),
]))
story.append(ft)

story.append(PageBreak())

# Model results
story.append(Paragraph("3. Model Performance", h1_s))
story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=colors.HexColor('#43a047')))
story.append(Spacer(1, 0.3*cm))

perf_data = [['Model','AUC','Precision','Recall','F1-Score','Accuracy']]
for name, res in results.items():
    r = res['report']
    perf_data.append([
        name,
        f"{res['auc']:.4f}",
        f"{r['Theft']['precision']:.4f}",
        f"{r['Theft']['recall']:.4f}",
        f"{r['Theft']['f1-score']:.4f}",
        f"{r['accuracy']:.4f}",
    ])
pt = Table(perf_data, colWidths=[4*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.2*cm])
pt.setStyle(TableStyle([
    ('BACKGROUND',  (0,0),(-1,0), colors.HexColor(GREEN)),
    ('TEXTCOLOR',   (0,0),(-1,0), colors.white),
    ('FONTNAME',    (0,0),(-1,0), 'Helvetica-Bold'),
    ('FONTSIZE',    (0,0),(-1,-1), 9),
    ('ALIGN',       (1,0),(-1,-1), 'CENTER'),
    ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor('#e8f5e9')]),
    ('GRID',        (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',  (0,0),(-1,-1), 5), ('BOTTOMPADDING',(0,0),(-1,-1), 5),
    ('LEFTPADDING', (0,0),(-1,-1), 6),
]))
story.append(pt)
story.append(Spacer(1, 0.4*cm))

img2 = Image(os.path.join(CHART_DIR, '02_roc_curves.png'), width=CONTENT_W, height=9*cm)
story.append(img2)
story.append(Paragraph("Figure 2: ROC curves for all three models. Higher AUC = better discrimination.", caption_s))

img3 = Image(os.path.join(CHART_DIR, '01_confusion_matrices.png'), width=CONTENT_W, height=6*cm)
story.append(img3)
story.append(Paragraph("Figure 3: Confusion matrices on test set. Rows=Actual, Cols=Predicted.", caption_s))

story.append(PageBreak())

# Feature importance
story.append(Paragraph("4. Feature Importances", h1_s))
story.append(HRFlowable(width=CONTENT_W, thickness=0.5, color=colors.HexColor('#43a047')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "The chart below shows which features contribute most to the Random Forest's decisions. "
    "Features highlighted in red are above the median importance — these are the primary theft indicators.", body_s))
img4 = Image(os.path.join(CHART_DIR, '03_feature_importances.png'), width=CONTENT_W, height=10*cm)
story.append(img4)
story.append(Paragraph("Figure 4: Feature importances from Random Forest. Red = above median importance.", caption_s))

# Top features table
fi_sorted = pd.Series(rf.feature_importances_, index=FEATURES).sort_values(ascending=False)
fi_data = [['Rank','Feature','Importance','Interpretation']]
interpretations = {
    'I_L3_zero': 'Blue/RB phase suppressed — strongest bypass_blue indicator',
    'I_L2': 'Yellow phase current — drops on bypass_yellow',
    'I_L2_zero': 'Yellow phase suppressed',
    'I_L1_zero': 'Red phase suppressed',
    'V_imbalance': 'Voltage imbalance — strongest bypass_red indicator',
    'I_imbalance': 'Current imbalance across phases',
    'PF_zero': 'PF locked at 0 — indicates CT bypass',
    'PF_total': 'Power factor shift',
    'I_total': 'Total current reduction',
    'P_per_I': 'Power/current ratio anomaly',
}
for rank, (feat, imp) in enumerate(fi_sorted.head(10).items(), 1):
    interp = interpretations.get(feat, '—')
    fi_data.append([str(rank), feat, f"{imp:.4f}", interp])

fit = Table(fi_data, colWidths=[1.2*cm, 3.5*cm, 2.3*cm, CONTENT_W-7*cm])
fit.setStyle(TableStyle([
    ('BACKGROUND',  (0,0),(-1,0), colors.HexColor(GREEN)),
    ('TEXTCOLOR',   (0,0),(-1,0), colors.white),
    ('FONTNAME',    (0,0),(-1,0), 'Helvetica-Bold'),
    ('FONTSIZE',    (0,0),(-1,-1), 8.5),
    ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor('#e8f5e9')]),
    ('GRID',        (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
    ('TOPPADDING',  (0,0),(-1,-1), 4), ('BOTTOMPADDING',(0,0),(-1,-1), 4),
    ('LEFTPADDING', (0,0),(-1,-1), 6),
]))
story.append(fit)
story.append(Spacer(1, 0.5*cm))

story.append(Paragraph(
    f"<b>Conclusion:</b> The Voting Ensemble (Random Forest + XGBoost) achieves AUC={best['auc']:.4f} "
    f"with {best['report']['Theft']['recall']*100:.1f}% theft recall on unseen data. "
    f"The top features are current suppression flags (I_Lx_zero), voltage imbalance, and PF_zero — "
    f"all directly tied to the physical bypass mechanism. "
    f"The model is ready for deployment on the Raspberry Pi for real-time detection.", info_s))

story.append(Spacer(1, 1*cm))
story.append(HRFlowable(width=CONTENT_W, thickness=1, color=colors.HexColor('#43a047')))
story.append(Paragraph(
    f"Generated by NFE data pipeline  |  {datetime.now().strftime('%d %B %Y, %H:%M')}  |  "
    f"Training samples: {len(X_train):,}  |  Test samples: {len(X_test):,}  |  Kampala, Uganda",
    caption_s))

doc.build(story)
print(f"PDF saved -> {OUTPUT_PDF}")
print("\nDone.")
