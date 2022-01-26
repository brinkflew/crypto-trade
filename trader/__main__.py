"""
Let's go tradin'
"""

import os
import time

from signal import SIGINT, SIGTERM
from urllib3.exceptions import ReadTimeoutError
from requests.exceptions import ReadTimeout
from binance.exceptions import BinanceAPIException

from trader import Config, Database, Scheduler
from trader.logger import logger, term
from trader.binance import BinanceManager
from trader.strategies import get_strategy


class ControlledException(Exception):
    pass


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

    logger.success(f"Starting trader using strategy {term.bold(config.STRATEGY)}")
    trader = strategy(manager, database, config)
    trader.initialize()

    if time.localtime().tm_min < 45:  # Avoid spamming the current balance
        trader.display_balance()

    schedule = Scheduler()
    schedule.every(config.SCOUT_SLEEP_TIME).seconds.do(trader.scout).tag("scout")
    schedule.every(1).minutes.do(trader.update_values).tag("update value history")
    schedule.every(1).minutes.do(database.prune_scout_history).tag("prune scout history")
    schedule.every(1).hours.do(database.prune_value_history).tag("prune value history")
    schedule.every(1).hours.at(':00').do(trader.display_balance).tag("display balance")
    schedule.every(1).hours.do(manager.reconnect).tag("reconnect manager")

    try:
        reconnection_attempts = 0

        while True:
            try:
                schedule.run_pending()
                time.sleep(1)

            except (ReadTimeoutError, ReadTimeout):
                logger.warning(f"Connection to API manager timed out")

                if config.BINANCE_RETRIES_UNLIMITED or reconnection_attempts < config.BINANCE_RETRIES:
                    reconnection_attempts += 1
                    logger.info(f"Reconnecting [{reconnection_attempts}/{config.BINANCE_RETRIES}]")
                    manager.reconnect()
                else:
                    raise ControlledException(
                        f"Maximum reconnection attempts reached "
                        f"[{reconnection_attempts}/{config.BINANCE_RETRIES}]"
                    )
    finally:
        if manager.stream_manager:
            manager.stream_manager.close()


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print("", end="\r")  # Clear the last line of extraneous characters (i.e. ^C)
        logger.warning(f"Received interrupt signal ({SIGINT}), exiting...")

    except ControlledException as e:
        logger.error(e)

    except Exception as e:
        logger.critical(e, exc_info=True)

    finally:
        os.kill(os.getpid(), SIGTERM)
