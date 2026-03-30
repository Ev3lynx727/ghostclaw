"""Logger that directly references Config (tight coupling)."""

from ..utils.config import get_config

class Logger:
    def __init__(self):
        """
        Initialize the Logger instance's log level from application configuration.
        
        Reads the global configuration via get_config() and sets self.level to the configured "log_level" value; if the setting is missing, defaults to "INFO".
        """
        cfg = get_config()
        self.level = cfg.settings.get("log_level", "INFO")

    def log(self, msg: str):
        """
        Prints the given message prefixed with the current log level when logging is enabled.
        
        Parameters:
            msg (str): The message to output. If the logger's level is set to "OFF", this message is not printed.
        """
        if self.level != "OFF":
            print(f"[{self.level}] {msg}")

logger = Logger()