"""
Ghostclaw Agent SDK - Foundation Module

Provides core abstractions for agent persistence, memory, and workspace isolation.

This module contains:

**Configuration**:
  - AgentSDKSettings: Global settings via environment variables
  - AgentSessionSettings: Session-specific settings
  - AgentMemorySettings: Memory file configuration
  - get_settings(): Singleton pattern access

**Data Models (Pydantic BaseModel)**:
  Enums: AgentType, AgentStatus, MessageRole, SuggestionType
  Identity: AgentPersonality, AgentGoals, AgentCapabilities, AgentConstraints, AgentIdentity
  Conversation: AgentMessage, Suggestion, SessionContext
  Registry: AgentMetadata, AgentRegistry, AgentMemory

**Serialization**:
  - AgentSDKEncoder: Custom JSON encoder for UUID, Path, datetime
  - serialize_to_json(), deserialize_from_json(): Convenience functions
  - ModelSerializer: Class-based serialization for model instances

Example:
    >>> from ghostclaw.core.agent_sdk import AgentIdentity, get_settings
    >>> settings = get_settings()
    >>> agent = AgentIdentity(...)
    >>> json_str = agent.model_dump_json()

Version: 0.3.0 (Foundation Release)
Status: Phase 1 - Agent SDK foundation

"""

from .config import (
    AgentMemorySettings,
    AgentSDKSettings,
    AgentSessionSettings,
    get_settings,
)
from .models import (
    AgentCapabilities,
    AgentConstraints,
    AgentGoals,
    AgentIdentity,
    AgentMemory,
    AgentMessage,
    AgentMetadata,
    AgentPersonality,
    AgentRegistry,
    AgentStatus,
    AgentType,
    MessageRole,
    SessionContext,
    Suggestion,
    SuggestionType,
)
from .serializers import (
    AgentSDKEncoder,
    ModelSerializer,
    deserialize_from_json,
    json_dict_to_model,
    model_to_json_dict,
    serialize_to_json,
)
from .agent_identity import AgentIdentityManager
from .agent_memory import AgentMemoryManager, MemoryEntry, MemoryFile
from .agent_workspace import (
    AgentWorkspaceManager,
    GitCommit,
    GitConfig,
    GitPullRequest,
    WorkspaceFile,
)
from .agent_session import (
    AgentSessionManager,
    SessionAction,
    SessionMetrics,
    SessionState,
    SessionSummary,
)
from .agent_cli import AgentCLI, CommandResult


__version__ = "0.3.0"
__author__ = "Ghostclaw Team"

__all__ = [
    # Configuration
    "AgentSDKSettings",
    "AgentSessionSettings",
    "AgentMemorySettings",
    "get_settings",
    # Models - Enums
    "AgentType",
    "AgentStatus",
    "MessageRole",
    "SuggestionType",
    # Models - Identity
    "AgentPersonality",
    "AgentGoals",
    "AgentCapabilities",
    "AgentConstraints",
    "AgentIdentity",
    # Models - Conversation
    "AgentMessage",
    "Suggestion",
    "SessionContext",
    # Models - Registry & Memory
    "AgentMetadata",
    "AgentRegistry",
    "AgentMemory",
    # Serialization
    "AgentSDKEncoder",
    "serialize_to_json",
    "deserialize_from_json",
    "model_to_json_dict",
    "json_dict_to_model",
    "ModelSerializer",
    # Managers
    "AgentIdentityManager",
    "AgentMemoryManager",
    "MemoryEntry",
    "MemoryFile",
    "AgentWorkspaceManager",
    "GitConfig",
    "GitCommit",
    "GitPullRequest",
    "WorkspaceFile",
    "AgentSessionManager",
    "SessionState",
    "SessionAction",
    "SessionMetrics",
    "SessionSummary",
    # CLI
    "AgentCLI",
    "CommandResult",
    # Module info
    "__version__",
    "__author__",
]
