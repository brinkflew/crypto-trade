from trader.trader import Trader
from trader.logger import term


class Strategy(Trader):
    """
    Jump between the currently held coin and the most profitable coin
    through the bridge currency.
    """

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
