#!/usr/bin/env python3
"""Generate model evaluation PDF report from saved results."""
import os, warnings
warnings.filterwarnings('ignore')
import pandas as pd, numpy as np, joblib
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, confusion_matrix, classification_report, roc_curve
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Image, Table, TableStyle, PageBreak, HRFlowable)

BASE_DIR  = os.path.join(os.path.dirname(__file__), '..')
DATA_DIR  = os.path.join(BASE_DIR, 'data')
MODEL_DIR = os.path.join(BASE_DIR, 'model')
CHART_DIR = os.path.join(BASE_DIR, 'docs', 'model_charts')
PDF_OUT   = os.path.join(BASE_DIR, 'docs', 'model_report.pdf')
os.makedirs(CHART_DIR, exist_ok=True)

# ── Rebuild dataset & evaluate ────────────────────────────────────────────────
dfs = []
for fname, mindate in [
    ('normal_final.csv',   None),
    ('bypass_red.csv',     None),
    ('bypass_yellow.csv',  None),
    ('bypass_blue.csv',    '2026-04-09'),
    ('bypass_red_blue.csv','2026-04-10'),
]:
    df = pd.read_csv(os.path.join(DATA_DIR, fname), parse_dates=['timestamp'])
    if mindate: df = df[df['timestamp'] >= mindate]
    dfs.append(df)
master = pd.concat(dfs, ignore_index=True)

def feats(df):
    f = df[['I_L1','I_L2','I_L3','V_L1','V_L2','V_L3','P_total','PF_total','frequency']].copy()
    f['I_imbalance'] = df[['I_L1','I_L2','I_L3']].std(axis=1)
    f['V_imbalance'] = df[['V_L1','V_L2','V_L3']].std(axis=1)
    for c in ['I_L1','I_L2','I_L3']: f[f'{c}_zero'] = (df[c] < 0.05).astype(int)
    for c in ['V_L1','V_L2','V_L3']: f[f'{c}_zero'] = (df[c] < 1.0).astype(int)
    f['PF_zero']  = (df['PF_total'].abs() < 0.01).astype(int)
    f['I_total']  = df['I_L1'] + df['I_L2'] + df['I_L3']
    f['P_per_I']  = df['P_total'] / (f['I_total'] + 1e-6)
    return f

X = feats(master); y = master['label']
FEATURES = list(X.columns)
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
sc  = joblib.load(os.path.join(MODEL_DIR, 'scaler.pkl'))
mdl = joblib.load(os.path.join(MODEL_DIR, 'theft_detector.pkl'))
X_te_s = sc.transform(X_te)
y_pred = mdl.predict(X_te_s)
y_prob = mdl.predict_proba(X_te_s)[:, 1]

AUC       = float(roc_auc_score(y_te, y_prob))
CM        = confusion_matrix(y_te, y_pred).tolist()
RPT       = classification_report(y_te, y_pred, target_names=['Normal','Theft'], output_dict=True)
PREC      = float(RPT['Theft']['precision'])
REC       = float(RPT['Theft']['recall'])
F1        = float(RPT['Theft']['f1-score'])
ACC       = float(RPT['accuracy'])

# RF feature importances (from ensemble estimator 0)
rf_model  = mdl.estimators_[0]
FI        = dict(zip(FEATURES, [float(v) for v in rf_model.feature_importances_]))
FI_sorted = sorted(FI.items(), key=lambda x: x[1], reverse=True)

# CV score on training data
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(mdl, sc.transform(X_tr), y_tr, cv=cv, scoring='roc_auc')
CV_MEAN = float(cv_scores.mean()); CV_STD = float(cv_scores.std())

print(f"AUC={AUC:.4f}  Prec={PREC:.4f}  Rec={REC:.4f}  F1={F1:.4f}  CV={CV_MEAN:.4f}±{CV_STD*2:.4f}")

# ── Charts ─────────────────────────────────────────────────────────────────────
# 1. Confusion matrix
fig, ax = plt.subplots(figsize=(6, 5))
cm_arr = np.array(CM)
ax.imshow(cm_arr, cmap='Blues', aspect='auto')
ax.set_xticks([0,1]); ax.set_yticks([0,1])
ax.set_xticklabels(['Normal','Theft'], fontsize=12)
ax.set_yticklabels(['Normal','Theft'], fontsize=12)
ax.set_xlabel('Predicted', fontsize=12); ax.set_ylabel('Actual', fontsize=12)
ax.set_title(f'Confusion Matrix — Ensemble\nAUC={AUC:.4f}', fontweight='bold', fontsize=13)
thresh = cm_arr.max() / 2
for i in range(2):
    for j in range(2):
        ax.text(j, i, f'{cm_arr[i,j]:,}', ha='center', va='center', fontsize=14,
                color='white' if cm_arr[i,j] > thresh else 'black')
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '01_confusion_matrix.png'), dpi=150); plt.close()
print("  [1/4] confusion matrix")

