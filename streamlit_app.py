import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Lubega — Theft Detection",
    page_icon="⚡",
    layout="wide",
)

# ── Connection ────────────────────────────────────────────────────────────────
conn = st.connection("neon", type="sql", url=st.secrets["NEON_DATABASE_URL"])

# ── Header ────────────────────────────────────────────────────────────────────
st.title("⚡ Lubega — Real-Time Electricity Theft Detection")
st.caption("UEDCL Distribution Monitoring · Powered by Raspberry Pi + ML")
st.divider()

# ── Safe query helper ─────────────────────────────────────────────────────────
def safe_query(sql, ttl=30):
    try:
        return conn.query(sql, ttl=ttl), None
    except Exception:
        return None, True

# ── Fetch data ────────────────────────────────────────────────────────────────
alerts_all, db_error_alerts   = safe_query("SELECT * FROM alerts ORDER BY detected_at DESC", ttl=30)
readings,   db_error_readings = safe_query("SELECT * FROM readings ORDER BY logged_at DESC LIMIT 96", ttl=30)

pi_offline = db_error_alerts or db_error_readings

# ── Pi offline banner ─────────────────────────────────────────────────────────
if pi_offline:
    st.warning(
        "🔌 **Raspberry Pi is offline or not transmitting data.**  \n"
        "The edge device may be powered off, disconnected from the network, "
        "or the detection service has stopped.  \n"
        "Data will resume automatically once the Pi reconnects.",
        icon="⚠️",
    )
    st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refreshes every 30s")
    st.stop()

# ── KPI row ──────────────────────────────────────────────────────────────────
alerts_24h = alerts_all[
    pd.to_datetime(alerts_all["detected_at"], utc=True)
    >= pd.Timestamp.now(tz="UTC") - timedelta(hours=24)
] if not alerts_all.empty else alerts_all

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Alerts", len(alerts_all))
k2.metric("Last 24 hrs", len(alerts_24h))
k3.metric(
    "Latest Probability",
    f"{alerts_all['probability'].iloc[0]:.2%}" if not alerts_all.empty else "—",
)
k4.metric(
    "Last Alert",
    pd.to_datetime(alerts_all["detected_at"].iloc[0]).strftime("%Y-%m-%d %H:%M")
    if not alerts_all.empty else "No alerts yet",
)

st.divider()

# ── Two columns: alerts + readings ───────────────────────────────────────────
col_left, col_right = st.columns([1.2, 1], gap="large")

with col_left:
    st.subheader("🚨 Theft Alerts")

    if alerts_all.empty:
        st.info("No alerts recorded yet. System is monitoring.")
    else:
        display = alerts_all[
            ["detected_at", "meter_name", "probability", "i_l1", "i_l2", "i_l3", "p_total"]
        ].copy()
        display.columns = ["Timestamp", "Meter", "Confidence", "I_L1 (A)", "I_L2 (A)", "I_L3 (A)", "P Total (kW)"]
        display["Confidence"] = display["Confidence"].map(lambda x: f"{x:.1%}")

        def row_colour(row):
            prob = float(row["Confidence"].strip("%")) / 100
            if prob >= 0.9:
                return ["background-color: #ffcccc"] * len(row)
            elif prob >= 0.7:
                return ["background-color: #fff3cc"] * len(row)
            return [""] * len(row)

        st.dataframe(
            display.style.apply(row_colour, axis=1),
            use_container_width=True,
            height=420,
        )

with col_right:
    st.subheader("📊 Live Readings")

    if readings is None or readings.empty:
        st.info("No readings yet. Waiting for Pi to push data.")
    else:
        readings["logged_at"] = pd.to_datetime(readings["logged_at"])
        readings = readings.sort_values("logged_at")

        tab1, tab2, tab3 = st.tabs(["Current (A)", "Voltage (V)", "Power (kW)"])

        with tab1:
            st.line_chart(
                readings.set_index("logged_at")[["i_l1", "i_l2", "i_l3"]],
                height=280,
            )
        with tab2:
            st.line_chart(
                readings.set_index("logged_at")[["v_l1", "v_l2", "v_l3"]],
                height=280,
            )
        with tab3:
            st.line_chart(
                readings.set_index("logged_at")[["p_total"]],
                height=280,
            )

st.divider()

# ── Alert trend chart ─────────────────────────────────────────────────────────
if not alerts_all.empty:
    st.subheader("📈 Alert Trend")
    alerts_all["date"] = pd.to_datetime(alerts_all["detected_at"]).dt.date
    trend = alerts_all.groupby("date").size().reset_index(name="alerts")
    st.bar_chart(trend.set_index("date"), height=200)

# ── Footer ────────────────────────────────────────────────────────────────────
st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Auto-refreshes every 30s")
