"""
Agent SDK Data Models

Pydantic v2 BaseModel classes for agent system.
All models support:
- JSON serialization/deserialization
- pydantic-ai function calling
- Validation with custom validators
- Field aliasing for API compatibility

"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ValidationInfo


# ==================== Enums ====================

class AgentType(str, Enum):
    """Agent type enumeration."""
    CLI = "cli"
    SERVICE = "service"
    MISSION_CONTROL = "mission_control"


class AgentStatus(str, Enum):
    """Agent status states."""
    ACTIVE = "active"
    IDLE = "idle"
    PAUSED = "paused"
    OFFLINE = "offline"
    ARCHIVED = "archived"


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SuggestionType(str, Enum):
    """Type of suggestion."""
    BUG = "bug"
    REFACTOR = "refactor"
    DOCS = "docs"
    TEST = "test"
    FEATURE = "feature"
    PERFORMANCE = "performance"


# ==================== Personality & Identity ====================

class AgentPersonality(BaseModel):
    """
    Agent personality definition.
    
    Describes how the agent communicates and makes decisions.
    """
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Agent name (e.g., 'api-refactor-agent')"
    )
    
    style: str = Field(
        default="direct",
        description="Communication style (direct, verbose, conversational, technical)",
        pattern=r"^(direct|verbose|conversational|technical)$"
    )
    
    communication: str = Field(
        default="Clear explanations, code-first",
        max_length=500,
        description="Communication approach"
    )
    
    decision_making: str = Field(
        default="Analyze metrics, suggest changes",
        max_length=500,
        description="Decision-making approach"
    )
    
    formality: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Formality level (0=casual, 1=formal)"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "name": "api-refactor-agent",
                "style": "direct",
                "communication": "Clear explanations with code examples",
                "decision_making": "Data-driven, suggest bold changes",
                "formality": 0.6
            }]
        }
    }


class AgentGoals(BaseModel):
    """Agent goals and objectives."""
    
    primary: List[str] = Field(
        default=["Reduce code complexity", "Improve testability"],
        max_length=10,
        description="Primary goals (max 10)"
    )
    
    secondary: List[str] = Field(
        default=[],
        max_length=10,
        description="Secondary goals"
    )
    
    success_metrics: Dict[str, str] = Field(
        default_factory=dict,
        description="Metrics to measure success (name -> description)"
    )
    
    long_term_vision: str = Field(
        default="",
        max_length=1000,
        description="Long-term vision or aspirations"
    )


class AgentCapabilities(BaseModel):
    """Agent strengths, weaknesses, and specializations."""
    
    strengths: List[str] = Field(
        default=["Complexity analysis", "Python/TypeScript"],
        description="What agent is good at"
    )
    
    weaknesses: List[str] = Field(
        default=["DevOps", "Legacy COBOL"],
        description="Known limitations"
    )
    
    specializations: Dict[str, float] = Field(
        default_factory=dict,
        description="Specialization areas with confidence (0-1)"
    )
    
    programming_languages: List[str] = Field(
        default=["Python", "TypeScript", "JavaScript"],
        description="Languages agent can work with"
    )
    
    frameworks: List[str] = Field(
        default=["Flask", "React", "FastAPI"],
        description="Frameworks agent knows well"
    )


class AgentConstraints(BaseModel):
    """Hard and soft constraints for agent behavior."""
    
    hard_rules: List[str] = Field(
        default=[
            "Never delete code without tests",
            "Never modify production config",
            "Never suggest breaking changes"
        ],
        description="Rules that must never be violated"
    )
    
    soft_rules: List[str] = Field(
        default=["Keep functions under 50 lines", "Use existing patterns"],
        description="Preferences that agent should follow"
    )
    
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Min confidence to make suggestions (0-1)"
    )
    
    max_files_per_suggestion: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Max files to modify per suggestion"
    )


class AgentIdentity(BaseModel):
    """
    Complete agent identity and personality profile.
    
    Loaded from IDENTITY.md and other memory files.
    """
    
    id: UUID = Field(..., description="Unique agent ID")
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Agent display name"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When agent was created"
    )
    
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When agent was last updated"
    )
    
    personality: AgentPersonality = Field(
        default_factory=AgentPersonality,
        description="Agent personality traits"
    )
    
    goals: AgentGoals = Field(
        default_factory=AgentGoals,
        description="Agent goals and objectives"
    )
    
    capabilities: AgentCapabilities = Field(
        default_factory=AgentCapabilities,
        description="Agent strengths and weaknesses"
    )
    
    constraints: AgentConstraints = Field(
        default_factory=AgentConstraints,
        description="Agent constraints and rules"
    )
    
    description: str = Field(
        default="",
        max_length=1000,
        description="Long description of agent"
    )
    
    revision: int = Field(
        default=1,
        ge=1,
        description="Identity revision number (for versioning)"
    )
    
    @field_validator("name")
    @classmethod
    def name_must_be_unique_like(cls, v: str) -> str:
        """Validate agent name format."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Name must contain only alphanumeric, dashes, underscores")
        return v


