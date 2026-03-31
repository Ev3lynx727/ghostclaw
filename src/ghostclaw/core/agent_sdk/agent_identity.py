"""
Agent Identity Module

Handles persistent agent identity including personality, goals, capabilities, and constraints.
Stores in ~/.ghostclaw/agents/{agent-id}/memory/IDENTITY.md as JSON format.

Main class: AgentIdentityManager - handles load/save/create operations
"""

from pathlib import Path
from typing import Optional
from uuid import UUID
import json

from .config import get_settings
from .models import (
    AgentIdentity,
    AgentPersonality,
    AgentGoals,
    AgentCapabilities,
    AgentConstraints,
)
from .serializers import ModelSerializer


class AgentIdentityManager:
    """Manages agent identity persistence and lifecycle."""
    
    IDENTITY_FILENAME = "IDENTITY.md"
    
    def __init__(self, agent_id: UUID):
        """Initialize identity manager for a specific agent."""
        self.agent_id = agent_id
        self.settings = get_settings()
        self.identity_dir = self.settings.memory_base_dir / str(agent_id) / "memory"
        self.identity_file = self.identity_dir / self.IDENTITY_FILENAME
        self.serializer = ModelSerializer(AgentIdentity)
    
    def create(
        self,
        personality: AgentPersonality,
        goals: AgentGoals,
        capabilities: AgentCapabilities,
        constraints: AgentConstraints,
    ) -> AgentIdentity:
        """
        Create a new agent identity.
        
        Args:
            personality: Agent personality definition
            goals: Agent goals and objectives
            capabilities: Agent strengths and specializations
            constraints: Agent constraints and rules
        
        Returns:
            New AgentIdentity instance
        """
        identity = AgentIdentity(
            id=self.agent_id,
            name=personality.name,
            personality=personality,
            goals=goals,
            capabilities=capabilities,
            constraints=constraints,
        )
        self.save(identity)
        return identity
    
    def load(self) -> Optional[AgentIdentity]:
        """
        Load identity from disk.
        
        Returns:
            AgentIdentity if exists, None otherwise
        """
        if not self.identity_file.exists():
            return None
        
        try:
            return self.serializer.deserialize_file(self.identity_file)
        except Exception as e:
            raise ValueError(f"Failed to load identity from {self.identity_file}: {e}")
    
    def load_or_create_default(self) -> AgentIdentity:
        """
        Load existing identity or create with defaults.
        
        Returns:
            AgentIdentity (loaded or newly created)
        """
        existing = self.load()
        if existing:
            return existing
        
        # Create with sensible defaults
        return self.create(
            personality=AgentPersonality(
                name=f"agent-{str(self.agent_id)[:8]}",
                style="direct",
                communication="Clear and concise explanations with code examples",
                decision_making="Analyze metrics, suggest evidence-based changes",
                formality=0.6,
            ),
            goals=AgentGoals(
                primary=[
                    "Reduce code complexity",
                    "Improve code maintainability",
                    "Suggest architectural improvements",
                ],
                secondary=[
                    "Identify performance issues",
                    "Recommend testing improvements",
                ],
                success_metrics={
                    "complexity_reduction": "Cyclomatic complexity decrease",
                    "maintainability": "Code health score increase",
                    "acceptance_rate": "% of suggestions accepted",
                },
                long_term_vision="Become a trusted architecture advisor for development teams",
            ),
            capabilities=AgentCapabilities(
                strengths=[
                    "Code complexity analysis",
                    "Python architecture",
                    "TypeScript/JavaScript patterns",
                    "Refactoring suggestions",
                    "Module isolation strategies",
                ],
                weaknesses=[
                    "DevOps/Infrastructure",
                    "Hardware optimization",
                    "Legacy code in non-mainstream languages",
                ],
                specializations={
                    "python": 0.95,
                    "typescript": 0.85,
                    "architecture": 0.90,
                    "refactoring": 0.88,
                },
                programming_languages=["Python", "TypeScript", "JavaScript", "Go"],
                frameworks=["FastAPI", "Flask", "React", "Vue", "Express"],
            ),
            constraints=AgentConstraints(
                hard_rules=[
                    "Never delete code without tests",
                    "Never modify production configuration",
                    "Never suggest breaking changes without migration path",
                    "Always respect existing architectural patterns",
                ],
                soft_rules=[
                    "Keep functions under 50 lines when possible",
                    "Prefer composition over inheritance",
                    "Use existing patterns and conventions",
                    "Consider performance implications",
                    "Document complex logic",
                ],
                confidence_threshold=0.7,
                max_files_per_suggestion=5,
            ),
        )
    
    def save(self, identity: AgentIdentity) -> None:
        """
        Save identity to disk.
        
        Args:
            identity: AgentIdentity to save
        """
        self.identity_dir.mkdir(parents=True, exist_ok=True)
        self.serializer.serialize_file(identity, self.identity_file)
    
    def update(self, identity: AgentIdentity) -> None:
        """
        Update identity with new values.
        
        Args:
            identity: Updated AgentIdentity
        """
        if identity.id != self.agent_id:
            raise ValueError(f"Identity agent_id {identity.id} != {self.agent_id}")
        self.save(identity)
    
    def get_summary(self) -> str:
        """Get human-readable summary of identity."""
        identity = self.load()
        if not identity:
            return "No identity defined"
        
        lines = [
            f"# Agent: {identity.personality.name}",
            f"ID: {identity.id}",
            "",
            "## Personality",
            f"- Style: {identity.personality.style}",
            f"- Communication: {identity.personality.communication}",
            f"- Decision Making: {identity.personality.decision_making}",
            f"- Formality: {identity.personality.formality:.1f}/1.0",
            "",
            "## Goals",
            f"- Primary: {', '.join(identity.goals.primary)}",
            f"- Secondary: {', '.join(identity.goals.secondary)}",
            "",
            "## Capabilities",
            f"- Strengths: {', '.join(identity.capabilities.strengths)}",
            f"- Languages: {', '.join(identity.capabilities.programming_languages)}",
            f"- Frameworks: {', '.join(identity.capabilities.frameworks)}",
            "",
            "## Constraints",
            f"- Confidence Threshold: {identity.constraints.confidence_threshold:.1f}",
            f"- Max Files Per Suggestion: {identity.constraints.max_files_per_suggestion}",
            f"- Hard Rules: {len(identity.constraints.hard_rules)} rules",
            f"- Soft Rules: {len(identity.constraints.soft_rules)} rules",
        ]
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Export identity as dictionary."""
        identity = self.load()
        if not identity:
            raise ValueError("No identity loaded")
        return json.loads(identity.model_dump_json())
    
    def from_dict(self, data: dict) -> AgentIdentity:
        """
        Import identity from dictionary.
        
        Args:
            data: Dictionary with identity data
        
        Returns:
            Imported AgentIdentity
        """
        identity = AgentIdentity(**data)
        self.save(identity)
        return identity


__all__ = ["AgentIdentityManager"]
