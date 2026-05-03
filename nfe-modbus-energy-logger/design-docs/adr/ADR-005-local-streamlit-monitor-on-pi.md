# ADR-005: Local Streamlit Live Monitor on Pi

## Status: Accepted

## Context

During commissioning, field engineers need to verify that the meter is reading correctly
before trusting the cloud dashboard. The Streamlit Cloud dashboard (`streamlit_app.py`)
only shows data after it has been written to Neon — there is a ~30s lag and it requires
internet access. On-site, a technician may have limited connectivity and needs immediate
visual feedback of raw sensor readings.

Additionally, the `theft-detector.service` + Neon path involves several hops (JSON file →
feature engineering → inference → psycopg2 → Neon → Streamlit Cloud), so a simpler
diagnostic tool that reads the JSON file directly is valuable for isolating failures
at each stage.

## Decision

Add `monitor.py` — a local Streamlit app that runs directly on the Pi (`nfetestpi2`).

- Reads `~/iot_meter/data/latest_reading_1.json` every 5 seconds
- Shows metric tiles: V_L1/L2/L3, I_L1/L2/L3, P_total, PF_total, frequency
- Shows rolling 60-reading line charts in three tabs: Current (A), Voltage (V), Power (kW)
- Launched manually via `streamlit run monitor.py` when on-site; not a systemd service
- Not deployed to Streamlit Cloud — purely a local diagnostic tool

## Consequences

**Better:**
- Field engineers can instantly verify meter readings without internet access
- Isolates meter-to-JSON path from the inference path — if the monitor shows data but
  the cloud dashboard shows nothing, the problem is in detect.py or Neon, not the meter
- Zero additional infrastructure — uses the same JSON file that detect.py already reads

**Worse:**
- Requires someone to SSH into the Pi and launch it manually (not always convenient)
- Adds a Streamlit dependency to the Pi environment (already present for dev use)
- Rolling history is lost on process restart — not a persistent store

**Watch for:**
- Port conflicts if run alongside other Streamlit processes on the Pi (default port 8501)
- The JSON path is hardcoded to `latest_reading_1.json` — needs updating for multi-meter setups
