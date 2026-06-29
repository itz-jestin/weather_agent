import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# ------------------------
# Page Config
# ------------------------

st.set_page_config(
    page_title="Weather Trading Agent",
    page_icon="🌦",
    layout="wide"
)

# Auto refresh every 10 seconds
st_autorefresh(interval=10000, key="refresh")

# ------------------------
# Dummy Data (replace later)
# ------------------------

weather = pd.DataFrame([
    ["Delhi", 36, 28, 82, 15, "YES"],
    ["Mumbai", 31, 27, 15, 10, "NO"],
    ["Bangalore", 29, 21, 60, 8, "YES"],
    ["Chennai", 35, 29, 20, 14, "NO"],
], columns=[
    "City",
    "Max Temp",
    "Min Temp",
    "Rain %",
    "Wind km/h",
    "Rain?"
])

markets = pd.DataFrame([
    ["Rain in Delhi?", 0.73, 0.90, "+0.17", "BUY YES"],
    ["Rain in Mumbai?", 0.44, 0.20, "-0.24", "BUY NO"],
    ["Rain in Chennai?", 0.52, 0.50, "+0.02", "SKIP"],
], columns=[
    "Question",
    "Market Prob",
    "Model Prob",
    "Edge",
    "Recommendation"
])

history = pd.DataFrame({
    "Trade": list(range(1, 11)),
    "Bankroll": [1000, 1015, 1040, 1030, 1075, 1090, 1120, 1150, 1170, 1205]
})

# ------------------------
# Title
# ------------------------

st.title("🌦 Weather Prediction Trading Agent")

st.caption("Live Weather + Prediction Markets + Paper Trading")

# ------------------------
# Statistics
# ------------------------

c1, c2, c3, c4 = st.columns(4)

c1.metric("💰 Bankroll", "$1205")
c2.metric("📈 ROI", "+20.5%")
c3.metric("📊 Trades", "10")
c4.metric("🏆 Win Rate", "70%")

st.divider()

# ------------------------
# Weather
# ------------------------

st.subheader("🌤 Live Weather")

st.dataframe(weather, use_container_width=True)

st.divider()

# ------------------------
# Markets
# ------------------------

st.subheader("📊 Prediction Markets")

st.dataframe(markets, use_container_width=True)

st.divider()

# ------------------------
# Portfolio Chart
# ------------------------

st.subheader("📈 Portfolio Growth")

fig = px.line(
    history,
    x="Trade",
    y="Bankroll",
    markers=True,
    title="Portfolio Value"
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

# ------------------------
# Open Positions
# ------------------------

st.subheader("💼 Open Positions")

positions = pd.DataFrame([
    ["Delhi Rain", "YES", "$50", "OPEN"],
    ["Mumbai Rain", "NO", "$40", "OPEN"]
], columns=[
    "Market",
    "Side",
    "Stake",
    "Status"
])

st.dataframe(positions, use_container_width=True)

st.success("Dashboard refreshed every 10 seconds.")