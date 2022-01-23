"""
Database mock for backtesting
"""

from trader import Database


class MockDatabase(Database):
    def __init__(self, config):
        super().__init__(config, "sqlite:///")

    def log_scout(self, pair, target_ratio, current_coin_price, other_coin_price):
        pass
