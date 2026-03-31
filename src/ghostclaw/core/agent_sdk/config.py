"""
Agent SDK Configuration

Settings for agent-sdk using pydantic-settings.
Supports environment variables, config files, and defaults.

Example:
    >>> from ghostclaw.core.agent_sdk.config import AgentSDKSettings
    >>> settings = AgentSDKSettings()
    >>> print(settings.memory_dir)
    /home/user/.ghostclaw/agents

"""

from pathlib import Path
from typing import Optional, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class AgentSDKSettings(BaseSettings):
    """
    Global Agent SDK configuration.
    
    Settings can be provided via:
    1. Environment variables (prefix: GHOSTCLAW_AGENT_)
    2. .env file
    3. Constructor arguments
    4. Defaults
    
    Example env vars:
        GHOSTCLAW_AGENT_MEMORY_DIR=/custom/path
        GHOSTCLAW_AGENT_MAX_MEMORY_SIZE_MB=500
    """
    
    # Directories
    memory_base_dir: Path = Field(
        default_factory=lambda: Path.home() / ".ghostclaw" / "agents",
        description="Base directory for all agent memories"
    )
    
    # Memory settings
    max_memory_size_mb: int = Field(
        default=500,
        description="Max total size of memory files per agent (MB)",
        ge=10,  # At least 10 MB
        le=5000,  # Max 5 GB
    )
    
    memory_save_interval_minutes: int = Field(
        default=30,
        description="How often to auto-save memory files (minutes)",
        ge=5,  # At least every 5 minutes
        le=1440,  # Max once a day
    )
    
    # Git settings
    git_default_branch: str = Field(
        default="main",
        description="Default git branch name (main or master)",
        pattern=r"^(main|master|develop|dev)$"
    )
    
    workspace_branch_prefix: str = Field(
        default="agent/workspaces",
        description="Prefix for agent workspace branches"
    )
    
    # LLM settings
    llm_model: Literal["claude-opus", "claude-sonnet", "gpt-4", "gpt-3.5-turbo"] = Field(
        default="claude-opus",
        description="Default LLM model for agent responses"
    )
    
    llm_temperature: float = Field(
        default=0.3,
        description="LLM temperature (0.0-1.0, lower = more deterministic)",
        ge=0.0,
        le=1.0
    )
    
    llm_max_tokens: int = Field(
        default=2000,
        description="Max tokens per response",
        ge=100,
        le=10000
    )
    
    # Logging & debugging
    debug: bool = Field(
        default=False,
        description="Enable debug logging"
    )
    
    log_memory_updates: bool = Field(
        default=True,
        description="Log when memory files are updated"
    )
    
    # pydantic-ai settings
    use_pydantic_ai: bool = Field(
        default=True,
        description="Enable pydantic-ai for agent reasoning"
    )
    
    pydantic_ai_model: str = Field(
        default="openai:gpt-4",
        description="pydantic-ai model identifier (e.g., 'openai:gpt-4', 'anthropic:claude-opus')"
    )
    
    # Validation
    strict_validation: bool = Field(
        default=True,
        description="Enforce strict Pydantic validation on all models"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="GHOSTCLAW_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_default=True,
        extra="ignore",  # Ignore unknown env vars
    )


class AgentSessionSettings(BaseSettings):
    """Settings for individual agent sessions."""
    
    session_timeout_minutes: int = Field(
        default=480,  # 8 hours
        description="Session timeout (minutes)",
        ge=5,
        le=10080,  # Max 7 days
    )
    
    max_messages_per_session: int = Field(
        default=1000,
        description="Max messages to keep in memory per session",
        ge=10,
        le=10000
    )
    
    max_suggestions_per_session: int = Field(
        default=100,
        description="Max suggestions to track per session",
        ge=5,
        le=1000
    )
    
    model_config = SettingsConfigDict(
        env_prefix="GHOSTCLAW_SESSION_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


class AgentMemorySettings(BaseSettings):
    """Settings for agent memory files."""
    
    compress_old_sessions: bool = Field(
        default=True,
        description="Compress older sessions to save space"
    )
    
    old_session_threshold_days: int = Field(
        default=30,
        description="Sessions older than this are compressed",
        ge=1,
        le=365
    )
    
    backup_memory_files: bool = Field(
        default=True,
        description="Create backups before updating memory files"
    )
    
    learnings_max_entries: int = Field(
        default=1000,
        description="Max entries in LEARNINGS.md before archiving",
        ge=100,
        le=10000
    )
    
    model_config = SettingsConfigDict(
        env_prefix="GHOSTCLAW_MEMORY_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
_settings: Optional[AgentSDKSettings] = None


def get_settings() -> AgentSDKSettings:
    """Get global agent-sdk settings (singleton)."""
    global _settings
    if _settings is None:
        _settings = AgentSDKSettings()
    return _settings


def reset_settings() -> None:
    """Reset settings (useful for testing)."""
    global _settings
    _settings = None


__all__ = [
    "AgentSDKSettings",
    "AgentSessionSettings",
    "AgentMemorySettings",
    "get_settings",
    "reset_settings",
]
