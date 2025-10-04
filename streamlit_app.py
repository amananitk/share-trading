import streamlit as st
from src.screener import screen_once

st.set_page_config(page_title="15m NIFTY Screener", layout="wide")
st.title("15-minute NIFTY Screener (RSI/MACD/OBV/VO)")

results = screen_once()
st.write(f"Found {len(results)} matches")
if results:
    st.dataframe(results)
else:
    st.info("No matches right now. Try during market hours or adjust strategy thresholds.")
