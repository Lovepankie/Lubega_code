# Lubega — Work Plan: Getting to Live Inference

**Branch:** `feature/live-inference-dashboard`  
**Goal:** Real-time CT bypass theft detection running on Pi, alerts visible on Streamlit dashboard  
**Players:** Hillary (cloud/dashboard) · Dennis (edge inference/Pi)

---

## What's Already Done

| Component | Status | Notes |
|---|---|---|
| Meter polling (10s Modbus RTU) | ✅ Done | `src/meter_reader.py` |
| 15-min aggregation + CSV logging | ✅ Done | `src/aggregator.py` |
| `meter.service` (systemd) | ✅ Done | Running on Pi in production |
| ~160K labelled training samples | ✅ Done | `docs/*.csv` (8 bypass scenarios) |
| Feature engineering pipeline | ✅ Done | 20 features (9 raw + 11 engineered) |
| VotingClassifier (RF + XGBoost) | ✅ Done | AUC = 1.0000 on test set |
| Model artefacts serialised | ✅ Done | `model/theft_detector.pkl` (14.4 MB) + `scaler.pkl` + `features.pkl` |
| ZeroTier VPN (remote Pi access) | ✅ Done | Pi at 192.168.100.11 |

---

## What's Left — Chronological Order

### STEP 1 — Hillary: Set up Neon PostgreSQL *(~30 min)*
> **Do this first. Dennis cannot test his INSERT code without the database URL.**

