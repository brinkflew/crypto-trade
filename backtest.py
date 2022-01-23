from datetime import datetime, timedelta
from signal import signal, SIGINT, SIGTERM

from trader import backtest
from trader.logger import logger, term


def signal_handler(signum, frame):
    print("", end="\r")  # Clear the last line of extraneous characters (i.e. ^C)
    logger.warning(f"Received interrupt signal ({signum}), exiting...")
    exit(signum)


def main():
    logger.info("Starting backtest trader")

    history = []
    now = datetime.now()

    for manager in backtest(now - timedelta(days=365), now):
        btc_value = manager.collate_coins("BTC")
        bridge_value = manager.collate_coins(manager.config.BRIDGE_COIN.symbol)
        history.append((btc_value, bridge_value))
        btc_diff = round((btc_value - history[0][0]) / history[0][0] * 100, 3)
        bridge_diff = round((bridge_value - history[0][1]) / history[0][1] * 100, 3)

        print(term.darkgray("Time: "), manager.datetime.strftime("%Y-%m-%d %H:%M:%S"))
        print(
            term.darkgray("Value:"),
            "{:,.8f}".format(btc_value),
            term.darkgray(term.yellow_bold("BTC")),
            term.darkgray(" {:.2f}%".format(btc_diff)),
            term.darkgray("|"),
            "{:,.8f}".format(bridge_value),
            term.darkgray(term.yellow_bold(manager.config.BRIDGE_COIN.symbol)),
            term.darkgray(" {:.2f}%".format(bridge_diff)),
        )
        print(term.darkgray("Balance details:"))

        for coin, balance in manager.balances.items():
            print(" " * 3, "{:>20,.8f}".format(balance), term.yellow_bold(coin))


if __name__ == "__main__":
    signal(SIGINT, signal_handler)
    signal(SIGTERM, signal_handler)

    try:
        main()
    except Exception as e:
        logger.exception(e)
