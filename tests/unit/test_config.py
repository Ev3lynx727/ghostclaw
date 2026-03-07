import os
import json
import pytest
from pathlib import Path
from ghostclaw.core.config import GhostclawConfig

def test_config_load_cli_overrides():
    config = GhostclawConfig.load(".", use_ai=True, ai_provider="openai")
    assert config.use_ai is True
    assert config.ai_provider == "openai"

def test_config_load_env_vars(monkeypatch):
    monkeypatch.setenv("GHOSTCLAW_API_KEY", "test-key")
    monkeypatch.setenv("GHOSTCLAW_USE_AI", "True")

    config = GhostclawConfig.load(".")
    assert config.api_key == "test-key"
    assert config.use_ai is True

def test_config_reject_local_api_key(tmp_path, monkeypatch):
    # Change current working directory to tmp_path for the test
    # since field_validator checks Path(".ghostclaw")
    monkeypatch.chdir(tmp_path)

    # Create local config with api_key
    gc_dir = tmp_path / ".ghostclaw"
    gc_dir.mkdir()
    config_file = gc_dir / "ghostclaw.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump({"api_key": "secret-key"}, f)

    with pytest.raises(ValueError, match="SECURITY RISK: API key found in local project configuration"):
        # The validation is now correctly in the `load` classmethod to check the specific repo path
        GhostclawConfig.load(".")
