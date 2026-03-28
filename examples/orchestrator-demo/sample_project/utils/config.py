"""Configuration loader (tightly coupled to global state)."""

import json
from pathlib import Path

class Config:
    _instance = None

    def __init__(self):
        self.settings = {
            "db_url": "sqlite:///default.db",
            "log_level": "INFO"
        }
        self._load()

    def _load(self):
        cfg_path = Path.home() / ".appconfig.json"
        if cfg_path.exists():
            with open(cfg_path) as f:
                self.settings.update(json.load(f))

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = Config()
        return cls._instance

def get_config():
    return Config.get()