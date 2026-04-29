from __future__ import annotations
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from zero_fade_bot.backtest import (
    BacktestConfig,
    BacktestService,
    ExecutionConfig,
    RiskConfig,
)

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
async def run_backtest(
    config: str = Form(...),
    csv_file: UploadFile = File(...),
) -> dict[str, Any]:
    try:
        parsed_config = BacktestRequest.model_validate_json(config)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid backtest config: {exc}"
        ) from exc

    filename = csv_file.filename
    if not filename:
        raise HTTPException(
            status_code=400, detail="Uploaded CSV file must have a filename"
        )

    tmp_dir = Path("tmp")
    tmp_dir.mkdir(exist_ok=True)
    target = tmp_dir / filename
    content = await csv_file.read()
    target.write_bytes(content)

    result = backtest_service.run_zero_fade(
        csv_path=target,
        config=BacktestConfig(
            symbol=parsed_config.symbol,
            execution=ExecutionConfig(
                spread_pips=parsed_config.spread_pips,
                slippage_pips=parsed_config.slippage_pips,
                execution_delay_bars=parsed_config.execution_delay_bars,
            ),
            risk=RiskConfig(
                initial_balance=parsed_config.initial_balance,
                lot_size=parsed_config.lot_size,
                risk_percent_per_trade=parsed_config.risk_percent_per_trade,
            ),
        ),
        start_date=parsed_config.start_date,
        end_date=parsed_config.end_date,
    )
    return result