# ==================== Message & Conversation ====================

class AgentMessage(BaseModel):
    """Single message in agent conversation."""
    
    id: UUID = Field(
        default_factory=UUID,
        description="Unique message ID"
    )
    
    session_id: UUID = Field(..., description="Parent session ID")
    
    role: MessageRole = Field(
        ...,
        description="Who sent message (user/assistant/system)"
    )
    
    content: str = Field(
        ...,
        min_length=1,
        description="Message content"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message timestamp"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata (token count, confidence, etc)"
    )
    
    model_config = {
        "json_encoders": {
            UUID: str,
            datetime: lambda v: v.isoformat() + "Z",
        }
    }


# ==================== Suggestions ====================

class Suggestion(BaseModel):
    """Code suggestion from agent."""
    
    id: UUID = Field(
        default_factory=UUID,
        description="Unique suggestion ID"
    )
    
    session_id: UUID = Field(..., description="Parent session ID")
    
    message_id: Optional[UUID] = Field(
        default=None,
        description="Which assistant message generated this"
    )
    
    type: SuggestionType = Field(
        default=SuggestionType.REFACTOR,
        description="Type of suggestion"
    )
    
    file_path: str = Field(
        ...,
        description="Target file path"
    )
    
    title: str = Field(
        ...,
        max_length=200,
        description="Suggestion title"
    )
    
    description: str = Field(
        default="",
        max_length=2000,
        description="Detailed explanation"
    )
    
    original_code: str = Field(
        default="",
        description="Original code snippet"
    )
    
    suggested_code: str = Field(
        default="",
        description="Suggested replacement code"
    )
    
    confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence in suggestion (0-1)"
    )
    
    applied: bool = Field(
        default=False,
        description="Has this suggestion been applied?"
    )
    
    applied_at: Optional[datetime] = Field(
        default=None,
        description="When was it applied"
    )
    
    rejected: bool = Field(
        default=False,
        description="Was suggestion rejected?"
    )
    
    rejection_reason: str = Field(
        default="",
        description="Why was it rejected"
    )
    
    impact_analysis: Dict[str, Any] = Field(
        default_factory=dict,
        description="Files affected, test impact, etc"
    )


# ==================== Session ====================

class SessionContext(BaseModel):
    """Current session context."""
    
    project_path: str = Field(..., description="Project being analyzed")
    
    scan_id: Optional[UUID] = Field(
        default=None,
        description="Most recent scan ID"
    )
    
    branch: str = Field(
        default="agent/workspaces/main",
        description="Git branch being used"
    )
    
    files_analyzed: int = Field(
        default=0,
        ge=0,
        description="Number of files analyzed"
    )
    
    suggestions_generated: int = Field(
        default=0,
        ge=0,
        description="Number of suggestions generated"
    )
    
    suggestions_applied: int = Field(
        default=0,
        ge=0,
        description="Number of suggestions applied"
    )
    
    last_activity: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last user activity time"
    )