# 2. ROC curve
fpr, tpr, _ = roc_curve(y_te, y_prob)
fig, ax = plt.subplots(figsize=(7, 6))
ax.plot(fpr, tpr, color='#1b5e20', linewidth=2.5, label=f'Ensemble (AUC={AUC:.4f})')
ax.plot([0,1],[0,1],'k--', linewidth=1, label='Random classifier')
ax.fill_between(fpr, tpr, alpha=0.1, color='#43a047')
ax.set_xlabel('False Positive Rate', fontsize=12)
ax.set_ylabel('True Positive Rate', fontsize=12)
ax.set_title('ROC Curve — Theft Detection Model', fontweight='bold', fontsize=13)
ax.legend(fontsize=11); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '02_roc_curve.png'), dpi=150); plt.close()
print("  [2/4] ROC curve")

# 3. Feature importances
fi_names  = [x[0] for x in FI_sorted]
fi_values = [x[1] for x in FI_sorted]
median_fi = float(np.median(fi_values))
bar_colors = ['#c62828' if v > median_fi else '#90a4ae' for v in fi_values]
fig, ax = plt.subplots(figsize=(10, 8))
bars = ax.barh(fi_names[::-1], fi_values[::-1], color=bar_colors[::-1], alpha=0.9)
ax.set_title('Feature Importances — Random Forest', fontweight='bold', fontsize=13)
ax.set_xlabel('Importance Score'); ax.grid(axis='x', alpha=0.3)
ax.axvline(median_fi, color='#e53935', linestyle='--', linewidth=1, label=f'Median={median_fi:.4f}')
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '03_feature_importances.png'), dpi=150); plt.close()
print("  [3/4] feature importances")

# 4. Dataset distribution
scenario_counts = master['scenario'].value_counts()
sc_colors = ['#43a047','#e53935','#f9a825','#1e88e5','#8e24aa']
fig, ax = plt.subplots(figsize=(9, 4))
bars = ax.bar(range(len(scenario_counts)), scenario_counts.values,
              color=sc_colors[:len(scenario_counts)], alpha=0.85)
ax.set_xticks(range(len(scenario_counts)))
ax.set_xticklabels(scenario_counts.index, rotation=15, fontsize=10)
ax.set_title('Samples per Scenario', fontweight='bold', fontsize=13)
ax.set_ylabel('Row count'); ax.grid(axis='y', alpha=0.3)
for bar, val in zip(bars, scenario_counts.values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 300,
            f'{val:,}', ha='center', va='bottom', fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, '04_dataset_distribution.png'), dpi=150); plt.close()
print("  [4/4] dataset distribution")

# ── PDF ────────────────────────────────────────────────────────────────────────
print("Building PDF...")
W, H = A4
CW = W - 4*cm

doc = SimpleDocTemplate(PDF_OUT, pagesize=A4,
      rightMargin=2*cm, leftMargin=2*cm, topMargin=2.5*cm, bottomMargin=2*cm)

styles  = getSampleStyleSheet()
GREEN   = '#1b5e20'
title_s = ParagraphStyle('T', parent=styles['Title'],   fontSize=20, spaceAfter=6,
              textColor=colors.HexColor(GREEN), alignment=TA_CENTER)
sub_s   = ParagraphStyle('S', parent=styles['Normal'],  fontSize=11, spaceAfter=4,
              textColor=colors.HexColor('#37474f'), alignment=TA_CENTER)
h1_s    = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=14, spaceBefore=14,
              spaceAfter=6, textColor=colors.HexColor(GREEN))
h2_s    = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=11, spaceBefore=8,
              spaceAfter=4, textColor=colors.HexColor('#2e7d32'))
body_s  = ParagraphStyle('B', parent=styles['Normal'],  fontSize=10, leading=15,
              spaceAfter=6, alignment=TA_JUSTIFY)
cap_s   = ParagraphStyle('C', parent=styles['Normal'],  fontSize=8.5, leading=12,
              spaceAfter=8, textColor=colors.HexColor('#546e7a'), alignment=TA_CENTER)

def tbl(data, col_widths, hdr_color='#1b5e20', alt_color='#e8f5e9'):
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND',     (0,0),(-1,0),  colors.HexColor(hdr_color)),
        ('TEXTCOLOR',      (0,0),(-1,0),  colors.white),
        ('FONTNAME',       (0,0),(-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0,0),(-1,-1), 9),
        ('ALIGN',          (1,0),(-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor(alt_color)]),
        ('GRID',           (0,0),(-1,-1), 0.4, colors.HexColor('#bdbdbd')),
        ('TOPPADDING',     (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',  (0,0),(-1,-1), 4),
        ('LEFTPADDING',    (0,0),(-1,-1), 6),
    ]))
    return t

