import json
from pathlib import Path
from typing import Optional, List, get_origin, get_args, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GhostclawConfig(BaseSettings):
    """
    Configuration manager for Ghostclaw.
    Resolves settings in order: CLI Flags -> Env Vars -> Local Config -> Global Config.
    """

    # AI Configuration
    use_ai: bool = Field(default=False, description="Enable Ghost Engine AI synthesis")
    ai_provider: str = Field(
        default="openrouter", description="AI Provider (openrouter, openai, anthropic)"
    )
    ai_model: Optional[str] = Field(
        default=None, description="Specific LLM model to use"
    )
    api_key: Optional[str] = Field(
        default=None, description="API Key for the selected provider (prefer env var)"
    )
    ai_temperature: float = Field(default=0.7, description="AI temperature (0.0-1.0)")
    ai_max_tokens: int = Field(default=4096, description="Max tokens for AI response")

    # Engine Integration
    use_pyscn: Optional[bool] = Field(
        default=None, description="Explicitly enable/disable PySCN integration"
    )
    use_ai_codeindex: Optional[bool] = Field(
        default=None, description="Explicitly enable/disable AI-CodeIndex integration"
    )

    # Analysis Behavior
    dry_run: bool = Field(
        default=False,
        description="Dry run mode: prints prompt and token count without API call",
    )
    verbose: bool = Field(
        default=False,
        description="Verbose mode: saves raw API requests/responses to debug.log",
    )
    patch: bool = Field(
        default=False,
        description="Enable refactor plan/patch suggestions from the AI engine",
    )
    show_progress: bool = Field(
        default=True, description="Show progress bar during analysis"
    )

    # Performance Tuning
    cache_enabled: bool = Field(default=True, description="Enable analysis caching")
    cache_ttl_hours: int = Field(
        default=168, description="Cache TTL in hours (default: 7 days)"
    )
    cache_compression: bool = Field(
        default=True, description="Enable compression for cached reports"
    )
    parallel_enabled: bool = Field(
        default=True, description="Enable parallel file processing"
    )
    concurrency_limit: int = Field(
        default=32, description="Max concurrent file operations"
    )
    batch_size: int = Field(default=50, description="Files per batch for processing")

    # Reliability
    retry_attempts: int = Field(
        default=3, description="Number of retry attempts for transient API failures"
    )
    retry_backoff_factor: float = Field(
        default=1.0, description="Exponential backoff factor (seconds) for retries"
    )
    retry_max_delay: float = Field(
        default=60.0, description="Maximum delay between retry attempts (seconds)"
    )

    # Plugin Management
    plugins_enabled: Optional[List[str]] = Field(
        default=None, description="List of enabled plugin names. None means all enabled."
    )

    # Analysis Thresholds
    large_file_threshold: int = Field(
        default=300, description="Lines threshold for 'large file' detection"
    )
    max_files_to_analyze: int = Field(
        default=10000, description="Maximum files to analyze (0 = unlimited)"
    )
    exclude_patterns: List[str] = Field(
        default_factory=lambda: [
            "node_modules/",
            ".git/",
            "__pycache__/",
            "*.pyc",
            "venv/",
            ".venv/",
        ],
        description="File patterns to exclude from analysis",
    )
    include_extensions: Optional[List[str]] = Field(
        default=None,
        description="File extensions to include (default: auto-detect from stack)",
    )

    # Output Configuration
    output_format: str = Field(
        default="json", description="Output format (json, markdown, html)"
    )
    report_timestamp: bool = Field(
        default=True, description="Include timestamp in report filenames"
    )
    store_reports: bool = Field(
        default=True, description="Store reports to .ghostclaw/reports/"
    )

    model_config = SettingsConfigDict(
        env_prefix="GHOSTCLAW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
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
                # Convert string to bool for boolean fields (including Optional[bool])
                annotation = cls.model_fields[k].annotation
                is_bool_type = annotation is bool or (get_origin(annotation) is Union and bool in get_args(annotation))
                if is_bool_type:
                    val = val.lower() in ("true", "1", "yes")
                resolved_config[k] = val

        # 4. CLI overrides (highest precedence)
        for k, v in cli_overrides.items():
            if v is not None:
                resolved_config[k] = v
        
        # print(f"DEBUG: GhostclawConfig.load - resolved_config['use_ai']={resolved_config.get('use_ai')}")
        return cls(**resolved_config)
