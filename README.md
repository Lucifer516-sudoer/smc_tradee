# Zero-Fade Trading System (MT5 + Backtesting + Web Dashboard)

This repository now includes **two production-oriented tracks**:
1. **Live bot runtime** (MT5 execution loop)
2. **Backtesting + Web Control Plane** (FastAPI + Streamlit)

---

## Recommended Tech Stack (with rationale)

### Backend API: FastAPI
- Async-ready, fast for control endpoints and file uploads.
- Strong request validation via Pydantic.
- Easy OpenAPI docs for operator workflows.

### UI: Streamlit (initial) → React (later)
- Streamlit is ideal for rapid prototyping dashboard and backtest UX.
- Keep REST contract stable so React can replace Streamlit without refactoring core logic.

### Core Engine: Pure Python Domain Modules
- Strategy and execution engine isolated from UI/API to maximize testability.
- Dependency inversion through strategy protocol (`BacktestStrategy`).

### Data & Analytics: pandas + matplotlib
- Fast CSV ingestion and analysis for ForexSB exports.
- Simple charting for equity and trade distributions.

---

## Architecture

```text
zero_fade_bot/
  api/
    app.py              # FastAPI app: health, bot control, backtest endpoints
    controller.py       # Runtime bot state controller abstraction
    schemas.py          # Pydantic request/response models
  backtest/
    config.py           # Backtest, execution and risk config dataclasses
    data_loader.py      # ForexSB CSV loader
    strategy.py         # BacktestStrategy protocol + ZeroFade strategy adapter
    models.py           # Core domain dataclasses (Bar/Signal/Trade/Position)
    engine.py           # Execution simulator + metrics engine
    service.py          # Service layer for API/UI invocation
  dashboard/
    app.py              # Streamlit monitoring/control/backtesting interface
  bot.py                # Live runtime loop and kill-switch orchestration
  strategy.py           # Live signal generation (MT5 runtime)
  mt5_gateway.py        # MT5 wrapper integration adapter
  logging_setup.py      # standard logging setup (console + file)
  news_filter.py        # News blackout extension point
main.py                 # Live runtime entrypoint
```

---

## Backtesting Features Implemented

- Load historical CSV (ForexSB-style columns: `Time/Open/High/Low/Close[/Volume]`).
- Configurable:
  - initial balance
  - lot size
  - risk % (config surface ready)
  - spread/slippage/execution-delay
- Simulation loop with:
  - delayed order execution
  - spread + slippage-aware fills
  - SL/TP handling
- Metrics:
  - net P/L
  - max drawdown
  - win rate
  - average risk-reward
  - equity curve
- Strategy plug-in via protocol (`BacktestStrategy`).

---

## Web Dashboard Capabilities

### Monitoring
- Bot status endpoint integration (`/bot/status`)
- Connected/running/active trades/account metrics display

### Control
- Start/Stop bot controls (`/bot/start`, `/bot/stop`)

### Backtesting
- CSV upload
- Parameter configuration
- Run backtest from UI
- Visualize:
  - equity curve
  - trade PnL distribution
  - detailed trade table

---

## Run Instructions

### 1) Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Run API

```bash
uvicorn zero_fade_bot.api.app:app --reload --port 8000
```

### 3) Run Dashboard

```bash
streamlit run zero_fade_bot/dashboard/app.py
```

### 4) Run Live MT5 Bot

```bash
export MT5_LOGIN=12345678
export MT5_PASSWORD='your-password'
export MT5_SERVER='YourBroker-Demo'
export LOG_LEVEL=INFO
export LOG_FILE_PATH='logs/bot.log'
python main.py
```

The live bot writes logs to `logs/bot.log` and console using the format `[TIME] [LEVEL] [MODULE] message`.

---

## Pitfalls and Performance Considerations

1. **Indicator recomputation cost**
   - Current backtest strategy recalculates indicators per bar for clarity.
   - For large datasets, precompute indicators once and iterate vectorized signals.

2. **Intrabar ambiguity**
   - If both TP and SL are touched in same candle, deterministic rule needed (currently first logical hit path).
   - Consider tick-level simulation for precision.

3. **Risk modeling vs fixed lot**
   - Runtime supports fixed lot as requested (0.01).
   - For scalable deployment, add dynamic position sizing from stop distance + equity risk cap.

4. **MT5 operational safety**
   - Add idempotency keys / order dedupe when reconnecting.
   - Separate execution service process from API process.

5. **State persistence**
   - Current controller is in-memory.
   - Production should persist runs, settings, and metrics to Postgres/Redis.

6. **News filter dependency**
   - Economic calendar is an integration point; production needs robust provider fallback and caching.

---

## Next Steps for Production Hardening

- Add unit tests for backtest engine edge cases (gap moves, simultaneous SL/TP, weekend candles).
- Add async task queue (RQ/Celery) for long backtests.
- Add auth (JWT/session) to API and role-based control actions.
- Add Docker Compose for API + dashboard + Redis + Postgres.

