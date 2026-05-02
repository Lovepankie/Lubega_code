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
        st.line_chart(
            readings.set_index("logged_at")[["i_l1", "i_l2", "i_l3"]],
            height=300
        )
