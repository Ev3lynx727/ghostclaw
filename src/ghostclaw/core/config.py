import json
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class GhostclawConfig(BaseSettings):
    """
    Configuration manager for Ghostclaw.
    Resolves settings in order: CLI Flags -> Env Vars -> Local Config -> Global Config.
    """
    use_ai: bool = Field(default=False, description="Enable Ghost Engine AI synthesis")
    ai_provider: str = Field(default="openrouter", description="AI Provider (openrouter, openai, anthropic)")
    api_key: Optional[str] = Field(default=None, description="API Key for the selected provider")
    use_pyscn: Optional[bool] = Field(default=None, description="Explicitly enable/disable PySCN integration")
    use_ai_codeindex: Optional[bool] = Field(default=None, description="Explicitly enable/disable AI-CodeIndex integration")
    dry_run: bool = Field(default=False, description="Dry run mode: prints prompt and token count without API call")
    verbose: bool = Field(default=False, description="Verbose mode: saves raw API requests/responses to debug.log")

    model_config = SettingsConfigDict(
        env_prefix="GHOSTCLAW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @classmethod
    def load(cls, repo_path: str, **cli_overrides) -> "GhostclawConfig":
        """
        Custom loader that merges config files before pydantic initializes.
        Merge order (lowest to highest precedence):
        1. Global Config (~/.ghostclaw/ghostclaw.json)
        2. Local Config (<repo_path>/.ghostclaw/ghostclaw.json)
        3. Environment Variables (handled by pydantic-settings)
        4. CLI overrides (passed as kwargs)
        """
        # Load and combine file configurations
        file_config = {}

        # 1. Global Config
        global_config_path = Path.home() / ".ghostclaw" / "ghostclaw.json"
        if global_config_path.exists():
            try:
                with open(global_config_path, "r", encoding="utf-8") as f:
                    file_config.update(json.load(f))
            except json.JSONDecodeError:
                pass

        # 2. Local Config
        local_config_path = Path(repo_path) / ".ghostclaw" / "ghostclaw.json"
        if local_config_path.exists():
            try:
                with open(local_config_path, "r", encoding="utf-8") as f:
                    local_data = json.load(f)
                    if "api_key" in local_data and local_data["api_key"]:
                        raise ValueError(
                            "SECURITY RISK: API key found in local project configuration "
                            f"({local_config_path}). Please move it to ~/.ghostclaw/ghostclaw.json "
                            "or use the GHOSTCLAW_API_KEY environment variable to prevent committing secrets."
                        )
                    file_config.update(local_data)
            except json.JSONDecodeError:
                pass

        # Manually apply precedence: CLI > Env > Local > Global

        default_settings = {k: v.default for k, v in cls.model_fields.items()}

        # Start with defaults
        resolved_config = default_settings.copy()

        # 1. & 2. Apply file config (Local > Global is already resolved in file_config)
        resolved_config.update(file_config)

        # 3. Apply env vars safely via os.environ
        import os
        env_prefix = cls.model_config.get("env_prefix", "")
        for k in cls.model_fields:
            env_key = f"{env_prefix}{k}".upper()
            if env_key in os.environ:
                val = os.environ[env_key]
                # Convert string to bool for boolean fields
                if cls.model_fields[k].annotation is bool:
                    val = val.lower() in ("true", "1", "yes")
                resolved_config[k] = val

        # 4. CLI overrides (highest precedence)
        for k, v in cli_overrides.items():
            if v is not None:
                resolved_config[k] = v

        return cls(**resolved_config)
