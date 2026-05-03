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

## Important: Training Data vs. Production Data

The model was trained on **raw 10-second poll rows** (one row per Modbus read — see `docs/*.csv`).  
But `meter.service` in production only writes **15-minute aggregated rows** to CSV.

Feeding detect.py a 15-minute average would break the model — it has never seen averaged data.  
A bypass halfway through a 15-min window dilutes `I_L1` from 0 to ~0.3 A → the `I_L1_zero` flag never fires.

**The fix (Option A — no retraining needed):**  
Add 3 lines to `main.py` so it writes a `data/latest_reading.json` file after every raw poll (overwriting it each time). detect.py reads this file every 10 seconds — same format, same distribution the model was trained on.

---

## What's Left — Chronological Order

### STEP 1 — Hillary: Set up Neon PostgreSQL *(~30 min)* ✅ DONE
> **Neon project `lubega-production` is live. Schema created. URL sent to Dennis.**

1. ~~Go to [neon.tech](https://neon.tech) → sign in (same account as DSN project)~~
2. ~~Create a new project: **`lubega-production`**~~
3. ~~Open the SQL editor and run:~~

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

### STEP 2 — Dennis: Add `latest_reading.json` hook to `main.py` *(~15 min)* ✅ DONE
> **3-line JSON hook added to `src/main.py`. Overwrites `data/latest_reading_{meter_id}.json` every 10s.**

**File:** `nfe-modbus-energy-logger/src/main.py`

After the line `reading = reader.read(client)` succeeds (i.e., `reading is not None`), add these 3 lines to write the raw reading to a file that detect.py can consume:

```python
# After: reading = reader.read(client)
# Add immediately after the `if reading is None: continue` block:
import json, pathlib
pathlib.Path(cfg['logging']['base_dir']).mkdir(parents=True, exist_ok=True)
with open(f"{cfg['logging']['base_dir']}/latest_reading_{meter_id}.json", 'w') as _f:
    json.dump({'meter_id': meter_id, 'meter_name': components['name'], **reading}, _f)
```

This overwrites the file every 10 seconds with the freshest raw poll — detect.py reads it.  
Put the `import json, pathlib` at the top of main.py with the other imports, not inside the loop.

---

### STEP 3 — Dennis: Write `feature_engineering.py` *(~2 hrs)* ✅ DONE
> **`src/feature_engineering.py` live. 20-feature pipeline using uppercase keys. `verify_features()` guard added.**

**File:** `nfe-modbus-energy-logger/src/feature_engineering.py`

Takes one raw reading dict (from `latest_reading.json`) and returns all 20 features.  
**Keys are uppercase** — that is what `meter_reader.py` returns and what the model was trained on.

```python
def engineer_features(reading: dict) -> dict:
    I_L1 = reading['I_L1']
    I_L2 = reading['I_L2']
    I_L3 = reading['I_L3']
    V_L1 = reading['V_L1']
    V_L2 = reading['V_L2']
    V_L3 = reading['V_L3']
    I_total = I_L1 + I_L2 + I_L3

    return {
        # raw (9)
        'I_L1': I_L1, 'I_L2': I_L2, 'I_L3': I_L3,
        'V_L1': V_L1, 'V_L2': V_L2, 'V_L3': V_L3,
        'P_total':   reading['P_total'],
        'PF_total':  reading['PF_total'],
        'frequency': reading['frequency'],
        # engineered (11)
        'I_imbalance': max(I_L1,I_L2,I_L3) - min(I_L1,I_L2,I_L3),
        'V_imbalance': max(V_L1,V_L2,V_L3) - min(V_L1,V_L2,V_L3),
        'I_L1_zero':   1 if I_L1 < 0.01 else 0,
        'I_L2_zero':   1 if I_L2 < 0.01 else 0,
        'I_L3_zero':   1 if I_L3 < 0.01 else 0,
        'V_L1_zero':   1 if V_L1 < 10 else 0,
        'V_L2_zero':   1 if V_L2 < 10 else 0,
        'V_L3_zero':   1 if V_L3 < 10 else 0,
        'PF_zero':     1 if reading['PF_total'] < 0.05 else 0,
        'I_total':     I_total,
        'P_per_I':     reading['P_total'] / (I_total + 0.001),
    }
```

**Test it:** load any row from `docs/*.csv` using pandas, convert to dict, pass to `engineer_features()`, print output. All 20 keys must be present.

> **Critical:** Load `model/features.pkl` and verify your dict keys match that list exactly (case included) before proceeding to Step 4.

---

### STEP 4 — Dennis: Write `detect.py` *(~3 hrs)* ✅ DONE
> **`detect.py` live. INSERTs every reading into `readings` table + alert into `alerts` table if prob > 0.5. Uses `joblib.load` not pickle. Skips unchanged readings via `last_seen` guard.**

**File:** `nfe-modbus-energy-logger/detect.py`

Reads `latest_reading_{meter_id}.json` (written by main.py every 10s), runs inference on each raw poll — same data distribution the model was trained on.

```python
import os, json, pickle, time, logging
import psycopg2
from dotenv import load_dotenv
from src.feature_engineering import engineer_features

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

load_dotenv()
NEON_URL   = os.environ['NEON_DATABASE_URL']
THRESHOLD  = float(os.environ.get('THEFT_THRESHOLD', '0.5'))
DATA_DIR   = os.environ.get('DATA_DIR', 'data')
METER_ID   = int(os.environ.get('METER_ID', '1'))
METER_NAME = os.environ.get('METER_NAME', 'Meter-01')
POLL_INTERVAL = int(os.environ.get('POLL_INTERVAL', '10'))  # seconds, match meter poll

# Load model artefacts once at startup
with open('model/theft_detector.pkl', 'rb') as f: model    = pickle.load(f)
with open('model/scaler.pkl',         'rb') as f: scaler   = pickle.load(f)
with open('model/features.pkl',       'rb') as f: features = pickle.load(f)

logging.info(f"Model loaded. Watching {DATA_DIR}/latest_reading_{METER_ID}.json")

last_seen = None  # track file content to avoid re-running on same reading

while True:
    try:
        json_path = f"{DATA_DIR}/latest_reading_{METER_ID}.json"
        with open(json_path) as f:
            reading = json.load(f)

        # Skip if same reading as last cycle
        reading_key = str(reading)
        if reading_key == last_seen:
            time.sleep(POLL_INTERVAL)
            continue
        last_seen = reading_key

        # Engineer features and run inference
        feat_dict = engineer_features(reading)
        X         = [feat_dict[f] for f in features]   # order must match training
        X_scaled  = scaler.transform([X])
        prob      = model.predict_proba(X_scaled)[0][1]  # P(theft)
        pred      = 1 if prob >= THRESHOLD else 0

        logging.info(f"pred={pred}  prob={prob:.4f}  "
                     f"I_L1={reading['I_L1']}  I_L2={reading['I_L2']}  I_L3={reading['I_L3']}")

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
                     reading['I_L1'], reading['I_L2'], reading['I_L3'],
                     reading['V_L1'], reading['V_L2'], reading['V_L3'],
                     reading['P_total'], reading['PF_total'], reading['frequency'])
                )
                conn.commit()
                conn.close()
                logging.warning(f"THEFT ALERT inserted — prob={prob:.4f}")
            except Exception as e:
                logging.error(f"Neon insert failed: {e}")  # log but don't crash

    except FileNotFoundError:
        logging.warning(f"Waiting for {json_path} — is meter.service running?")
    except Exception as e:
        logging.error(f"Inference error: {e}")

    time.sleep(POLL_INTERVAL)
```

**Create `.env` on the Pi** (never commit this file):
```
NEON_DATABASE_URL=postgresql://neondb_owner:<password>@<endpoint>.neon.tech/neondb?sslmode=require
THEFT_THRESHOLD=0.5
DATA_DIR=/home/pi/nfe-modbus-energy-logger/data
METER_ID=1
METER_NAME=Meter-01
POLL_INTERVAL=10
```

---

### STEP 5 — Dennis: Write `theft-detector.service` *(~30 min)* ✅ DONE
> **Service deployed and active on nfetestpi2. User=nfetestpi2, WorkingDirectory=/home/nfetestpi2/nfe-modbus-energy-logger.**

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

### STEP 6 — Dennis: End-to-end test on Pi *(~1 hr)* ✅ DONE
> **System fully live. `readings` + `alerts` tables both populating in Neon. Dashboard showing 10+ alerts at ~94% probability. Known issue: I_L2=0.000A is causing every reading to fire as theft (false positive) — field investigation pending.**

1. Confirm `meter.service` is running and writing `latest_reading_1.json`:
   ```bash
   watch -n 2 cat data/latest_reading_1.json
   ```
2. Start `theft-detector.service` and watch logs:
   ```bash
   sudo journalctl -fu theft-detector
   ```
3. **Simulate a theft** — temporarily edit `latest_reading_1.json`, set `I_L1` to `0.0`. The next detect.py cycle (within 10 seconds) should fire and INSERT into Neon.
4. Check the Neon SQL editor — confirm a row appeared in the `alerts` table.
5. Restore `latest_reading_1.json` to normal (meter.service will overwrite it automatically within 10s anyway).
6. **Tell Hillary:** "Neon is receiving alerts" — that is his go signal to deploy the dashboard.

---

### STEP 7 — Hillary: Write `streamlit_app.py` *(~3 hrs)* ✅ DONE
> Live at `lubegacode-tbn4wlkpdrzqhjahqssdvf.streamlit.app`. Reads from Neon. Showing "No alerts yet — system monitoring."

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

### STEP 8 — Hillary: Deploy to Streamlit Community Cloud *(~30 min)* ✅ DONE

Dashboard is **LIVE** at: `lubegacode-tbn4wlkpdrzqhjahqssdvf.streamlit.app`

- Repo: `RincolTech-Solutions-ltd/Lubega_code`, branch `main`, file `streamlit_app.py`
- `NEON_DATABASE_URL` secret configured in Streamlit Cloud secrets
- App shows KPIs, colour-coded alerts table, live readings tabs (Current/Voltage/Power), alert trend chart

---

### STEP 9 — Both: Full end-to-end test *(~1 hr together)* ✅ DONE

- Dashboard live at `lubegacode-tbn4wlkpdrzqhjahqssdvf.streamlit.app`
- Pi inference running — alerts and readings flowing into Neon in real time
- **System is fully live as of 2026-05-04**
- Next: investigate I_L2=0.000A false positive (wiring or no load on L2?)

---

## Dependency Map

```
Hillary → Step 1 (Neon setup) ──────────────────────────────────────────────────────────┐
                 │ sends NEON_DATABASE_URL to Dennis                                     │
                 ↓                                                                       ↓
Dennis  → Step 2 (main.py hook → latest_reading.json)          Hillary → Step 7 (app.py)
            → Step 3 (feature_engineering.py)                             → Step 8 (deploy)
              → Step 4 (detect.py)                                                       │
                → Step 5 (systemd service)                                               │
                  → Step 6 (Pi test) ─── "alerts flowing" signal ───────────────────────┘
                                                                                         ↓
                                                                     Both → Step 9 (end-to-end test)
```

**Estimated time:** one focused weekend.

---

## Key Files Reference

```
Lubega_code/  (repo: RincolTech-Solutions-ltd/Lubega_code, branch: main)
├── WORK_PLAN.md                          ← you are here
├── streamlit_app.py                      ← ✅ LIVE at lubegacode-tbn4wlkpdrzqhjahqssdvf.streamlit.app
├── requirements.txt                      ← ✅ done (streamlit, pandas, psycopg2-binary, sqlalchemy)
├── Lubega_Project_Report.docx            ← fill in student names + reg numbers (updated 2026-05-03)
├── Lubega_Project_Presentation.pptx      ← fill in student names + reg numbers (updated 2026-05-03)
├── monitor.py                            ← ✅ local Pi diagnostic dashboard (Streamlit, 5s refresh, 60-reading history)
├── nfe-modbus-energy-logger/
│   ├── src/
│   │   ├── meter_reader.py               ← ✅ done
│   │   ├── aggregator.py                 ← ✅ done
│   │   ├── main.py                       ← ✅ done (JSON hook at line 188-190)
│   │   └── feature_engineering.py        ← ✅ done (20 features, uppercase keys, verify_features guard)
│   ├── detect.py                         ← ✅ done (JSON polling, reads+alerts to Neon every 10s)
│   ├── systemd/
│   │   ├── meter.service                 ← ✅ done (running on nfetestpi2)
│   │   └── theft-detector.service        ← ✅ done (running on nfetestpi2)
│   ├── model/
│   │   ├── theft_detector.pkl            ← ✅ done (14.4 MB, VotingClassifier RF+XGB)
│   │   ├── scaler.pkl                    ← ✅ done
│   │   └── features.pkl                  ← ✅ done
│   └── design-docs/
│       ├── architecture.dsl              ← ✅ updated 2026-05-04 (v4.0.0, all components live)
│       └── adr/                          ← ✅ done (ADR-001 to ADR-004; ADR-005 pending for monitor.py)
└── app/
    └── app.py                            ← ✅ same content as streamlit_app.py (Hillary's reference copy)
```

---

## Notes

- `.env` on the Pi is **never committed to Git** — it contains the Neon password
- `NEON_DATABASE_URL` on Streamlit Cloud is set as a **secret** in the dashboard — not in code
- If Neon INSERT fails, `detect.py` logs the error and continues — a cloud outage does not stop theft detection
- The Streamlit app may sleep after 7 days of no browser visits (free tier) — this is fine, the Pi keeps writing to Neon regardless
