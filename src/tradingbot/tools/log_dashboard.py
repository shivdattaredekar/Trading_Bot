# streamlit run src/tradingbot/tools/log_dashboard.py
import streamlit as st
import pandas as pd

@st.cache_data
def load_sl(path="sl_trail_log.csv"):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

df = load_sl()
st.title("SL Trail Log")
if df.empty:
    st.write("No SL trail log found.")
else:
    st.dataframe(df)
    st.line_chart(df.pivot(index="timestamp", columns="order_id", values="new_sl").fillna(method="ffill"))
