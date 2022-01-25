# Strategies

You can add your own strategy to this folder. The filename is the name of the strategy
when set in the trader configuration.

The file must contain at least the following:

```py
from trader.trader import Trader


class Strategy(Trader):

    def scout(self):
        # Your custom scout method

```

Then, set your `strategy` configuration to your strategy name. If you named your file
`custom_strategy.py`, you'd need to put `strategy=custom_strategy` in your config file.

You can put your strategy in a subfolder, and the bot will still find it. If you'd like to
share your strategy with others, try using git submodules.

---

Some premade strategies are listed below:

## `coin_switch`

Jump between the currently held coin and the most profitable coin through the bridge currency.

## `coin_switch_multi`

Jump between the currently held coin and the most profitable coin through the bridge currency,
scouting multiple coins at a time.

Effectively the same as the `coin_switch` strategy but the bot is less likely to get stuck.
