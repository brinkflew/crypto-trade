"""
Mock Binance API manager for backtesting
"""

import os

from datetime import datetime, timedelta
from collections import defaultdict
from sqlitedict import SqliteDict
from binance.exceptions import BinanceAPIException

from trader.logger import term
from trader.binance import BinanceManager, BinanceOrder

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
CACHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../.data/backtest_cache.sqlite')
)
os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
cache = SqliteDict(CACHE_PATH)


class MockBinanceManager(BinanceManager):
    def __init__(self, config, database, start_date=None, start_balances=None):
        super().__init__(config, database)
        self.config = config
        self.datetime = start_date or datetime(2021, 1, 1)
        self.balances = start_balances or {config.BRIDGE_COIN.symbol: 100.0}

    def setup_websockets(self):
        pass  # No websockets are needed for backtesting

    def increment(self, interval=1):
        self.datetime += timedelta(minutes=interval)

    def get_fee(self, origin_coin, target_coin, selling):
        return 0.00075

    def get_ticker_price(self, ticker_symbol):
        """
        Get ticker price of a specific coin
        """
        target_date = self.datetime.replace(second=0).strftime(DATE_FORMAT)
        key = f"{ticker_symbol} - {target_date}"
        val = cache.get(key, None)

        if val is None:
            end_date = min(self.datetime + timedelta(hours=12), datetime.now())
            self.logger.info(
                f"Fetching prices for {term.yellow_bold(ticker_symbol)} between "
                f"{target_date} and {end_date.strftime(DATE_FORMAT)}"
            )

            try:
                for result in self.client.get_historical_klines(
                    ticker_symbol,
                    "1m",
                    int(datetime.timestamp(self.datetime) * 1000),
                    int(datetime.timestamp(end_date) * 1000),
                    limit=1000
                ):
                    date = datetime.utcfromtimestamp(result[0] / 1000).strftime(DATE_FORMAT)
                    price = float(result[1])
                    cache[f"{ticker_symbol} - {date}"] = price
            except BinanceAPIException as e:
                if e.code == -1121:
                    self.logger.warning(f"Invalid symbol: {term.yellow_bold(ticker_symbol)}")
                    return 0
                raise e

            cache.commit()
            val = cache.get(key, None)
        return val

    def get_currency_balance(self, currency_symbol, force=False):
        """
        Get balance of a specific coin
        """
        return self.balances.get(currency_symbol, 0.0)

    def buy_alt(self, origin_coin, target_coin):
        origin_symbol = origin_coin.symbol
        target_symbol = target_coin.symbol

        target_balance = self.get_currency_balance(target_symbol)
        from_coin_price = self.get_ticker_price(origin_symbol + target_symbol) or 1

        order_quantity = self._buy_quantity(origin_symbol, target_symbol, target_balance, from_coin_price)
        target_quantity = order_quantity * from_coin_price
        self.balances[target_symbol] -= target_quantity
        self.balances[origin_symbol] = self.balances.get(origin_symbol, 0) + order_quantity * (
            1 - self.get_fee(origin_coin, target_coin, False)
        )
        self.logger.success(
            f"{term.darkolivegreen3_bold('BUY')} "
            f"{'{:>,.8f}'.format(self.balances[origin_symbol])} "
            f"{term.yellow_bold(origin_symbol)} "
            f"{term.darkgray('for')} "
            f"{'{:>,.8f}'.format(target_quantity)} "
            f"{term.yellow_bold(target_symbol)} "
        )
        self.logger.info(
            f"{' ' * 4}Coin:"
            f"{'{:>20,.8f}'.format(self.balances[origin_symbol])} {term.yellow_bold(origin_symbol)}"
        )
        self.logger.info(
            f"{' ' * 4}Fiat:"
            f"{'{:>20,.8f}'.format(self.balances[target_symbol])} {term.yellow_bold(target_symbol)}"
        )

        event = defaultdict(lambda: None, order_price=from_coin_price, cumulative_quote_asset_transacted_quantity=0)
        return BinanceOrder(event)

    def sell_alt(self, origin_coin, target_coin):
        origin_symbol = origin_coin.symbol
        target_symbol = target_coin.symbol

        origin_balance = self.get_currency_balance(origin_symbol)
        from_coin_price = self.get_ticker_price(origin_symbol + target_symbol)

        order_quantity = self._sell_quantity(origin_symbol, target_symbol, origin_balance)
        target_quantity = order_quantity * from_coin_price
        self.balances[origin_symbol] -= order_quantity
        self.balances[target_symbol] = self.balances.get(target_symbol, 0) + target_quantity * (
            1 - self.get_fee(origin_coin, target_coin, True)
        )
        self.logger.success(
            f"{term.lightcoral_bold('SELL')} "
            f"{'{:>,.8f}'.format(self.balances[origin_symbol])} "
            f"{term.yellow_bold(origin_symbol)} "
            f"{term.darkgray('for')} "
            f"{'{:>,.8f}'.format(target_quantity)} "
            f"{term.yellow_bold(target_symbol)} "
        )
        self.logger.info(
            f"{' ' * 4}Coin:"
            f"{'{:>20,.8f}'.format(self.balances[origin_symbol])} {term.yellow_bold(origin_symbol)}"
        )
        self.logger.info(
            f"{' ' * 4}Fiat:"
            f"{'{:>20,.8f}'.format(self.balances[target_symbol])} {term.yellow_bold(target_symbol)}"
        )
        return {"price": from_coin_price}

    def collate_coins(self, target_symbol: str):
        total = 0
        for coin, balance in self.balances.items():
            if coin == target_symbol:
                total += balance
                continue
            if coin == self.config.BRIDGE_COIN.symbol:
                price = self.get_ticker_price(target_symbol + coin)
                if price is None:
                    continue
                total += balance / price
            else:
                price = self.get_ticker_price(coin + target_symbol)
                if price is None:
                    continue
                total += price * balance
        return total
