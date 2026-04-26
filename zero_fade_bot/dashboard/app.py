from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

API_URL = st.sidebar.text_input("API URL", value="http://localhost:8000")

st.title("Zero-Fade Trading Dashboard")

st.header("Bot Monitoring")
if st.button("Refresh status"):
    response = requests.get(f"{API_URL}/bot/status", timeout=10)
    st.json(response.json())

col1, col2 = st.columns(2)
with col1:
    if st.button("Start Bot"):
        requests.post(f"{API_URL}/bot/start", json={}, timeout=10)
with col2:
    if st.button("Stop Bot"):
        requests.post(f"{API_URL}/bot/stop", timeout=10)

st.header("Backtesting")
uploaded = st.file_uploader("Upload ForexSB CSV", type=["csv"])
symbol = st.text_input("Symbol", value="EURUSD")
initial_balance = st.number_input("Initial balance", value=10.0)
lot_size = st.number_input("Lot size", value=0.01, step=0.01, min_value=0.01)
risk_pct = st.number_input("Risk % per trade", value=20.0, min_value=0.1, max_value=100.0)

if st.button("Run Backtest") and uploaded is not None:
    files = {"csv_file": (uploaded.name, uploaded.getvalue(), "text/csv")}
    payload = {
        "symbol": symbol,
        "initial_balance": initial_balance,
        "lot_size": lot_size,
        "risk_percent_per_trade": risk_pct,
        "spread_pips": 1.2,
        "slippage_pips": 0.5,
        "execution_delay_bars": 1,
    }
    response = requests.post(f"{API_URL}/backtest/run", params=payload, files=files, timeout=120)
    data = response.json()

    st.subheader("Metrics")
    st.json(
        {
            "final_balance": data["final_balance"],
            "net_pnl": data["net_pnl"],
            "max_drawdown_pct": data["max_drawdown_pct"],
            "win_rate_pct": data["win_rate_pct"],
            "avg_rr": data["avg_rr"],
        }
    )

    st.subheader("Equity Curve")
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(data["equity_curve"])
    ax.set_xlabel("Step")
    ax.set_ylabel("Equity")
    st.pyplot(fig)

    st.subheader("Trade Distribution")
    trades = pd.DataFrame(data["trades"])
    if not trades.empty:
        st.bar_chart(trades["pnl"])
        st.dataframe(trades)
