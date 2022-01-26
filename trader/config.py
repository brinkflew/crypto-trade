"""
Config manager
"""

import os
import re
import configparser

from trader.logger import logger
from trader.models import Coin

TRADER_CONFIG_FILE_NAME = "trader.cfg"
TRADER_CONFIG_FILE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), f"../{TRADER_CONFIG_FILE_NAME}")
)
TRADER_CONFIG_SECTION = "binance_trader"


class Config:
    def __init__(self):
        config = configparser.ConfigParser()
        config["__default"] = {
            "bridge_coin_symbol": "USDT",
            "coins_list": "",
            "scout_retention_time": 1,
            "scout_multiplier": 5,
            "scout_sleep_time": 5,
            "strategy": "default",
            "binance_tld": "com",
            "binance_retries": 0,
            "sell_timeout": 0,
            "buy_timeout": 0,
            "scout_margin": 0.8,
            "use_margin": "no",
        }

        if os.path.exists(TRADER_CONFIG_FILE_PATH):
            config.read(TRADER_CONFIG_FILE_PATH)
        else:
            logger.warning(
                f"Configuration file not found ({TRADER_CONFIG_FILE_NAME}), "
                f"assuming default configuration"
            )
            config[TRADER_CONFIG_SECTION] = {}

        def get_option(key):
            return os.environ.get(key.upper()) or config.get(TRADER_CONFIG_SECTION, key.lower())

        # Coins config
        self.CURRENT_COIN_SYMBOL = get_option("CURRENT_COIN_SYMBOL")
        self.BRIDGE_COIN_SYMBOL = get_option("BRIDGE_COIN_SYMBOL")
        self.BRIDGE_COIN = Coin(self.BRIDGE_COIN_SYMBOL, False)
        self.BALANCE_COIN_SYMBOL = get_option("BALANCE_COIN_SYMBOL") or self.BRIDGE_COIN_SYMBOL
        self.BALANCE_COIN = Coin(self.BALANCE_COIN_SYMBOL, False) \
            if self.BALANCE_COIN_SYMBOL != self.BRIDGE_COIN_SYMBOL \
            else self.BRIDGE_COIN

        coins_list = {coin for coin in re.split(r"[^A-Z]", get_option("COINS_LIST").upper()) if coin}
        coins_list.discard(self.BRIDGE_COIN_SYMBOL)

        self.COINS_LIST = list(coins_list)

        if self.BRIDGE_COIN_SYMBOL in self.COINS_LIST:
            self.COINS_LIST.remove(self.BRIDGE_COIN_SYMBOL)

        self.COINS_LIST = list(self.COINS_LIST)

        # Prune settings
        self.SCOUT_RETENTION_TIME = float(get_option("SCOUT_RETENTION_TIME"))

        # Scouting config
        self.SCOUT_MULTIPLIER = float(get_option("SCOUT_MULTIPLIER"))
        self.SCOUT_SLEEP_TIME = int(get_option("SCOUT_SLEEP_TIME"))

        # Binance config
        self.BINANCE_API_KEY = get_option("BINANCE_API_KEY")
        self.BINANCE_API_SECRET = get_option("BINANCE_API_SECRET")
        self.BINANCE_TLD = get_option("BINANCE_TLD")
        self.BINANCE_RETRIES = int(get_option("BINANCE_RETRIES"))
        self.BINANCE_RETRIES_UNLIMITED = not self.BINANCE_RETRIES

        # Selected strategy
        self.STRATEGY = get_option("STRATEGY")

        # Timeouts
        self.SELL_TIMEOUT = get_option("SELL_TIMEOUT")
        self.BUY_TIMEOUT = get_option("BUY_TIMEOUT")

        # Margin usage
        self.SCOUT_MARGIN = float(get_option("SCOUT_MARGIN"))
        self.USE_MARGIN = get_option("USE_MARGIN")
