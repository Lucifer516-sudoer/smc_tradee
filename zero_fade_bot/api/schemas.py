from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BotStatusResponse(BaseModel):
    connected: bool
    running: bool
    active_trades: int
    balance: float
    equity: float
    margin: float


class StartBotRequest(BaseModel):
    risk_percent_per_trade: float = Field(20.0, ge=0.1, le=100.0)
    lot_size: float = Field(0.01, ge=0.01)
    strategy_name: str = "zero_fade"


class BacktestRequest(BaseModel):
    symbol: str = "EURUSD"
    initial_balance: float = 10.0
    lot_size: float = 0.01
    risk_percent_per_trade: float = 20.0
    spread_pips: float = 1.2
    slippage_pips: float = 0.5
    execution_delay_bars: int = 1
    # Date range for backtest (optional)
    start_date: Optional[datetime] = Field(
        None, description="Start date for backtest (UTC)"
    )
    end_date: Optional[datetime] = Field(
        None, description="End date for backtest (UTC)"
    )