1. Go to [neon.tech](https://neon.tech) → sign in (same account as DSN project)
2. Create a new project: **`lubega-production`**
3. Open the SQL editor and run:

```sql
CREATE TABLE alerts (
    id          BIGSERIAL PRIMARY KEY,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    meter_id    INT NOT NULL,
    meter_name  TEXT NOT NULL,
    prediction  INT NOT NULL,
    probability FLOAT NOT NULL,
    i_l1 FLOAT, i_l2 FLOAT, i_l3 FLOAT,
    v_l1 FLOAT, v_l2 FLOAT, v_l3 FLOAT,
    p_total FLOAT, pf_total FLOAT, frequency FLOAT
);

CREATE TABLE readings (
    id          BIGSERIAL PRIMARY KEY,
    logged_at   TIMESTAMPTZ NOT NULL,
    meter_id    INT NOT NULL,
    meter_name  TEXT NOT NULL,
    v_l1 FLOAT, v_l2 FLOAT, v_l3 FLOAT,
    i_l1 FLOAT, i_l2 FLOAT, i_l3 FLOAT,
    p_total FLOAT, pf_total FLOAT, frequency FLOAT
);
```

4. Copy the connection string (format: `postgresql://neondb_owner:<password>@<endpoint>.neon.tech/neondb?sslmode=require`)
5. **Send the connection string to Dennis** — this is his `NEON_DATABASE_URL`

---

### STEP 2 — Dennis: Write `feature_engineering.py` *(~2 hrs)*

**File:** `nfe-modbus-energy-logger/src/feature_engineering.py`

Takes one row from the aggregated CSV, returns a dict of all 20 features:

```python
def engineer_features(row):
    i_l1, i_l2, i_l3 = row['i_l1'], row['i_l2'], row['i_l3']
    v_l1, v_l2, v_l3 = row['v_l1'], row['v_l2'], row['v_l3']
    i_total = i_l1 + i_l2 + i_l3

    return {
        # raw (9)
        'i_l1': i_l1, 'i_l2': i_l2, 'i_l3': i_l3,
        'v_l1': v_l1, 'v_l2': v_l2, 'v_l3': v_l3,
        'p_total':   row['p_total'],
        'pf_total':  row['pf_total'],
        'frequency': row['frequency'],
        # engineered (11)
        'i_imbalance': max(i_l1,i_l2,i_l3) - min(i_l1,i_l2,i_l3),
        'v_imbalance': max(v_l1,v_l2,v_l3) - min(v_l1,v_l2,v_l3),
        'i_l1_zero':   1 if i_l1 < 0.01 else 0,
        'i_l2_zero':   1 if i_l2 < 0.01 else 0,
        'i_l3_zero':   1 if i_l3 < 0.01 else 0,
        'v_l1_zero':   1 if v_l1 < 10 else 0,
        'v_l2_zero':   1 if v_l2 < 10 else 0,
        'v_l3_zero':   1 if v_l3 < 10 else 0,
        'pf_zero':     1 if row['pf_total'] < 0.05 else 0,
        'i_total':     i_total,
        'p_per_i':     row['p_total'] / (i_total + 0.001),
    }
```

**Test it:** load any row from `docs/*.csv` using pandas and print the output. All 20 keys must be present.

> **Critical:** The feature names and order must exactly match what the model was trained on.  
> Load `model/features.pkl` and verify your dict keys match that list before proceeding to Step 3.

---

### STEP 3 — Dennis: Write `detect.py` *(~3 hrs)*

**File:** `nfe-modbus-energy-logger/detect.py`

```python
import os, pickle, time, logging
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from src.feature_engineering import engineer_features

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

load_dotenv()
NEON_URL  = os.environ['NEON_DATABASE_URL']
THRESHOLD = float(os.environ.get('THEFT_THRESHOLD', '0.5'))
CSV_PATH  = os.environ.get('CSV_PATH', 'data/current.csv')
METER_ID  = int(os.environ.get('METER_ID', '1'))
METER_NAME = os.environ.get('METER_NAME', 'Meter-01')

# Load model artefacts once at startup
with open('model/theft_detector.pkl', 'rb') as f: model  = pickle.load(f)
with open('model/scaler.pkl',         'rb') as f: scaler = pickle.load(f)
with open('model/features.pkl',       'rb') as f: features = pickle.load(f)

logging.info("Model loaded. Starting inference loop.")

while True:
    try:
        df  = pd.read_csv(CSV_PATH)
        row = df.iloc[-1]                          # last 15-min window
        feat_dict  = engineer_features(row)
        X          = [feat_dict[f] for f in features]   # ordered correctly
        X_scaled   = scaler.transform([X])
        prob       = model.predict_proba(X_scaled)[0][1] # P(theft)
        pred       = 1 if prob >= THRESHOLD else 0

        logging.info(f"pred={pred} prob={prob:.4f}")

        if pred == 1:
            try:
                conn = psycopg2.connect(NEON_URL)
                cur  = conn.cursor()
                cur.execute(
                    """INSERT INTO alerts
                       (meter_id, meter_name, prediction, probability,
                        i_l1, i_l2, i_l3, v_l1, v_l2, v_l3,
                        p_total, pf_total, frequency)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (METER_ID, METER_NAME, pred, prob,
                     row.i_l1, row.i_l2, row.i_l3,
                     row.v_l1, row.v_l2, row.v_l3,
                     row.p_total, row.pf_total, row.frequency)
                )
                conn.commit()
                conn.close()
                logging.info("Alert inserted into Neon.")
            except Exception as e:
                logging.error(f"Neon insert failed: {e}")  # don't crash inference

    except Exception as e:
        logging.error(f"Inference error: {e}")

    time.sleep(900)  # wait for next 15-min window
```

**Create `.env` on the Pi** (never commit this file):
```
NEON_DATABASE_URL=postgresql://neondb_owner:<password>@<endpoint>.neon.tech/neondb?sslmode=require
THEFT_THRESHOLD=0.5
CSV_PATH=/home/pi/nfe-modbus-energy-logger/data/current.csv
METER_ID=1
METER_NAME=Meter-01
```

---

### STEP 4 — Dennis: Write `theft-detector.service` *(~30 min)*

**File:** `nfe-modbus-energy-logger/systemd/theft-detector.service`

```ini
[Unit]
Description=Lubega Electricity Theft Detector
After=network.target meter.service
Requires=meter.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/nfe-modbus-energy-logger
EnvironmentFile=/home/pi/nfe-modbus-energy-logger/.env
ExecStart=/home/pi/nfe-modbus-energy-logger/venv/bin/python detect.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Deploy to Pi:**
```bash
sudo cp systemd/theft-detector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable theft-detector
sudo systemctl start theft-detector
sudo journalctl -fu theft-detector    # watch logs live
```

---

### STEP 5 — Dennis: End-to-end test on Pi *(~1 hr)*

1. Confirm `meter.service` is writing to CSV normally:
   ```bash
   tail -f data/current.csv
   ```
2. Start `theft-detector.service` and watch logs:
   ```bash
   sudo journalctl -fu theft-detector
   ```
3. **Simulate a theft** — manually edit the last row of `current.csv`, set `i_l1=0.000` (L1 bypass). Wait up to 15 min for the next inference cycle, or restart detect.py to trigger immediately.
4. Check the Neon SQL editor — confirm a row appeared in the `alerts` table.
5. **Tell Hillary:** "Neon is receiving alerts" — that is his go signal to deploy the dashboard.

---

### STEP 6 — Hillary: Write `app/app.py` *(~3 hrs)*
> Can be started any time after Step 1. Finish after Dennis confirms Step 5.

**File:** `app/app.py`

```python
import streamlit as st

st.set_page_config(page_title="Lubega Theft Detection", layout="wide")
conn = st.connection("neon", type="sql", url=st.secrets["NEON_DATABASE_URL"])

st.title("Lubega — Real-Time Electricity Theft Detection")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Theft Alerts")
    alerts = conn.query(
        "SELECT detected_at, meter_name, probability, prediction, i_l1, i_l2, i_l3 "
        "FROM alerts ORDER BY detected_at DESC LIMIT 200",
        ttl=60
    )
    st.dataframe(alerts, use_container_width=True)

with col2:
    st.subheader("Live Readings (last 24 hrs)")
    readings = conn.query(
        "SELECT logged_at, i_l1, i_l2, i_l3, v_l1, v_l2, v_l3, p_total "
        "FROM readings ORDER BY logged_at DESC LIMIT 96",
        ttl=60
    )
    if not readings.empty:
        st.line_chart(readings.set_index("logged_at")[["i_l1","i_l2","i_l3"]],
                      height=300)
```

Build from there — add colour coding for high-probability alerts, per-phase charts, alert count KPIs.

---

### STEP 7 — Hillary: Deploy to Streamlit Community Cloud *(~30 min)*

1. Push `app/app.py` to GitHub on the `feature/live-inference-dashboard` branch
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Connect to the `Lubega_code` GitHub repo
4. Set: Branch = `feature/live-inference-dashboard`, Main file = `app/app.py`
5. Under **Secrets**, add:
   ```toml
   NEON_DATABASE_URL = "postgresql://neondb_owner:..."
   ```
6. Deploy → copy the public URL → share with Dennis

---

### STEP 8 — Both: Full end-to-end test *(~1 hr together)*

- Dennis simulates a bypass on the live meter (or edits a CSV row as in Step 5)
- Both watch the Streamlit dashboard — alert should appear within 15 minutes
- Confirm timestamp, probability score, and phase readings are correct
- **Done — system is live**

---

## Dependency Map

```
Hillary → Step 1 (Neon setup) ─────────────────────────────────────────────────────────┐
                 │ sends NEON_DATABASE_URL to Dennis                                    │
                 ↓                                                                      ↓
Dennis  → Step 2 (feature_engineering.py)                               Hillary → Step 6 (app.py)
            → Step 3 (detect.py)                                                  → Step 7 (deploy)
              → Step 4 (systemd service)                                                │
                → Step 5 (Pi test) ─── "alerts flowing" signal ────────────────────────┘
                                                                                        ↓
                                                                    Both → Step 8 (end-to-end test)
```

**Estimated time:** one focused weekend.

---

## Key Files Reference

```
Lubega_code/
├── WORK_PLAN.md                          ← you are here
├── Lubega_Project_Report.docx            ← fill in student names + reg numbers
├── Lubega_Project_Presentation.pptx      ← fill in student names + reg numbers
├── nfe-modbus-energy-logger/
│   ├── src/
│   │   ├── meter_reader.py               ← ✅ done
│   │   ├── aggregator.py                 ← ✅ done
│   │   └── feature_engineering.py        ← ❌ Dennis writes (Step 2)
│   ├── detect.py                         ← ❌ Dennis writes (Step 3)
│   ├── systemd/
│   │   ├── meter.service                 ← ✅ done (running on Pi)
│   │   └── theft-detector.service        ← ❌ Dennis writes (Step 4)
│   ├── model/
│   │   ├── theft_detector.pkl            ← ✅ done (14.4 MB)
│   │   ├── scaler.pkl                    ← ✅ done
│   │   └── features.pkl                  ← ✅ done
│   └── design-docs/
│       ├── architecture.dsl              ← ✅ done
│       └── adr/                          ← ✅ done (ADR-001 to ADR-004)
└── app/
    └── app.py                            ← ❌ Hillary writes (Step 6)
```

---

## Notes

- `.env` on the Pi is **never committed to Git** — it contains the Neon password
- `NEON_DATABASE_URL` on Streamlit Cloud is set as a **secret** in the dashboard — not in code
- If Neon INSERT fails, `detect.py` logs the error and continues — a cloud outage does not stop theft detection
- The Streamlit app may sleep after 7 days of no browser visits (free tier) — this is fine, the Pi keeps writing to Neon regardless
