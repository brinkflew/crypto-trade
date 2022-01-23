"""
Backtest the trading bot to see how it performed in the past
"""

from datetime import datetime
from traceback import format_exc

from trader import Config
from trader.logger import logger
from trader.mocks import MockDatabase, MockBinanceManager, cache

from trader.strategies import get_strategy


def backtest(
    start_date=None,
    end_date=None,
    interval=1,
    yield_interval=100,
    start_balances=None,
    starting_coin=None,
    config=None,
):
    """

    :param config: Configuration object to use
    :param start_date: Date to  backtest from
    :param end_date: Date to backtest up to
    :param interval: Number of virtual minutes between each scout
    :param yield_interval: After how many intervals should the manager be yielded
    :param start_balances: A dictionary of initial coin values. Default: {BRIDGE: 100}
    :param starting_coin: The coin to start on. Default: first coin in coin list

    :return: The final coin balances
    """

    config = config or Config()
    end_date = end_date or datetime.today()

    database = MockDatabase(config)
    database.create_database()
    database.set_coins(config.COINS_LIST)

    manager = MockBinanceManager(config, database, start_date, start_balances)
    starting_coin = database.get_coin(starting_coin or config.COINS_LIST[0])
    assert starting_coin is not None

    if manager.get_currency_balance(starting_coin.symbol) == 0:
        manager.buy_alt(starting_coin, config.BRIDGE_COIN)

    database.set_current_coin(starting_coin)

    strategy = get_strategy(config.STRATEGY)

    if strategy is None:
        logger.critical(f"Invalid strategy '{config.STRATEGY}'")
        return manager

    trader = strategy(manager, database, config)
    trader.initialize()

    yield manager
    n = 1

    while manager.datetime < end_date:
        try:
            trader.scout()
        except Exception:  # pylint: disable=broad-except
            logger.warning(format_exc())
        manager.increment(interval)
        if n % yield_interval == 0:
            yield manager
        n += 1

    cache.close()
    return manager
