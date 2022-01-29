# Crypto-Trader

Automated cryptocurrency trading bot

> *Largely copied and inspired from [edeng23/binance-trade-bot](https://github.com/edeng23/binance-trade-bot)*


## Why?

This project was inspired by the observation that all cryptocurrencies pretty much behave in the same way. When one spikes, they all spike, and when one takes a dive, they all do. *Pretty much*. Moreover, all coins follow Bitcoin's lead; the difference is their phase offset.

So, if coins are basically oscillating with respect to each other, it seems smart to trade the rising coin for the falling coin, and then trade back when the ratio is reversed.

## How?

The trading is done in the Binance market platform, which of course, does not have markets for every altcoin pair. The workaround for this is to use a bridge currency that will complement missing pairs. The default bridge currency is Tether (USDT), which is stable by design and compatible with nearly every coin on the platform.

<p align="center">
  Coin A → USDT → Coin B
</p>

The way the bot takes advantage of the observed behaviour is to always downgrade from the "strong" coin to the "weak" coin, under the assumption that at some point the tables will turn. It will then return to the original coin, ultimately holding more of it than it did originally. This is done while taking into consideration the trading fees.

<div align="center">
  <p><b>Coin A</b> → USDT → Coin B</p>
  <p>Coin B → USDT → Coin C</p>
  <p>...</p>
  <p>Coin C → USDT → <b>Coin A</b></p>
</div>

The bot jumps between a configured set of coins on the condition that it does not return to a coin unless it is profitable in respect to the amount held last. This means that we will never end up having less of a certain coin. The risk is that one of the coins may freefall relative to the others all of a sudden, attracting our reverse greedy algorithm.

## Binance Setup

-   Create a [Binance account](https://accounts.binance.com/en/register?ref=74751172) (Includes my referral link, I'll be super grateful if you use it).
-   Enable Two-factor Authentication.
-   Create a new API key.
-   Get a cryptocurrency. If its symbol is not in the default list, add it.

## Tool Setup

### Install Python dependencies

Run the following line in the terminal: `pip install -r requirements.txt`.

### Configuration

#### `trader.cfg` file

Create a file named `trader.cfg` based off `trader.cfg.example`, then add your API keys and current coin.

**The configuration file consists of the following fields:**

- `binance_api_key` - Binance API key generated in the Binance account setup stage.
- `binance_api_secret` - Binance secret key generated in the Binance account setup stage.
- `binance_tld` - `com` or `us`, depending on your region. Default is `com`. Use `us` if the bot is hosted on the American continent.
- `binance_retries` - Number of reconnection attempts in case of connection error with the Binance API server. Leave empty or set to `0` for unlimited retries.
- `bridge_coin_symbol` - Your bridge currency of choice. Notice that different bridges will allow different sets of supported coins. For example, there may be a Binance particular-coin/USDT pair but no particular-coin/BUSD pair.
- `current_coin_symbol` - This is your starting coin of choice. This should be one of the coins from your supported coin list. If you want to start from your bridge currency, leave this field empty, the bot will select a random coin from your supported coin list and buy it.
- `balance_coin_symbol` - This coin will be used when printing out the status of your balance. It does not need to be in the coin list as it is used for display purposes only.
- `coins_list` - The list of coins your are willing to trade, the bot will detect existing pairs by itself.
- `scout_retention_time` - Controls how many hours of scouting values are kept in the database. After the amount of time specified has passed, the information will be deleted.
- `use_margin` - `yes` to use scout_margin, `no` to use scout_multiplier.
- `scout_multiplier` - Controls the value by which the difference between the current state of coin ratios and previous state of ratios is multiplied. For bigger values, the bot will wait for bigger margins to arrive before making a trade.
- `scout_margin` - Minimum percentage coin gain per trade. 0.8 translates to a scout multiplier of 5 at 0.1% fee.
- `scout_sleep_time` - Controls how many seconds bot should wait between analysis of current prices. Since the bot now operates on websockets this value should be set to something low (like 1), the reasons to set it above 1 are when you observe high CPU usage or you receive API errors about requests weight limit.
- `strategy` - The trading strategy to use. See [`trader/strategies`](trader/strategies/README.md) for more information
- `buy_timeout`/`sell_timeout` - Controls how many minutes to wait before cancelling a limit order (buy/sell) and returning to "scout" mode. 0 means that the order will never be cancelled prematurely.
- `discord_webhook_url` - URL of the Discord webhook to use for sending alerts and notifications.

#### Environment Variables

All of the options provided in `trader.cfg` can also be configured using environment variables.

```sh
BINANCE_API_KEY=""
BINANCE_API_SECRET=""
BINANCE_TLD="com"
BINANCE_RETRIES=5
BRIDGE_COIN_SYMBOL="USDT"
CURRENT_COIN_SYMBOL="DOT"
COINS_LIST="BTC ETH BCH BNB ADA XRP ATOM LUNA DOT SOL USDT"
SCOUT_RETENTION_TIME=1
USE_MARGIN="no"
SCOUT_MULTIPLIER=5
SCOUT_MARGIN=0.8
SCOUT_SLEEP_TIME=1
STRATEGY="coin_switch"
BUY_TIMEOUT=15
SELL_TIMEOUT=15
DISCORD_WEBHOOK_URL=""
```

### Paying Fees with BNB
You can [use BNB to pay for any fees on the Binance platform](https://www.binance.com/en/support/faq/115000583311-Using-BNB-to-Pay-for-Fees), which will reduce all fees by 25%. In order to support this benefit, the bot will always perform the following operations:
- Automatically detect that you have BNB fee payment enabled.
- Make sure that you have enough BNB in your account to pay the fee of the inspected trade.
- Take into consideration the discount when calculating the trade threshold.

### Notifications

The bot can send alert and trade notifications to Discord through webhooks.

To setup the notifications, you first need to create a webhook in your Discord server by choosing a text channel and editing it.

Go to `Integrations` then `Webhooks` and create a new webhook. Click the `Copy Webhook URL` and paste that content into your `trader.cfg` file next to the `discord_webhook_url` key, or in the `DISCORD_WEBHOOK_URL` environment variable.

### Run

```sh
python3 -m trader
```

## Backtesting

You can test the bot on historic data to see how it performs.

```shell
python3 backtest.py
```

Feel free to modify that file to test and compare different settings and time periods.

## Support the Project

<a href="https://www.buymeacoffee.com/avanserv" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-green.png" alt="Buy Me a Coffee" height="41" width="174"></a>

## Disclaimer

This project is for informational purposes only. You should not construe any
such information or other material as legal, tax, investment, financial, or
other advice. Nothing contained here constitutes a solicitation, recommendation,
endorsement, or offer by me or any third party service provider to buy or sell
any securities or other financial instruments in this or in any other
jurisdiction in which such solicitation or offer would be unlawful under the
securities laws of such jurisdiction.

If you plan to use real money, USE AT YOUR OWN RISK.

Under no circumstances will I be held responsible or liable in any way for any
claims, damages, losses, expenses, costs, or liabilities whatsoever, including,
without limitation, any direct or indirect damages for loss of profits.
