# Zero-Fade Bot (J.A.R.V.I.S. Protocol)

Production-style Python architecture for the **Zero-Fade** reversal system using:
- `MetaTrader5` for broker connectivity
- `pandas_ta` for SMA(20) trend filtering
- `smartmoneyconcepts` for additional market-structure context
- `loguru` for console and file logging

## Architecture

- `main.py`: entry point, loads credentials from environment, starts bot
- `zero_fade_bot/config.py`: typed runtime configuration dataclasses
- `zero_fade_bot/logging_setup.py`: centralized loguru setup (console + rotating file)
- `zero_fade_bot/mt5_gateway.py`: MT5 adapter and order execution
- `zero_fade_bot/strategy.py`: Zero-Fade signal generation logic
- `zero_fade_bot/news_filter.py`: economic-calendar blackout abstraction
- `zero_fade_bot/bot.py`: orchestration loop, kill-switch enforcement, symbol scanning

## Risk rules implemented

- Hard-coded account assumptions in config defaults:
  - Initial equity target: `$10.00`
  - Lot size: `0.01`
  - Kill-switch equity: `$4.00`
  - Stop-loss distance: `20 pips` from double-zero anchor
  - Take-profit distance: `35 pips` from entry

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export MT5_LOGIN=12345678
export MT5_PASSWORD='your-password'
export MT5_SERVER='YourBroker-Demo'
python main.py
```

## Notes

- Bot operates on M15 only by default.
- Major FX pairs are predefined in `StrategyConfig`.
- News filter is intentionally abstract; wire `EconomicCalendarFilter.get_upcoming_events` to your preferred calendar provider.
- This is educational software and not financial advice.
