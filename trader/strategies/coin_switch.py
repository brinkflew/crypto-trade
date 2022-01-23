import random

from trader.trader import Trader
from trader.logger import term


class Strategy(Trader):
    """
    Jump between the currently held coin and the most profitable coin
    through the bridge currency
    """

    def initialize(self):
        super().initialize()
        self.initialize_current_coin()

    def scout(self):
        """
        Scout for potential jumps from the current coin to another coin
        """
        current_coin = self.database.get_current_coin()
        pair_symbol = current_coin + self.config.BRIDGE_COIN

        self.logger.over(f"Scouting pair {term.yellow_bold(pair_symbol)}...")

        current_coin_price = self.manager.get_ticker_price(pair_symbol)

        if current_coin_price is None:
            self.logger.warning(f"Ticker price for {term.yellow_bold(pair_symbol)} not found, not scouting")
            return

        self._jump_to_best_coin(current_coin, current_coin_price)

    def bridge_scout(self):
        current_coin = self.database.get_current_coin()

        if self.manager.get_currency_balance(current_coin.symbol) > self.manager.get_min_notional(
            current_coin.symbol,
            self.config.BRIDGE_COIN.symbol,
        ):
            # Only scout if we don't have enough of the current coin
            return

        new_coin = super().bridge_scout()

        if new_coin is not None:
            self.database.set_current_coin(new_coin)

    def initialize_current_coin(self):
        """
        Decide what is the current coin, and set it up in the database
        """
        if self.database.get_current_coin() is None:
            current_coin_symbol = self.config.CURRENT_COIN_SYMBOL

            if not current_coin_symbol:
                current_coin_symbol = random.choice(self.config.COINS_LIST)

            self.logger.info(f"Setting initial coin to {term.yellow_bold(current_coin_symbol)}")

            if current_coin_symbol not in self.config.COINS_LIST:
                raise ValueError("Current coin symbol must be in coins list")

            self.database.set_current_coin(current_coin_symbol)

            # If we don't have a configuration, we selected a coin at random... Buy it so we can start trading.
            if self.config.CURRENT_COIN_SYMBOL == "":
                current_coin = self.database.get_current_coin()
                self.logger.info(f"Purchasing {term.yellow_bold(current_coin_symbol)} to begin trading")
                self.manager.buy_alt(current_coin, self.config.BRIDGE_COIN)
                self.logger.success("Ready to start trading")
