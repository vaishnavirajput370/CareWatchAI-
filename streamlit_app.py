import streamlit as st
from snowflake.snowpark.context import get_active_session

st.title("CareWatch AI – Public Health & Inventory Guardian")
session = get_active_session()

# ---------- ASK CAREWATCH (SIMULATED VOICE) ----------
st.subheader("💬 CareWatch Copilot")

if "messages" not in st.session_state:
    st.session_state.messages = []

user_msg = st.chat_input("Ask CareWatch about disease or inventory...")

if user_msg:
    st.session_state.messages.append({"role": "user", "content": user_msg})

    q = user_msg.lower()

    if "malaria" in q or "disease" in q:
        df = session.sql("""
            SELECT disease, region FROM health_anomalies
            WHERE is_spike='YES' LIMIT 1
        """).collect()

        reply = f"{df[0]['DISEASE']} cases spiked in {df[0]['REGION']} region." if df else "No disease spikes today."

    elif "stock" in q or "inventory" in q:
        df = session.sql("""
            SELECT item, hospital FROM inventory_health
            WHERE risk_level='CRITICAL' LIMIT 1
        """).collect()

        reply = f"{df[0]['ITEM']} stock is critically low at {df[0]['HOSPITAL']}." if df else "All inventory looks healthy."

    else:
        reply = "Try asking about disease spikes or inventory stock levels."

    st.session_state.messages.append({"role": "assistant", "content": reply})

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])


# ---------- HEALTH RISK SCORE ----------
risk = session.sql("SELECT COUNT(*)*30 AS score FROM health_anomalies WHERE is_spike='YES'").collect()[0]['SCORE']
st.metric("Health Risk Score", f"{risk} / 100")

# ---------- BUTTON: ANY DISEASE SPIKE ----------
if st.button("Any Disease Spike?"):
    df = session.sql("""
        SELECT disease, region FROM health_anomalies
        WHERE is_spike='YES' LIMIT 1
    """).collect()
    if df:
        st.error(f"{df[0]['DISEASE']} cases spiked in {df[0]['REGION']} region.")
    else:
        st.success("No disease spikes.")

# ---------- INVENTORY HEAT-MAP ----------
st.subheader("Inventory Heat-Map")

inv = session.sql("""
    SELECT hospital, item, stock_left, risk_level
    FROM inventory_health
""").to_pandas()

def highlight(row):
    if row["RISK_LEVEL"] == "CRITICAL":
        return ["background-color: #ff4d4d"]*len(row)
    elif row["RISK_LEVEL"] == "WARNING":
        return ["background-color: #ffd966"]*len(row)
    else:
        return ["background-color: #9fff9f"]*len(row)

st.dataframe(inv.style.apply(highlight, axis=1))

# ---------- DATA QUALITY CHECK ----------
if st.button("Is Data Quality OK?"):
    df = session.sql("""
        SELECT COALESCE(SUM(missing_fields), 0) AS total_missing
        FROM public_health_visits
    """).collect()

    if df and df[0]["TOTAL_MISSING"] > 0:
        st.error(f"Warning: {df[0]['TOTAL_MISSING']} missing values found in health records.")
    else:
        st.success("All health records look clean.")

        
# ---------- FIND MISSING FIELDS ----------
if st.button("Where is data missing?"):
    df = session.sql("""
        SELECT visit_date, region, disease, missing_columns
        FROM public_health_visits
        WHERE missing_fields > 0
    """).to_pandas()

    if not df.empty:
        st.error("Missing data found in these records:")
        st.dataframe(df)
    else:
        st.success("No missing fields found in any record.")


# ---------- EXPORT REORDER LIST ----------
if st.button("Export Reorder List"):
    df = session.sql("""
        SELECT hospital, item, stock_left
        FROM inventory_health
        WHERE risk_level='CRITICAL'
    """).to_pandas()
    st.download_button("Download CSV", df.to_csv(index=False), "reorder_list.csv")

# ---------- VOICE MODE PREVIEW ----------
if st.button("🔊 Voice Alert for Critical Items"):
    df = session.sql("""
        SELECT hospital, item
        FROM inventory_health
        WHERE risk_level='CRITICAL' LIMIT 1
    """).collect()
    if df:
        st.error(f"Alert! {df[0]['ITEM']} stock is critically low at {df[0]['HOSPITAL']} hospital.")
        st.info("🎤 Voice Mode Enabled – This alert is spoken in the browser/mobile version.")
    else:
        st.success("All stocks are safe today.")