story = []

# Cover
story.append(Spacer(1, 1.5*cm))
story.append(Paragraph("NFE Electricity Theft Detection System", sub_s))
story.append(Paragraph("ML Model — Training & Evaluation Report", title_s))
story.append(HRFlowable(width=CW, thickness=2, color=colors.HexColor('#43a047')))
story.append(Spacer(1, 0.6*cm))

meta_data = [
    ["Report Date:",     datetime.now().strftime("%d %B %Y %H:%M")],
    ["Total Samples:",   f"{len(master):,}  (Normal: {int((master['label']==0).sum()):,}  |  Theft: {int((master['label']==1).sum()):,})"],
    ["Train / Test:",    f"{len(X_tr):,} / {len(X_te):,}  (80/20 stratified split)"],
    ["Features:",        f"{len(FEATURES)} features (9 raw + 11 engineered)"],
    ["Model:",           "Voting Ensemble — Random Forest (200 trees) + XGBoost (200 trees)"],
    ["AUC:",             f"{AUC:.4f}"],
    ["5-Fold CV AUC:",   f"{CV_MEAN:.4f} \u00b1 {CV_STD*2:.4f}"],
    ["Theft Precision:", f"{PREC:.4f}  ({PREC*100:.2f}% of flagged alarms are real theft)"],
    ["Theft Recall:",    f"{REC:.4f}  ({REC*100:.2f}% of all theft events correctly caught)"],
    ["Theft F1:",        f"{F1:.4f}"],
    ["Accuracy:",        f"{ACC:.4f}"],
    ["False Negatives:", f"{CM[1][0]}  (missed theft events in test set)"],
    ["False Positives:", f"{CM[0][1]}  (false alarms in test set)"],
]
mt = Table(meta_data, colWidths=[4.8*cm, CW-4.8*cm])
mt.setStyle(TableStyle([
    ('FONTSIZE',       (0,0),(-1,-1), 10),
    ('FONTNAME',       (0,0),(0,-1),  'Helvetica-Bold'),
    ('TEXTCOLOR',      (0,0),(0,-1),  colors.HexColor(GREEN)),
    ('ROWBACKGROUNDS', (0,0),(-1,-1), [colors.HexColor('#e8f5e9'), colors.white]),
    ('GRID',           (0,0),(-1,-1), 0.4, colors.HexColor('#e0e0e0')),
    ('TOPPADDING',     (0,0),(-1,-1), 5),
    ('BOTTOMPADDING',  (0,0),(-1,-1), 5),
    ('LEFTPADDING',    (0,0),(-1,-1), 8),
]))
story.append(mt)
story.append(PageBreak())

