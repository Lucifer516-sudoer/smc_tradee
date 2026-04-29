from __future__ import annotations

from zero_fade_bot.bot import ZeroFadeBot
from zero_fade_bot.config import load_config_from_env
from zero_fade_bot.logging_setup import configure_logging


def main() -> None:
    config = load_config_from_env()
    configure_logging(config.logging)
    bot = ZeroFadeBot(config=config)
    bot.run()


if __name__ == "__main__":
    main()
