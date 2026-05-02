import os
import pickle
import time
import logging

import pandas as pd
import psycopg2
from dotenv import load_dotenv

from src.feature_engineering import engineer_features, verify_features

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

load_dotenv()

NEON_URL   = os.environ.get('NEON_DATABASE_URL')
THRESHOLD  = float(os.environ.get('THEFT_THRESHOLD', '0.5'))
CSV_PATH   = os.environ.get('CSV_PATH', 'data/current.csv')
METER_ID   = int(os.environ.get('METER_ID', '1'))
METER_NAME = os.environ.get('METER_NAME', 'Meter-01')

# Load model artefacts once at startup
with open('model/theft_detector.pkl', 'rb') as f:
    model = pickle.load(f)
with open('model/scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)
with open('model/features.pkl', 'rb') as f:
    features = pickle.load(f)

logging.info("Model loaded. Feature count: %d. Starting inference loop.", len(features))
if not NEON_URL:
    logging.warning("NEON_DATABASE_URL not set — alerts will be logged locally only.")

while True:
    try:
        df  = pd.read_csv(CSV_PATH)
        row = df.iloc[-1]                              # latest 15-min window

        feat_dict = engineer_features(row)
        verify_features(feat_dict)                     # guard: keys must match model

        X        = [feat_dict[f] for f in features]   # ordered exactly as trained
        X_scaled = scaler.transform([X])
        prob     = model.predict_proba(X_scaled)[0][1] # P(theft)
        pred     = 1 if prob >= THRESHOLD else 0

        logging.info("pred=%d  prob=%.4f  threshold=%.2f", pred, prob, THRESHOLD)

        if pred == 1:
            logging.warning("THEFT DETECTED — meter=%s  prob=%.4f", METER_NAME, prob)

            if NEON_URL:
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
                         float(row.i_l1), float(row.i_l2), float(row.i_l3),
                         float(row.v_l1), float(row.v_l2), float(row.v_l3),
                         float(row.p_total), float(row.pf_total), float(row.frequency))
                    )
                    conn.commit()
                    conn.close()
                    logging.info("Alert inserted into Neon.")
                except Exception as e:
                    logging.error("Neon insert failed: %s", e)  # never crash inference

    except Exception as e:
        logging.error("Inference error: %s", e)

    time.sleep(900)   # 15-min window matches aggregator cadence
