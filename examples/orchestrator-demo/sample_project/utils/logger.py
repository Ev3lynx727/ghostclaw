"""Logger that directly references Config (tight coupling)."""

from ..utils.config import get_config

class Logger:
    def __init__(self):
        cfg = get_config()
        self.level = cfg.settings.get("log_level", "INFO")

    def log(self, msg: str):
        if self.level != "OFF":
            print(f"[{self.level}] {msg}")

logger = Logger()