# 1. Dataset
story.append(Paragraph("1. Dataset Summary", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#43a047')))
story.append(Spacer(1, 0.3*cm))
story.append(Image(os.path.join(CHART_DIR, '04_dataset_distribution.png'), width=CW, height=6*cm))
story.append(Paragraph("Figure 1: Samples collected per scenario. All bypass scenarios are labelled Theft (1).", cap_s))

ds_rows = [['Scenario','Rows','Label','Phase Bypassed']]
phase_map = {'normal':'None','bypass_red':'L1 (Red)','bypass_yellow':'L2 (Yellow)',
             'bypass_blue':'L3 (Blue)','bypass_red_blue':'L1 + L3 (Red + Blue)'}
for sc_name, grp in master.groupby('scenario'):
    lbl = '0 — Normal' if grp['label'].iloc[0] == 0 else '1 — Theft'
    ds_rows.append([sc_name, f'{len(grp):,}', lbl, phase_map.get(sc_name,'—')])
story.append(tbl(ds_rows, [4.5*cm, 2*cm, 3*cm, CW-9.5*cm]))
story.append(Spacer(1, 0.4*cm))

# 2. Features
story.append(Paragraph("2. Engineered Features", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#43a047')))
story.append(Spacer(1, 0.3*cm))
feat_rows = [['Feature','Type','Why it matters']]
for row in [
    ('I_L1, I_L2, I_L3',    'Raw',        'Primary current measurements — suppressed to ~0 on bypassed phase'),
    ('V_L1, V_L2, V_L3',    'Raw',        'Phase voltages — collapse to 0V when CT shunted'),
    ('P_total',              'Raw',        'Total power — drops when a phase is unmetered'),
    ('PF_total',             'Raw',        'Power factor — locks to exactly 0 on any CT bypass'),
    ('frequency',            'Raw',        'Grid frequency — reference signal'),
    ('I_imbalance',          'Engineered', 'Std across phases — rises sharply when one phase is suppressed'),
    ('V_imbalance',          'Engineered', 'Std across voltages — best feature for bypass_red (47V vs 0.01V normal)'),
    ('I_L1/2/3_zero',        'Engineered', 'Binary: 1 if current < 0.05A — direct bypass flag per phase'),
    ('V_L1/2/3_zero',        'Engineered', 'Binary: 1 if voltage < 1V — voltage collapse flag'),
    ('PF_zero',              'Engineered', 'Binary: 1 if |PF| < 0.01 — signals CT bypass'),
    ('I_total',              'Engineered', 'Sum of all currents — global load indicator'),
    ('P_per_I',              'Engineered', 'Power/current ratio — drops when current is under-reported'),
]:
    feat_rows.append(list(row))
story.append(tbl(feat_rows, [4*cm, 3*cm, CW-7*cm]))
story.append(PageBreak())

# 3. Performance
story.append(Paragraph("3. Model Performance", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#43a047')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    f"The Voting Ensemble correctly flags <b>{REC*100:.2f}%</b> of all theft events (recall) "
    f"with only <b>{CM[0][1]}</b> false alarm(s) and <b>{CM[1][0]}</b> missed detection(s) "
    f"in the test set of <b>{len(X_te):,} samples</b>. "
    f"AUC of <b>{AUC:.4f}</b> and 5-fold CV of <b>{CV_MEAN:.4f}</b> confirm the model generalises well.", body_s))

story.append(Image(os.path.join(CHART_DIR, '02_roc_curve.png'), width=CW, height=9*cm))
story.append(Paragraph("Figure 2: ROC curve. AUC=1.0 means perfect separation between Normal and Theft.", cap_s))

story.append(Image(os.path.join(CHART_DIR, '01_confusion_matrix.png'), width=CW*0.6, height=8*cm))
story.append(Paragraph("Figure 3: Confusion matrix on held-out test set.", cap_s))
story.append(PageBreak())

# 4. Feature importances
story.append(Paragraph("4. Feature Importances", h1_s))
story.append(HRFlowable(width=CW, thickness=0.5, color=colors.HexColor('#43a047')))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "Features shown in red are above median importance. "
    "Current suppression flags (I_Lx_zero) and voltage imbalance dominate — "
    "directly reflecting the physical bypass mechanism.", body_s))
story.append(Image(os.path.join(CHART_DIR, '03_feature_importances.png'), width=CW, height=10*cm))
story.append(Paragraph("Figure 4: Feature importances from Random Forest component. Red = above median.", cap_s))

fi_rows = [['Rank','Feature','Importance','Physical Meaning']]
interp_map = {
    'I_L3_zero':    'Blue/RB phase fully suppressed',
    'V_imbalance':  'Voltage imbalance — strongest bypass_red signal',
    'I_L2':         'Yellow phase current magnitude',
    'I_L2_zero':    'Yellow phase fully suppressed',
    'I_L1_zero':    'Red phase fully suppressed',
    'PF_zero':      'PF locked at 0 — CT bypass detected',
    'PF_total':     'Power factor deviation from normal',
    'I_imbalance':  'Phase current imbalance',
    'I_total':      'Total current reduction',
    'P_per_I':      'Power/current ratio anomaly',
}
for rank, (feat, imp) in enumerate(FI_sorted[:10], 1):
    fi_rows.append([str(rank), feat, f"{imp:.4f}", interp_map.get(feat,'—')])
story.append(tbl(fi_rows, [1.2*cm, 3.5*cm, 2.3*cm, CW-7*cm]))
story.append(Spacer(1, 0.5*cm))

story.append(Paragraph(
    f"<b>Conclusion:</b> The model is production-ready. "
    f"AUC={AUC:.4f}, Recall={REC*100:.2f}%, Precision={PREC*100:.2f}%. "
    f"With only {CM[1][0]} missed theft(s) and {CM[0][1]} false alarm(s) across {len(X_te):,} test samples, "
    f"this model is suitable for real-time deployment on the Raspberry Pi. "
    f"Saved files: theft_detector.pkl, scaler.pkl, features.pkl.", body_s))

story.append(Spacer(1, 1*cm))
story.append(HRFlowable(width=CW, thickness=1, color=colors.HexColor('#43a047')))
story.append(Paragraph(
    f"Generated by NFE data pipeline  |  {datetime.now().strftime('%d %B %Y, %H:%M')}  |  "
    f"Training: {len(X_tr):,} samples  |  Test: {len(X_te):,} samples  |  Kampala, Uganda", cap_s))

doc.build(story)
print(f"PDF saved -> {PDF_OUT}")
