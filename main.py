from __future__ import annotations

import os

from zero_fade_bot.bot import ZeroFadeBot
from zero_fade_bot.config import BotConfig
from zero_fade_bot.logging_setup import configure_logging


def load_config_from_env() -> BotConfig:
    login = int(os.environ["MT5_LOGIN"])
    password = os.environ["MT5_PASSWORD"]
    server = os.environ["MT5_SERVER"]
    return BotConfig(mt5_login=login, mt5_password=password, mt5_server=server)


def main() -> None:
    config = load_config_from_env()
    configure_logging(config.logging)
    bot = ZeroFadeBot(config=config)
    bot.run()


if __name__ == "__main__":
    main()
