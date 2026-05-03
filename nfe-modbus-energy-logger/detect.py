import os
import json
import time
import logging

import joblib
import psycopg2
from dotenv import load_dotenv

from src.feature_engineering import engineer_features, verify_features

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

load_dotenv()

NEON_URL      = os.environ.get('NEON_DATABASE_URL')
THRESHOLD     = float(os.environ.get('THEFT_THRESHOLD', '0.5'))
DATA_DIR      = os.environ.get('DATA_DIR', 'data')
METER_ID      = int(os.environ.get('METER_ID', '1'))
METER_NAME    = os.environ.get('METER_NAME', 'Meter-01')
POLL_INTERVAL = int(os.environ.get('POLL_INTERVAL', '10'))

# Load model artefacts once at startup
model    = joblib.load('model/theft_detector.pkl')
scaler   = joblib.load('model/scaler.pkl')
features = joblib.load('model/features.pkl')

logging.info("Model loaded. Feature count: %d. Watching %s/latest_reading_%d.json",
             len(features), DATA_DIR, METER_ID)
if not NEON_URL:
    logging.warning("NEON_DATABASE_URL not set — alerts will be logged locally only.")

last_seen = None  # avoid re-running inference on the same reading

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

        feat_dict = engineer_features(reading)
        verify_features(feat_dict)

        X        = [feat_dict[f] for f in features]
        X_scaled = scaler.transform([X])
        prob     = model.predict_proba(X_scaled)[0][1]
        pred     = 1 if prob >= THRESHOLD else 0

        logging.info("pred=%d  prob=%.4f  I_L1=%.3f  I_L2=%.3f  I_L3=%.3f",
                     pred, prob,
                     reading.get('I_L1', 0), reading.get('I_L2', 0), reading.get('I_L3', 0))

        if NEON_URL:
            try:
                conn = psycopg2.connect(NEON_URL)
                cur  = conn.cursor()

                # Always log every reading to the readings table
                cur.execute(
                    """INSERT INTO readings
                       (logged_at, meter_id, meter_name,
                        v_l1, v_l2, v_l3, i_l1, i_l2, i_l3,
                        p_total, pf_total, frequency)
                       VALUES (now(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (METER_ID, METER_NAME,
                     float(reading.get('V_L1', 0)), float(reading.get('V_L2', 0)), float(reading.get('V_L3', 0)),
                     float(reading.get('I_L1', 0)), float(reading.get('I_L2', 0)), float(reading.get('I_L3', 0)),
                     float(reading.get('P_total', 0)), float(reading.get('PF_total', 0)), float(reading.get('frequency', 0)))
                )

                if pred == 1:
                    logging.warning("THEFT DETECTED — meter=%s  prob=%.4f", METER_NAME, prob)
                    cur.execute(
                        """INSERT INTO alerts
                           (meter_id, meter_name, prediction, probability,
                            i_l1, i_l2, i_l3, v_l1, v_l2, v_l3,
                            p_total, pf_total, frequency)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (METER_ID, METER_NAME, int(pred), float(prob),
                         float(reading.get('I_L1', 0)), float(reading.get('I_L2', 0)), float(reading.get('I_L3', 0)),
                         float(reading.get('V_L1', 0)), float(reading.get('V_L2', 0)), float(reading.get('V_L3', 0)),
                         float(reading.get('P_total', 0)), float(reading.get('PF_total', 0)), float(reading.get('frequency', 0)))
                    )
                    logging.warning("THEFT ALERT inserted into Neon.")

                conn.commit()
                conn.close()
            except Exception as e:
                logging.error("Neon insert failed: %s", e)

    except FileNotFoundError:
        logging.warning("Waiting for %s/latest_reading_%d.json — is meter.service running?",
                        DATA_DIR, METER_ID)
    except Exception as e:
        logging.error("Inference error: %s", e)

    time.sleep(POLL_INTERVAL)
