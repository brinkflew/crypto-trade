from trader.trader import Trader
from trader.logger import term


class Strategy(Trader):
    """
    Jump between the currently held coin and the most profitable coin
    through the bridge currency, scouting multiple coins at a time.

    Effectively the same as the `coin_switch` strategy but the bot
    is less likely to get stuck.
    """

    def scout(self):
        """
        Scout for potential jumps from the current coin to another coin
        """
        coin_possessed = False
        current_coin = self.database.get_current_coin()

        for coin in self.database.get_coins():
            pair_symbol = coin.symbol + self.config.BRIDGE_COIN.symbol
            coin_balance = self.manager.get_currency_balance(coin.symbol)
            coin_price = self.manager.get_ticker_price(pair_symbol)

            if coin_price is None:
                self.logger.warning(f"Ticker price for {term.yellow_bold(pair_symbol)} not found, not scouting")
                continue

            min_notional = self.manager.get_min_notional(coin.symbol, self.config.BRIDGE_COIN.symbol)

            if coin.symbol != current_coin.symbol and coin_price * coin_balance < min_notional:
                continue

            coin_possessed = True
            self.logger.over(f"Scouting pair {term.yellow_bold(pair_symbol)}...")
            self._jump_to_best_coin(coin, coin_price)

        if not coin_possessed:
            self.bridge_scout()
