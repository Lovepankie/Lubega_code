import json
import time
from collections import deque
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Meter Live Monitor", layout="wide")
st.title("⚡ Live Meter Monitor")

JSON_PATH   = Path.home() / "iot_meter" / "data" / "latest_reading_1.json"
MAX_HISTORY = 60  # keep last 60 readings (~10 min at 10s poll)

if "history" not in st.session_state:
    st.session_state.history = deque(maxlen=MAX_HISTORY)

placeholder = st.empty()

while True:
    try:
        data = json.loads(JSON_PATH.read_text())
        data["time"] = time.strftime("%H:%M:%S")
        st.session_state.history.append(data)

        df = pd.DataFrame(st.session_state.history)

        with placeholder.container():
            st.caption(f"Last read: {data['time']} · auto-refreshes every 5s · {len(df)} samples")

            # ── Metrics row ──────────────────────────────────────────────
            c1, c2, c3 = st.columns(3)
            c1.metric("V L1 (V)",       f"{data.get('V_L1', 0):.1f}")
            c2.metric("V L2 (V)",       f"{data.get('V_L2', 0):.1f}")
            c3.metric("V L3 (V)",       f"{data.get('V_L3', 0):.1f}")

            c4, c5, c6 = st.columns(3)
            c4.metric("I L1 (A)",       f"{data.get('I_L1', 0):.3f}")
            c5.metric("I L2 (A)",       f"{data.get('I_L2', 0):.3f}")
            c6.metric("I L3 (A)",       f"{data.get('I_L3', 0):.3f}")

            c7, c8, c9 = st.columns(3)
            c7.metric("P Total (kW)",   f"{data.get('P_total', 0):.3f}")
            c8.metric("PF Total",       f"{data.get('PF_total', 0):.3f}")
            c9.metric("Frequency (Hz)", f"{data.get('frequency', 0):.2f}")

            st.divider()

            # ── Charts ───────────────────────────────────────────────────
            if len(df) > 1:
                tab1, tab2, tab3 = st.tabs(["Current (A)", "Voltage (V)", "Power (kW)"])

                with tab1:
                    st.line_chart(df.set_index("time")[["I_L1", "I_L2", "I_L3"]], height=250)

                with tab2:
                    st.line_chart(df.set_index("time")[["V_L1", "V_L2", "V_L3"]], height=250)

                with tab3:
                    st.line_chart(df.set_index("time")[["P_total"]], height=250)
            else:
                st.info("Collecting data for charts… check back in a few seconds.")

    except FileNotFoundError:
        placeholder.warning(f"Waiting for {JSON_PATH} — is meter.service running?")
    except Exception as e:
        placeholder.error(f"Error: {e}")

    time.sleep(5)
