from __future__ import annotations

import json

import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st
# Note: Removed stylable_container - using native Streamlit components

API_URL = st.sidebar.text_input("API URL", value="http://localhost:8000")

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);
    }
    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    div[data-testid="stMetricLabel"] {
        color: #a0a0b0;
    }
    div[data-testid="stMetricValue"] {
        color: #00d4ff;
    }
    .title-text {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #00d4ff, #00ff88);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .subtitle-text {
        color: #8888aa;
        font-size: 1rem;
    }
    .section-header {
        color: #00d4ff;
        border-bottom: 2px solid #00d4ff;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    .success-box {
        background: rgba(0, 255, 136, 0.1);
        border: 1px solid #00ff88;
        border-radius: 10px;
        padding: 15px;
    }
    .error-box {
        background: rgba(255, 77, 77, 0.1);
        border: 1px solid #ff4d4d;
        border-radius: 10px;
        padding: 15px;
    }
    .info-box {
        background: rgba(0, 212, 255, 0.1);
        border: 1px solid #00d4ff;
        border-radius: 10px;
        padding: 15px;
    }
    div.stButton > button {
        background: linear-gradient(90deg, #00d4ff, #00ff88);
        border: none;
        border-radius: 8px;
        color: #0f0f23;
        font-weight: bold;
        padding: 10px 20px;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
    }
    .uploadedFile {
        border: 2px dashed #00d4ff;
        border-radius: 10px;
        padding: 20px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Title
st.markdown(
    '<p class="title-text">🚀 Zero-Fade Trading Dashboard</p>', unsafe_allow_html=True
)
st.markdown(
    '<p class="subtitle-text">Smart Money Concepts Trading Bot</p>',
    unsafe_allow_html=True,
)
st.markdown("---")


def _show_api_error(response: requests.Response) -> None:
    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": response.text}
    st.markdown(
        f'<div class="error-box">❌ API request failed with status {response.status_code}</div>',
        unsafe_allow_html=True,
    )
    with st.expander("Error Details"):
        st.json(payload)


# Create tabs for different sections
tab1, tab2, tab3 = st.tabs(["🤖 Bot Control", "📊 Backtesting", "📈 Analytics"])

with tab1:
    st.markdown('<p class="section-header">Bot Monitoring</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("▶️ Start Bot", use_container_width=True):
            response = requests.post(f"{API_URL}/bot/start", json={}, timeout=10)
            if response.ok:
                st.markdown(
                    '<div class="success-box">✅ Bot start request sent!</div>',
                    unsafe_allow_html=True,
                )
            else:
                _show_api_error(response)

    with col2:
        if st.button("⏹️ Stop Bot", use_container_width=True):
            response = requests.post(f"{API_URL}/bot/stop", timeout=10)
            if response.ok:
                st.markdown(
                    '<div class="success-box">✅ Bot stop request sent!</div>',
                    unsafe_allow_html=True,
                )
            else:
                _show_api_error(response)

    with col3:
        if st.button("🔄 Refresh Status", use_container_width=True):
            response = requests.get(f"{API_URL}/bot/status", timeout=10)
            if response.ok:
                status = response.json()
                st.markdown(
                    '<div class="info-box">📡 Status retrieved!</div>',
                    unsafe_allow_html=True,
                )
                st.json(status)
            else:
                _show_api_error(response)

with tab2:
    st.markdown('<p class="section-header">Backtesting</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        symbol = st.text_input("📌 Symbol", value="EURUSD")
        initial_balance = st.number_input(
            "💰 Initial Balance", value=10000.0, step=1000.0
        )
        # Date range for backtest
        st.markdown("**📅 Date Range (Optional)**")
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input("Start Date", value=None)
        with col_date2:
            end_date = st.date_input("End Date", value=None)

    with col2:
        lot_size = st.number_input("📏 Lot Size", value=0.01, step=0.01, min_value=0.01)
        risk_pct = st.number_input(
            "⚠️ Risk %", value=20.0, min_value=0.1, max_value=100.0
        )
        # Timeframe selection
        st.markdown("**⏱️ Timeframe**")
        timeframe = st.selectbox(
            "Select Data",
            options=["M5", "M15", "M30", "H1", "H4", "D1"],
            index=1,
            help="Select the timeframe for backtesting",
        )

    uploaded = st.file_uploader(
        "📁 Upload ForexSB CSV File",
        type=["csv"],
        help="Upload a tab-delimited CSV file from ForexSB",
    )

    if uploaded is not None:
        st.markdown(
            f'<div class="info-box">📄 File loaded: {uploaded.name}</div>',
            unsafe_allow_html=True,
        )

    # Option to use local data files
    st.markdown("**Or select from data folder:**")
    data_files = ["GBPUSD_M5.csv", "GBPUSD_M15.csv", "GBPUSD_M30.csv", "GBPUSD_H1.csv", "GBPUSD_H4.csv", "GBPUSD_D1.csv"]
    selected_file = st.selectbox("Select CSV File", options=data_files, index=1)

    # Determine which file to use
    use_uploaded = uploaded is not None
    csv_filename = uploaded.name if use_uploaded else selected_file

    run_backtest = st.button(
        "🚀 Run Backtest", use_container_width=True, disabled=not (uploaded is not None or selected_file)
    )

    if run_backtest and (uploaded is not None or selected_file):
        # Prepare payload with date range
        payload = {
            "symbol": symbol,
            "initial_balance": initial_balance,
            "lot_size": lot_size,
            "risk_percent_per_trade": risk_pct,
            "spread_pips": 1.2,
            "slippage_pips": 0.5,
            "execution_delay_bars": 1,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        }

        # Progress bar for long-running backtest
        progress_bar = st.progress(0)
        status_text = st.empty()

        if use_uploaded:
            # Use uploaded file
            files = {"csv_file": (uploaded.name, uploaded.getvalue(), "text/csv")}
            status_text.markdown("⏳ Starting backtest with uploaded file...")
            response = requests.post(
                f"{API_URL}/backtest/run",
                data={"config": json.dumps(payload)},
                files=files,
                timeout=300,  # 5 minutes timeout
            )
        else:
            # Use local file from data folder
            status_text.markdown(f"⏳ Starting backtest with {selected_file}...")
            # Read the local file and send it
            with open(f"data/{selected_file}", "rb") as f:
                file_content = f.read()
            files = {"csv_file": (selected_file, file_content, "text/csv")}
            response = requests.post(
                f"{API_URL}/backtest/run",
                data={"config": json.dumps(payload)},
                files=files,
                timeout=300,  # 5 minutes timeout
            )

        # Progress bar for long-running backtest
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.markdown("⏳ Starting backtest...")
            response = requests.post(
                f"{API_URL}/backtest/run",
                data={"config": json.dumps(payload)},
                files=files,
                timeout=300,  # 5 minutes timeout
            )
            progress_bar.progress(100)
        except requests.exceptions.ReadTimeout:
            progress_bar.empty()
            st.warning(
                "⏱️ Backtest is taking longer than expected. The server may still be processing. Please check the terminal for progress."
            )
            st.info(
                "💡 Tip: For large datasets, try with a smaller CSV file first to test."
            )
            st.stop()

        if not response.ok:
            _show_api_error(response)
            st.stop()

        data = response.json()

        required_keys = {
            "final_balance",
            "net_pnl",
            "max_drawdown_pct",
            "win_rate_pct",
            "avg_rr",
            "equity_curve",
            "trades",
        }
        missing_keys = sorted(required_keys.difference(data.keys()))
        if missing_keys:
            st.error("Backtest response is missing expected fields.")
            st.json({"missing_keys": missing_keys, "payload": data})
            st.stop()

        # Display results in a nice format
        st.markdown("---")
        st.markdown(
            '<p class="section-header">📊 Backtest Results</p>', unsafe_allow_html=True
        )

        # Metrics row
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.metric("Final Balance", f"${data['final_balance']:,.2f}")
        with m2:
            pnl_color = "normal" if data["net_pnl"] >= 0 else "inverse"
            st.metric("Net P&L", f"${data['net_pnl']:,.2f}", delta_color=pnl_color)
        with m3:
            st.metric("Max Drawdown", f"{data['max_drawdown_pct']:.2f}%")
        with m4:
            st.metric("Win Rate", f"{data['win_rate_pct']:.2f}%")
        with m5:
            st.metric("Avg R:R", f"{data['avg_rr']:.2f}")

        st.markdown("---")

        # Charts
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.subheader("📈 Equity Curve")
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(data["equity_curve"], color="#00d4ff", linewidth=2)
            ax.fill_between(
                range(len(data["equity_curve"])),
                data["equity_curve"],
                alpha=0.3,
                color="#00d4ff",
            )
            ax.set_xlabel("Step", color="#8888aa")
            ax.set_ylabel("Equity", color="#8888aa")
            ax.tick_params(colors="#8888aa")
            ax.set_facecolor("#1a1a2e")
            fig.patch.set_facecolor("#1a1a2e")
            st.pyplot(fig)

        with col_chart2:
            st.subheader("📊 Trade P&L Distribution")
            trades = pd.DataFrame(data["trades"])
            if not trades.empty:
                fig2, ax2 = plt.subplots(figsize=(8, 4))
                colors = ["#00ff88" if x >= 0 else "#ff4d4d" for x in trades["pnl"]]
                ax2.bar(range(len(trades)), trades["pnl"], color=colors)
                ax2.set_xlabel("Trade #", color="#8888aa")
                ax2.set_ylabel("P&L", color="#8888aa")
                ax2.tick_params(colors="#8888aa")
                ax2.set_facecolor("#1a1a2e")
                fig2.patch.set_facecolor("#1a1a2e")
                st.pyplot(fig2)

        # Trade details
        with st.expander("📋 Trade Details"):
            if not trades.empty:
                st.dataframe(trades, use_container_width=True)

with tab3:
    st.markdown('<p class="section-header">Analytics</p>', unsafe_allow_html=True)
    st.info(
        "📊 Analytics will be available after running a backtest. Go to the Backtesting tab to run your first backtest!"
    )

    # Placeholder for future analytics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trades", "0")
    with col2:
        st.metric("Profitable Trades", "0")
    with col3:
        st.metric("Total Profit", "$0")
    with col4:
        st.metric("Best Trade", "$0")

# Footer
st.markdown("---")
st.markdown(
    '<p style="text-align: center; color: #8888aa;">🤖 Zero-Fade Bot | Powered by Smart Money Concepts</p>',
    unsafe_allow_html=True,
)
