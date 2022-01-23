import os
import configparser

CONFIG_FILE_NAME = "trader.cfg"
CONFIG_FILE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), f"../{CONFIG_FILE_NAME}")
)
CONFIG_SECTION = "notifications"


class DiscordConfig:
    def __init__(self):
        config = configparser.ConfigParser()

        if os.path.exists(CONFIG_FILE_PATH):
            config.read(CONFIG_FILE_PATH)
        else:
            config[CONFIG_SECTION] = {}

        def get_option(key):
            return os.environ.get(key.upper()) or config.get(CONFIG_SECTION, key.lower()) or None

        self.WEBHOOK_URL = get_option("DISCORD_WEBHOOK_URL")
