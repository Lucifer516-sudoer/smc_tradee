from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .config import BacktestConfig
from .models import Bar, ClosedTrade, FillEvent, Position, Side
from .strategy import BacktestStrategy


@dataclass
class BacktestResult:
    initial_balance: float
    final_balance: float
    net_pnl: float
    max_drawdown_pct: float
    win_rate_pct: float
    avg_rr: float
    equity_curve: list[float]
    trades: list[ClosedTrade]


class BacktestEngine:
    def __init__(self, config: BacktestConfig, strategy: BacktestStrategy) -> None:
        self.config = config
        self.strategy = strategy

    def _pip_size(self) -> float:
        return 0.01 if self.config.symbol.endswith("JPY") else 0.0001

    def _pip_value_for_lot(self) -> float:
        return self.config.risk.pip_value_per_lot * self.config.risk.lot_size

    def run(self, bars: list[Bar]) -> BacktestResult:
        balance = self.config.risk.initial_balance
        equity_curve: list[float] = [balance]
        peak = balance
        max_dd = 0.0
        open_position: Position | None = None
        trades: list[ClosedTrade] = []
        delayed_signals: deque[tuple[int, Side, float, float]] = deque()

        pip_size = self._pip_size()
        pip_value = self._pip_value_for_lot()

        for idx, bar in enumerate(bars):
            signal = self.strategy.on_bar(bars, idx)
            if signal is not None and open_position is None:
                delayed_signals.append((idx + self.config.execution.execution_delay_bars, signal.side, signal.stop_loss_pips, signal.take_profit_pips))

            if delayed_signals and delayed_signals[0][0] <= idx and open_position is None:
                _, side, sl_pips, tp_pips = delayed_signals.popleft()
                fill = self._fill_from_bar(bar=bar, side=side)
                sl_price = fill.price - sl_pips * pip_size if side == Side.BUY else fill.price + sl_pips * pip_size
                tp_price = fill.price + tp_pips * pip_size if side == Side.BUY else fill.price - tp_pips * pip_size
                open_position = Position(
                    side=side,
                    entry_time=bar.time,
                    entry_price=fill.price,
                    stop_loss=sl_price,
                    take_profit=tp_price,
                    lot_size=self.config.risk.lot_size,
                )

            if open_position is not None:
                closed_trade = self._try_close(bar=bar, pos=open_position, pip_size=pip_size, pip_value=pip_value)
                if closed_trade is not None:
                    trades.append(closed_trade)
                    balance += closed_trade.pnl
                    open_position = None

            equity_curve.append(balance)
            peak = max(peak, balance)
            dd = ((peak - balance) / peak) * 100 if peak > 0 else 0.0
            max_dd = max(max_dd, dd)

        wins = [t for t in trades if t.pnl > 0]
        avg_rr = sum(t.rr for t in trades) / len(trades) if trades else 0.0
        return BacktestResult(
            initial_balance=self.config.risk.initial_balance,
            final_balance=balance,
            net_pnl=balance - self.config.risk.initial_balance,
            max_drawdown_pct=max_dd,
            win_rate_pct=(len(wins) / len(trades) * 100) if trades else 0.0,
            avg_rr=avg_rr,
            equity_curve=equity_curve,
            trades=trades,
        )

    def _fill_from_bar(self, bar: Bar, side: Side) -> FillEvent:
        pip_size = self._pip_size()
        spread = self.config.execution.spread_pips * pip_size
        slippage = self.config.execution.slippage_pips * pip_size
        if side == Side.BUY:
            price = bar.open + spread + slippage
        else:
            price = bar.open - spread - slippage
        return FillEvent(time=bar.time, price=price, slippage_pips=self.config.execution.slippage_pips, spread_pips=self.config.execution.spread_pips)

    def _try_close(self, bar: Bar, pos: Position, pip_size: float, pip_value: float) -> ClosedTrade | None:
        if pos.side == Side.BUY:
            hit_sl = bar.low <= pos.stop_loss
            hit_tp = bar.high >= pos.take_profit
        else:
            hit_sl = bar.high >= pos.stop_loss
            hit_tp = bar.low <= pos.take_profit

        if not hit_sl and not hit_tp:
            return None

        exit_price = pos.stop_loss if hit_sl else pos.take_profit
        delta = (exit_price - pos.entry_price) / pip_size
        signed_pips = delta if pos.side == Side.BUY else -delta
        pnl = signed_pips * pip_value
        risk_pips = abs((pos.entry_price - pos.stop_loss) / pip_size)
        rr = abs(signed_pips / risk_pips) if risk_pips else 0.0

        return ClosedTrade(
            side=pos.side,
            entry_time=pos.entry_time,
            exit_time=bar.time,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            pnl=pnl,
            rr=rr,
        )
