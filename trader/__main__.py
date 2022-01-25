"""
Let's go tradin'
"""

import os
import time

from signal import signal, SIGINT, SIGTERM
from binance.exceptions import BinanceAPIException

from trader import Config, Database, Scheduler
from trader.logger import logger, term
from trader.binance import BinanceManager
from trader.strategies import get_strategy


def signal_handler(signum, frame):
    print("", end="\r")  # Clear the last line of extraneous characters (i.e. ^C)
    logger.warning(f"Received interrupt signal ({signum}), exiting...")
    os.kill(os.getpid(), SIGTERM)


def main():
    logger.debug("Starting trader")

    config = Config()
    database = Database(config)
    manager = BinanceManager(config, database)

    # Check if we can access API features that require a valid config
    try:
        manager.get_account()
    except BinanceAPIException as e:
        logger.error("Couldn't access Binance API - API keys may be wrong or lack sufficient permissions")
        return

    database.create_database()
    database.set_coins(config.COINS_LIST)
    logger.debug("Initialized database")

    strategy = get_strategy(config.STRATEGY)

    if strategy is None:
        logger.error(f"Invalid strategy '{config.STRATEGY}'")
        return

    trader = strategy(manager, database, config)
    trader.initialize()

    logger.success(f"Started trader using strategy {term.bold(config.STRATEGY)}")
    schedule = Scheduler()
    schedule.every(config.SCOUT_SLEEP_TIME).seconds.do(trader.scout).tag("scout")
    schedule.every(1).minutes.do(trader.update_values).tag("update value history")
    schedule.every(1).minutes.do(database.prune_scout_history).tag("prune scout history")
    schedule.every(1).hours.do(database.prune_value_history).tag("prune value history")

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    finally:
        if manager.stream_manager:
            manager.stream_manager.close()


if __name__ == "__main__":
    signal(SIGINT, signal_handler)

    try:
        main()
    except Exception as e:
        logger.critical(e, exc_info=True)
        os.kill(os.getpid(), SIGTERM)
