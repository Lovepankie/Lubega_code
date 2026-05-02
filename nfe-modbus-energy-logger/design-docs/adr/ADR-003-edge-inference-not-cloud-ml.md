# ADR-003: Edge Inference on Pi — Model Runs on Device, Not Cloud

## Status
Accepted

## Context
Once the ML model is trained, it must run somewhere to produce real-time theft alerts. Two architectures were evaluated:

**Option A — Cloud inference:** Pi streams raw readings to a cloud server via MQTT or HTTP. Cloud server runs the model, returns a prediction, stores the alert. Pi is "dumb".

**Option B — Edge inference:** Model (.pkl files) are deployed onto the Pi. detect.py runs locally. Pi produces alerts itself. Cloud only receives the alert outcome.

The Pi is in a field location with intermittent connectivity (ZeroTier VPN, WiFi). Uganda's power grid has frequent outages, which also affects WiFi routers.

## Decision
Edge inference on the Raspberry Pi. The three model artefacts (`theft_detector.pkl`, `scaler.pkl`, `features.pkl`) are deployed to the Pi alongside the application code. `detect.py` loads them at startup and runs `predict_proba()` locally.

Only alert records (not raw readings) are pushed to Supabase — a small HTTP POST of a few hundred bytes per alert event (rare, not every 15 minutes).

## Consequences

**Better:**
- Inference works even with zero internet connectivity — alert is logged locally regardless
- Inference latency: <2 ms (in-RAM sklearn call) — no network roundtrip
- Minimal cloud dependency — system degrades gracefully to local-only logging if Supabase is unreachable
- Model update is a simple `scp model/*.pkl` deployment — no cloud ML infrastructure to maintain
- Privacy: raw electrical readings never leave the site

**Worse:**
- Model artefacts (14.4 MB) must be deployed to every Pi — SCP step in deployment pipeline
- Pi RAM usage increases by ~50 MB when model is loaded (within Pi 4's 4 GB headroom)
- Cannot hot-swap the model without restarting `theft-detector.service`
- If the Pi's SD card fails, the model must be re-deployed from the dev machine

**Design note:** The cloud (Supabase + Streamlit) is display-only infrastructure. It can go offline without affecting theft detection. The Pi is the authoritative detection node.
