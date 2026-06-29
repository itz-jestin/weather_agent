import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os

from trading.paper_trader import PaperTrader
from data.weather_fetcher import fetch_all_cities
from data.polymarket_fetcher import fetch_parsed_markets

st.set_page_config(
    page_title="Weather Prediction Trading Agent",
    page_icon="🌦",
    layout="wide"
)

st.title("🌦 Weather Prediction Trading Agent")
st.caption("CrowdWisdomTrading Internship Project")

trader = PaperTrader()
stats = trader.stats()

# ---------------- Sidebar ----------------

st.sidebar.header("Portfolio")

st.sidebar.metric(
    "Portfolio Value",
    f"${stats['portfolio_value']:.2f}"
)

st.sidebar.metric(
    "ROI",
    f"{stats['roi_pct']:.2f}%"
)

st.sidebar.metric(
    "Open Positions",
    stats["open_positions"]
)

st.sidebar.metric(
    "Closed Trades",
    stats["closed_trades"]
)

if st.sidebar.button("Refresh"):
    st.rerun()

# ---------------- Top Metrics ----------------

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Cash", f"${stats['cash']:.2f}")

with c2:
    st.metric("Portfolio", f"${stats['portfolio_value']:.2f}")

with c3:
    st.metric("ROI", f"{stats['roi_pct']:.2f}%")

with c4:
    st.metric("Win Rate", f"{stats['win_rate']:.1f}%")

st.divider()

# ---------------- Weather ----------------

st.header("🌤 Live Weather")

try:
    weather = fetch_all_cities()

    if weather:
        weather_df = pd.DataFrame(weather)

        show_cols = [
            "city",
            "max_temp_c",
            "min_temp_c",
            "total_precip_mm",
            "max_wind_kmh",
            "will_rain"
        ]

        weather_df = weather_df[show_cols]

        st.dataframe(
            weather_df,
            use_container_width=True
        )
    else:
        st.info("No weather data available.")

except Exception as e:
    st.error(str(e))

st.divider()

# ---------------- Markets ----------------

st.header("📊 Prediction Markets")

try:
    markets = fetch_parsed_markets()

    if markets:
        market_df = pd.DataFrame(markets)

        cols = []

        for c in [
            "question",
            "matched_city",
            "yes_prob",
            "volume",
            "liquidity"
        ]:
            if c in market_df.columns:
                cols.append(c)

        st.dataframe(
            market_df[cols],
            use_container_width=True
        )

    else:
        st.info("No markets available.")

except Exception as e:
    st.error(str(e))

st.divider()

# ---------------- Open Positions ----------------

st.header("💼 Open Positions")

if trader.positions:

    positions = pd.DataFrame(trader.positions)

    st.dataframe(
        positions,
        use_container_width=True
    )

else:
    st.success("No open positions.")

st.divider()

# ---------------- Trade History ----------------

st.header("📜 Trade History")

if trader.history:

    history = pd.DataFrame(trader.history)

    st.dataframe(
        history,
        use_container_width=True
    )

    csv = history.to_csv(index=False).encode()

    st.download_button(
        "Download Trade History",
        csv,
        file_name="trade_history.csv",
        mime="text/csv"
    )

else:
    st.info("No trades settled yet.")

st.divider()

# ---------------- Portfolio Chart ----------------

st.header("📈 Portfolio Performance")

if trader.history:

    bankroll = trader.starting

    values = [bankroll]

    for trade in trader.history:
        bankroll += trade["pnl_usd"]
        values.append(bankroll)

    fig, ax = plt.subplots(figsize=(10,4))

    ax.plot(values, linewidth=3)

    ax.set_xlabel("Trades")

    ax.set_ylabel("Portfolio Value")

    ax.grid(True)

    st.pyplot(fig)

else:
    st.info("Portfolio chart will appear after completed trades.")

st.divider()

st.success("Dashboard Running Successfully ✅")