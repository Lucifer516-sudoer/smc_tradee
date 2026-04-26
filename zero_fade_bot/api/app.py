from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, UploadFile

from zero_fade_bot.backtest import BacktestConfig, BacktestService, ExecutionConfig, RiskConfig

from .controller import BotController
from .schemas import BacktestRequest, BotStatusResponse, StartBotRequest

app = FastAPI(title="Zero-Fade Control API", version="1.0.0")
controller = BotController()
backtest_service = BacktestService()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/bot/status", response_model=BotStatusResponse)
def bot_status() -> BotStatusResponse:
    state = controller.status()
    return BotStatusResponse(
        connected=state.connected,
        running=state.running,
        active_trades=state.active_trades,
        balance=state.balance,
        equity=state.equity,
        margin=state.margin,
    )


@app.post("/bot/start")
def bot_start(request: StartBotRequest) -> dict[str, str]:
    _ = request
    controller.start()
    return {"message": "bot started"}


@app.post("/bot/stop")
def bot_stop() -> dict[str, str]:
    controller.stop()
    return {"message": "bot stopped"}


@app.post("/backtest/run")
async def run_backtest(config: BacktestRequest, csv_file: UploadFile = File(...)) -> dict:
    tmp_dir = Path("tmp")
    tmp_dir.mkdir(exist_ok=True)
    target = tmp_dir / csv_file.filename
    content = await csv_file.read()
    target.write_bytes(content)

    result = backtest_service.run_zero_fade(
        csv_path=target,
        config=BacktestConfig(
            symbol=config.symbol,
            execution=ExecutionConfig(
                spread_pips=config.spread_pips,
                slippage_pips=config.slippage_pips,
                execution_delay_bars=config.execution_delay_bars,
            ),
            risk=RiskConfig(
                initial_balance=config.initial_balance,
                lot_size=config.lot_size,
                risk_percent_per_trade=config.risk_percent_per_trade,
            ),
        ),
    )
    return result