class AgentSession(BaseModel):
    """
    Agent session state and conversation management.
    
    Tracks messages, suggestions, and session context.
    """
    
    id: UUID = Field(
        default_factory=UUID,
        description="Unique session ID"
    )
    
    agent_id: UUID = Field(..., description="Parent agent ID")
    
    project_path: str = Field(..., description="Target project path")
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Session start time"
    )
    
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update time"
    )
    
    closed_at: Optional[datetime] = Field(
        default=None,
        description="When session was closed"
    )
    
    messages: List[AgentMessage] = Field(
        default_factory=list,
        description="Conversation messages"
    )
    
    suggestions: List[Suggestion] = Field(
        default_factory=list,
        description="Suggestions in this session"
    )
    
    context: SessionContext = Field(
        default_factory=SessionContext,
        description="Session context"
    )
    
    title: str = Field(
        default="",
        max_length=200,
        description="Session title for reference"
    )
    
    description: str = Field(
        default="",
        max_length=2000,
        description="Session description"
    )
    
    tags: List[str] = Field(
        default_factory=list,
        description="Session tags for organization"
    )
    
    is_shared: bool = Field(
        default=False,
        description="Is this session shared with team?"
    )
    
    shared_with: List[str] = Field(
        default_factory=list,
        description="Team members with access"
    )


# ==================== Agent Registry ====================

class AgentMetadata(BaseModel):
    """Metadata for agent discovery and management."""
    
    id: UUID = Field(..., description="Agent UUID")
    
    name: str = Field(..., description="Agent name")
    
    type: AgentType = Field(default=AgentType.CLI, description="Agent type")
    
    status: AgentStatus = Field(default=AgentStatus.IDLE, description="Current status")
    
    version: str = Field(default="0.3.0", description="Agent version")
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When agent was created"
    )
    
    last_active: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last activity time"
    )
    
    last_session_id: Optional[UUID] = Field(
        default=None,
        description="Most recent session"
    )
    
    current_project: Optional[str] = Field(
        default=None,
        description="Currently active project"
    )
    
    total_sessions: int = Field(
        default=0,
        ge=0,
        description="Total sessions run"
    )
    
    total_suggestions: int = Field(
        default=0,
        ge=0,
        description="Total suggestions made"
    )
    
    suggestion_acceptance_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Rate of accepted suggestions"
    )
    
    memory_path: Optional[Path] = Field(
        default=None,
        description="Path to memory files"
    )
    
    tags: List[str] = Field(
        default_factory=list,
        description="Agent tags (specializations, etc)"
    )


class AgentMemory(BaseModel):
    """Agent memory file structure."""
    
    identity_file: str = Field(
        default="IDENTITY.md",
        description="Identity memory file path"
    )
    
    hook_file: str = Field(
        default="HOOK.md",
        description="Hook/trigger memory file path"
    )
    
    user_file: str = Field(
        default="USER.md",
        description="User preferences and interactions memory"
    )
    
    agent_file: str = Field(
        default="AGENT.md",
        description="Agent-specific behavior and state memory"
    )
    
    rules_file: str = Field(
        default="RULES.md",
        description="Rules and constraints memory"
    )
    
    context_file: str = Field(
        default="CONTEXT.md",
        description="Context and current state memory"
    )
    
    learnings_file: str = Field(
        default="LEARNINGS.md",
        description="Learned patterns and insights"
    )
    
    base_directory: Path = Field(
        default_factory=lambda: Path.home() / ".ghostclaw" / "agents",
        description="Base directory for memory files"
    )
    
    model_config = {
        "json_schema_extra": {
            "description": "Agent memory file configuration and paths"
        }
    }


class AgentRegistry(BaseModel):
    """Global agent registry."""
    
    agents: List[AgentMetadata] = Field(
        default_factory=list,
        description="All registered agents"
    )
    
    version: str = Field(
        default="1.0",
        description="Registry version"
    )
    
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update time"
    )
    
    model_config = {
        "json_schema_extra": {
            "description": "Global index of all agents in ecosystem"
        }
    }


# ==================== Exports ====================

__all__ = [
    # Enums
    "AgentType",
    "AgentStatus",
    "MessageRole",
    "SuggestionType",
    # Identity
    "AgentPersonality",
    "AgentGoals",
    "AgentCapabilities",
    "AgentConstraints",
    "AgentIdentity",
    # Messages & Conversation
    "AgentMessage",
    "Suggestion",
    "SessionContext",
    "AgentSession",
    # Registry & Memory
    "AgentMetadata",
    "AgentMemory",
    "AgentRegistry",
]
