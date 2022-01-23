"""
Binance cache
"""

import threading

from contextlib import contextmanager


class BinanceCache:
    ticker_values = {}
    non_existent_tickers = set()
    orders = {}

    _balances = {}
    _balances_mutex = threading.Lock()

    @contextmanager
    def open_balances(self):
        with self._balances_mutex:
            yield self._balances
