"""Configuration loader (tightly coupled to global state)."""

import json
from pathlib import Path

class Config:
    _instance = None

    def __init__(self):
        """
        Initialize the Config instance with default settings and apply any user overrides from the per-user configuration file.
        
        The instance will have a `settings` dictionary initially containing `"db_url": "sqlite:///default.db"` and `"log_level": "INFO"`. After initialization, `settings` may be updated with values loaded from the user's configuration file (if present).
        """
        self.settings = {
            "db_url": "sqlite:///default.db",
            "log_level": "INFO"
        }
        self._load()

    def _load(self):
        """
        Attempt to load JSON configuration from the user's ~/.appconfig.json and merge any keys into self.settings.
        
        If the file exists, parse it as JSON and update self.settings in place with the top-level object’s key/value pairs; if the file is absent, leave self.settings unchanged.
        """
        cfg_path = Path.home() / ".appconfig.json"
        if cfg_path.exists():
            with open(cfg_path) as f:
                self.settings.update(json.load(f))

    @classmethod
    def get(cls):
        """
        Provide access to the class-level singleton Config instance.
        
        Returns:
            Config: The canonical Config instance for this class; creates and caches a new one on the class if none exists.
        """
        if cls._instance is None:
            cls._instance = Config()
        return cls._instance

def get_config():
    """
    Get the singleton Config instance used by the application.
    
    Returns:
        Config: The singleton configuration object exposing application settings.
    """
    return Config.get()