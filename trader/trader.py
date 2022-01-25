"""
Automagic trader
"""

import re
import random

from datetime import datetime as _datetime

from trader.logger import logger, discord_logger, term
from trader.models import Coin, CoinValue, Pair


class Trader:
    def __init__(self, manager, database, config):
        self.logger = logger
        self.database = database
        self.config = config
        self.manager = manager

    def initialize(self):
        self.initialize_trade_thresholds()
        self.initialize_current_coin()
        self.initialize_starting_balances()

    def transaction_through_bridge(self, pair):
        """
        Jump from the source coin to the destination coin through bridge coin
        """
        can_sell = False
        balance = self.manager.get_currency_balance(pair.from_coin.symbol)
        from_coin_price = self.manager.get_ticker_price(pair.from_coin + self.config.BRIDGE_COIN)

        if balance and balance * from_coin_price > self.manager.get_min_notional(
            pair.from_coin.symbol,
            self.config.BRIDGE_COIN.symbol
        ):
            can_sell = True
        else:
            logger.warning(
                f"Insufficient balance for {term.lightcoral_bold('SELL')} order "
                f"for {term.yellow_bold(str(pair))}"
            )

        if can_sell and self.manager.sell_alt(pair.from_coin, self.config.BRIDGE_COIN) is None:
            logger.warning(f"Failed to place {term.lightcoral_bold('SELL')} order for {term.yellow_bold(str(pair))}")
            logger.over("Scouting...")
            return None

        result = self.manager.buy_alt(pair.to_coin, self.config.BRIDGE_COIN)
        if result is not None:
            self.database.set_current_coin(pair.to_coin)
            self.update_trade_threshold(pair.to_coin, result.price)
            return result

        logger.warning(f"Failed to place {term.darkolivegreen3_bold('BUY')} order for {term.yellow_bold(str(pair))}")
        logger.over("Scouting...")
        return None

    def update_trade_threshold(self, coin, coin_price):
        """
        Update all the coins with the threshold of buying the current held coin
        """

        if coin_price is None:
            logger.warning(f"{term.yellow_bold(coin + self.config.BRIDGE_COIN)} pair not found, skipping update")
            return

        with self.database.db_session() as session:
            for pair in session.query(Pair).filter(Pair.to_coin == coin):
                from_coin_price = self.manager.get_ticker_price(pair.from_coin + self.config.BRIDGE_COIN)

                if from_coin_price is None:
                    logger.warning(
                        f"{term.yellow_bold(coin + self.config.BRIDGE_COIN)} pair not found, skipping update"
                    )
                    continue

                pair.ratio = from_coin_price / coin_price

    def initialize_trade_thresholds(self):
        """
        Initialize the buying threshold of all the coins for trading between them
        """

        with self.database.db_session() as session:
            for pair in session.query(Pair).filter(Pair.ratio.is_(None)).all():
                if pair.from_coin.symbol == pair.to_coin.symbol:
                    continue

                if not pair.from_coin.enabled or not pair.to_coin.enabled:
                    continue

                logger.over(f"Initializing pair {term.yellow_bold(str(pair))}")

                from_coin_price = self.manager.get_ticker_price(pair.from_coin + self.config.BRIDGE_COIN)
                if from_coin_price is None:
                    logger.warning(
                        f"{term.yellow_wold(pair.from_coin)} symbol not found, "
                        f"skipping initialization"
                    )
                    continue

                to_coin_price = self.manager.get_ticker_price(pair.to_coin + self.config.BRIDGE_COIN)
                if to_coin_price is None:
                    logger.warning(
                        f"{term.yellow_wold(pair.to_coin)} symbol not found, "
                        f"skipping initialization"
                    )
                    continue

                pair.ratio = from_coin_price / to_coin_price
                logger.over(f"Initialized pair {term.yellow_bold(str(pair))}")

    def scout(self):
        """
        Scout for potential jumps from the current coin to another coin
        """
        raise NotImplementedError()

    def _get_ratios(self, coin, coin_price):
        """
        Given a coin, get the current price ratio for every other enabled coin
        """
        ratio_dict = {}

        for pair in self.database.get_pairs_from(coin):
            optional_coin_price = self.manager.get_ticker_price(pair.to_coin + self.config.BRIDGE_COIN)

            if optional_coin_price is None:
                logger.warning(f"Optional pair {term.yellow_bold(str(pair))} not found, skipping")
                continue

            self.database.log_scout(pair, pair.ratio, coin_price, optional_coin_price)

            # Obtain (current coin)/(optional coin)
            coin_opt_coin_ratio = coin_price / optional_coin_price

            # Fees
            from_fee = self.manager.get_fee(pair.from_coin, self.config.BRIDGE_COIN, True)
            to_fee = self.manager.get_fee(pair.to_coin, self.config.BRIDGE_COIN, False)
            transaction_fee = from_fee + to_fee - from_fee * to_fee

            if self.config.USE_MARGIN == "yes":
                ratio_dict[pair] = (
                    (1 - transaction_fee) * coin_opt_coin_ratio / pair.ratio - 1 - self.config.SCOUT_MARGIN / 100
                )
            else:
                ratio_dict[pair] = (
                    coin_opt_coin_ratio - transaction_fee * self.config.SCOUT_MULTIPLIER * coin_opt_coin_ratio
                ) - pair.ratio
        return ratio_dict

    def _jump_to_best_coin(self, coin, coin_price):
        """
        Given a coin, search for a coin to jump to
        """
        ratio_dict = self._get_ratios(coin, coin_price)

        # Keep only ratios bigger than zero
        ratio_dict = {k: v for k, v in ratio_dict.items() if v > 0}

        # If we have any viable options, pick the one with the biggest ratio
        if ratio_dict:
            best_pair = max(ratio_dict, key=ratio_dict.get)  # type: ignore
            self.logger.info(
                f"Jumping from {term.yellow_bold(str(coin))} to "
                f"{term.yellow_bold(best_pair.to_coin_id)} through "
                f"{term.yellow_bold(self.config.BRIDGE_COIN_SYMBOL)}",
            )
            self.transaction_through_bridge(best_pair)

    def bridge_scout(self):
        """
        If we have any bridge coin leftover, buy a coin with it that we won't immediately trade out of
        """
        bridge_balance = self.manager.get_currency_balance(self.config.BRIDGE_COIN.symbol)

        for coin in self.database.get_coins():
            current_coin_price = self.manager.get_ticker_price(coin + self.config.BRIDGE_COIN)

            if current_coin_price is None:
                continue

            ratio_dict = self._get_ratios(coin, current_coin_price)

            if not any(v > 0 for v in ratio_dict.values()):
                # There will only be one coin where all the ratios are negative. When we find it, buy it if we can
                if bridge_balance > self.manager.get_min_notional(coin.symbol, self.config.BRIDGE_COIN.symbol):
                    self.logger.info(
                        f"Buying {term.yellow_bold(str(coin))} using "
                        f"{self.config.BRIDGE_COIN.symbol} bridge coin"
                    )
                    self.manager.buy_alt(coin, self.config.BRIDGE_COIN)
                    return coin
        return None

    def update_values(self):
        """
        Log current value state of all altcoin balances against BTC and the bridge coin in DB.
        """
        now = _datetime.now()

        with self.database.db_session() as session:
            coins = session.query(Coin).all()
            for coin in coins:
                balance = self.manager.get_currency_balance(coin.symbol)

                if balance == 0:
                    continue

                bridge_value = self.manager.get_ticker_price(coin + self.config.BRIDGE_COIN_SYMBOL)
                btc_value = self.manager.get_ticker_price(coin + "BTC")
                coin_value = CoinValue(coin, balance, bridge_value, btc_value, datetime=now)
                session.add(coin_value)
                self.database.send_update(coin_value)

    def initialize_starting_balances(self):
        symbols = {
            "BTC",
            *{coin.symbol for coin in self.database.get_coins(only_enabled=True)},
            self.config.BRIDGE_COIN.symbol,
            self.config.BALANCE_COIN.symbol,
        }

        values = {symbol: self.manager.collate_coins(symbol) for symbol in symbols}

        with self.manager.cache.starting_balances() as starting_balances:
            starting_balances.update({symbol: value for symbol, value in values.items()})

    def display_balance(self):
        """
        Log the current balance total value in the currently held coin, BTC and the bridge coin.
        """

        # Clear the cached balances once and only once
        with self.manager.cache.open_balances() as open_balances:
            open_balances.clear()

        with self.manager.cache.starting_balances() as starting_balances:
            values = {}

            for symbol, starting_balance in starting_balances.items():
                collated_balance = self.manager.collate_coins(symbol)
                change = '{:+,.2f}%'.format((collated_balance - starting_balance) / collated_balance * 100)

                if re.match(r"^[+-]0\.00%$", change):
                    change = change.replace('-', '+')
                    change_color = term.darkgray(change)
                elif change.startswith('+'):
                    change_color = term.darkolivegreen3(change)
                else:
                    change_color = term.lightcoral(change)

                values[symbol] = {
                    "balance": '{:,.8f}'.format(collated_balance),
                    "change": change,
                    "change_color": change_color,
                }

        values = {symbol: values[symbol] for symbol in sorted(values)}
        balance_align_size = max(len(value["balance"]) for value in values.values())
        symbol_align_size = max(len(symbol) for symbol in values.keys())
        formatted_values = [
            f"{'{:>{align}}'.format(value['balance'], align=balance_align_size + 4)} "
            f"{term.yellow_bold('{:<{align}}'.format(symbol, align=symbol_align_size))} "
            f"{term.darkgray('(')}"
            f"{value['change_color']}"
            f"{term.darkgray(')')}"
            for symbol, value in values.items()
        ]
        logger.info("Current collated balance value:\n" + "\n".join(formatted_values))

        if logger.discord_enabled:
            formatted_values = "\n".join([
                f"{'{:>{align}}'.format(value['balance'], align=balance_align_size)} "
                f"{'{:<{align}}'.format(symbol, align=symbol_align_size)} "
                f"({value['change']})"
                for symbol, value in values.items()
            ])

            discord_logger.info({
                "description":
                    "Current collated balance value:"
                    "\n```\n"
                    f"{formatted_values}"
                    "\n```",
            })

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

            # If we don't have a configuration, we selected a coin at random...
            # Buy it so we can start trading.
            if self.config.CURRENT_COIN_SYMBOL == "":
                current_coin = self.database.get_current_coin()
                self.logger.info(f"Purchasing {term.yellow_bold(current_coin_symbol)} to begin trading")
                self.manager.buy_alt(current_coin, self.config.BRIDGE_COIN)
