from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuntimeControl:
    running: bool = False
    connected: bool = False
    active_trades: int = 0
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0


class BotController:
    """Thin runtime controller for API wiring.

    Replace internals with thread/process-based orchestration for production.
    """

    def __init__(self) -> None:
        self.state = RuntimeControl()

    def start(self) -> None:
        self.state.running = True
        self.state.connected = True

    def stop(self) -> None:
        self.state.running = False

    def status(self) -> RuntimeControl:
        return self.state
