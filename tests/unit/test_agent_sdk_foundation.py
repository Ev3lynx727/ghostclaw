"""
Unit tests for agent-sdk foundation (config, models, serializers).

Tests the Pydantic-first foundation created in v0.3.0.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest

from ghostclaw.core.agent_sdk import (
    AgentCapabilities,
    AgentConstraints,
    AgentGoals,
    AgentIdentity,
    AgentMemory,
    AgentMemorySettings,
    AgentMessage,
    AgentMetadata,
    AgentPersonality,
    AgentRegistry,
    AgentSDKEncoder,
    AgentSDKSettings,
    AgentSessionSettings,
    AgentStatus,
    AgentType,
    MessageRole,
    ModelSerializer,
    SessionContext,
    Suggestion,
    SuggestionType,
    deserialize_from_json,
    get_settings,
    json_dict_to_model,
    model_to_json_dict,
    serialize_to_json,
)


class TestConfiguration:
    """Test agent-sdk configuration system."""
    
    def test_get_settings_returns_singleton(self):
        """Test that get_settings() returns same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
    
    def test_settings_default_values(self):
        """Test default configuration values."""
        settings = get_settings()
        assert settings.memory_base_dir == Path.home() / ".ghostclaw" / "agents"
        assert settings.max_memory_size_mb == 500
        assert settings.memory_save_interval_minutes == 30
        assert settings.use_pydantic_ai is True
    
    def test_agent_session_settings(self):
        """Test session-specific settings."""
        session_settings = AgentSessionSettings()
        assert session_settings.max_messages_per_session == 1000
        assert session_settings.session_timeout_minutes == 480
        assert session_settings.max_suggestions_per_session == 100
    
    def test_agent_memory_settings(self):
        """Test memory file settings."""
        memory_settings = AgentMemorySettings()
        assert memory_settings.compress_old_sessions is True
        assert memory_settings.old_session_threshold_days == 30
        assert memory_settings.backup_memory_files is True
        assert memory_settings.learnings_max_entries == 1000


class TestModels:
    """Test Pydantic data models."""
    
    def test_agent_personality_model(self):
        """Test AgentPersonality model creation and validation."""
        personality = AgentPersonality(
            name="TestAgent",
            style="direct",
            communication="Clear and concise",
        )
        assert personality.name == "TestAgent"
        assert personality.style == "direct"
        assert personality.formality == 0.5  # default
    
    def test_agent_goals_model(self):
        """Test AgentGoals model."""
        goals = AgentGoals(
            primary=["Reduce complexity"],
            secondary=["Improve docs"],
            success_metrics={"accuracy": "measure in %"},
        )
        assert goals.primary == ["Reduce complexity"]
        assert len(goals.secondary) == 1
    
    def test_agent_capabilities_model(self):
        """Test AgentCapabilities model."""
        capabilities = AgentCapabilities(
            strengths=["Python", "Architecture"],
            weaknesses=["DevOps"],
        )
        assert "Python" in capabilities.strengths
        assert "DevOps" in capabilities.weaknesses
    
    def test_agent_constraints_model(self):
        """Test AgentConstraints model."""
        constraints = AgentConstraints(
            hard_rules=["Never delete"],
            soft_rules=["Keep functions short"],
        )
        assert "Never delete" in constraints.hard_rules
        assert constraints.confidence_threshold == 0.7
        assert constraints.max_files_per_suggestion == 5
    
    def test_agent_identity_model(self):
        """Test complete AgentIdentity model."""
        agent_id = uuid4()
        identity = AgentIdentity(
            id=agent_id,
            personality=AgentPersonality(name="CodeReviewer"),
            goals=AgentGoals(primary=["Review code"]),
            capabilities=AgentCapabilities(),
            constraints=AgentConstraints(),
        )
        assert identity.id == agent_id
        assert identity.personality.name == "CodeReviewer"
    
    def test_agent_message_model(self):
        """Test AgentMessage model."""
        message = AgentMessage(
            id=uuid4(),
            role=MessageRole.USER,
            content="What is the complexity?",
            session_id=uuid4(),
        )
        assert message.role == MessageRole.USER
        assert "complexity" in message.content
    
    def test_suggestion_model(self):
        """Test Suggestion model."""
        session_id = uuid4()
        suggestion = Suggestion(
            session_id=session_id,
            type=SuggestionType.REFACTOR,
            file_path="src/main.py",
            title="Extract function",
            description="Extract complex logic",
            confidence=0.85,
        )
        assert suggestion.type == SuggestionType.REFACTOR
        assert suggestion.confidence == 0.85
        assert suggestion.file_path == "src/main.py"
    
    def test_session_context_model(self):
        """Test SessionContext model."""
        context = SessionContext(
            project_path="/path/to/project",
            branch="main",
        )
        assert context.project_path == "/path/to/project"
        assert context.branch == "main"
        assert context.files_analyzed == 0
    
    def test_agent_metadata_model(self):
        """Test AgentMetadata model."""
        agent_id = uuid4()
        metadata = AgentMetadata(
            id=agent_id,
            name="test-agent",
            type=AgentType.CLI,
            status=AgentStatus.ACTIVE,
            version="0.3.0",
        )
        assert metadata.id == agent_id
        assert metadata.name == "test-agent"
        assert metadata.type == AgentType.CLI
        assert metadata.version == "0.3.0"
    
    def test_agent_registry_model(self):
        """Test AgentRegistry model with multiple agents."""
        agent1_id = uuid4()
        agent2_id = uuid4()
        
        registry = AgentRegistry(
            agents=[
                AgentMetadata(
                    id=agent1_id,
                    name="agent1",
                    type=AgentType.CLI,
                    status=AgentStatus.ACTIVE,
                ),
                AgentMetadata(
                    id=agent2_id,
                    name="agent2",
                    type=AgentType.SERVICE,
                    status=AgentStatus.OFFLINE,
                ),
            ]
        )
        assert len(registry.agents) == 2
        assert registry.agents[0].id == agent1_id
    
    def test_model_json_serialization(self):
        """Test that models can be serialized to JSON."""
        agent_metadata = AgentMetadata(
            id=uuid4(),
            name="test-agent",
            type=AgentType.CLI,
            status=AgentStatus.ACTIVE,
            version="0.3.0",
        )
        json_str = agent_metadata.model_dump_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["type"] == "cli"
        assert parsed["status"] == "idle"  # default value


class TestSerializers:
    """Test serialization utilities."""
    
    def test_custom_encoder_uuid(self):
        """Test AgentSDKEncoder handles UUID."""
        agent_id = uuid4()
        data = {"id": agent_id}
        json_str = json.dumps(data, cls=AgentSDKEncoder)
        assert str(agent_id) in json_str
    
    def test_custom_encoder_path(self):
        """Test AgentSDKEncoder handles Path."""
        path = Path("/home/user/projects")
        data = {"path": path}
        json_str = json.dumps(data, cls=AgentSDKEncoder)
        assert "/home/user/projects" in json_str
    
    def test_serialize_to_json_function(self):
        """Test serialize_to_json convenience function."""
        metadata = AgentMetadata(
            id=uuid4(),
            name="test-agent",
            type=AgentType.CLI,
            status=AgentStatus.ACTIVE,
        )
        json_str = serialize_to_json(metadata)
        assert isinstance(json_str, str)
        assert "id" in json_str
        assert "type" in json_str
    
    def test_deserialize_from_json_function(self):
        """Test deserialize_from_json convenience function."""
        original_id = uuid4()
        json_str = f'{{"id": "{original_id}", "name": "test", "type": "cli", "status": "idle", "version": "0.3.0"}}'
        
        metadata = deserialize_from_json(json_str, AgentMetadata)
        assert metadata.id == original_id
        assert metadata.name == "test"
        assert metadata.type == AgentType.CLI
        assert metadata.type == AgentType.GENERALIST
    
    def test_model_to_json_dict(self):
        """Test model_to_json_dict function."""
        agent_id = uuid4()
        metaname="test-agent",
            type=AgentType.CLI,
            status=AgentStatus.ACTIVE,
        )
        data_dict = model_to_json_dict(metadata)
        assert isinstance(data_dict, dict)
        assert data_dict["id"] == str(agent_id)
        assert data_dict["type"] == "cli
        assert data_dict["id"] == str(agent_id)
        assert data_dict["type"] == "specialist"
    
    def test_json_dict_to_model(self):
        """Test json_dict_to_model function."""
        agentname": "test-agent",
            "type": "cli",
            "status": "idle",
            "version": "0.3.0",
        }
        metadata = json_dict_to_model(data_dict, AgentMetadata)
        assert metadata.id == agent_id
        assert metadata.name == "test-agent"
        assert metadata.type == AgentType.CLI
        metadata = json_dict_to_model(data_dict, AgentMetadata)
        assert metadata.id == agent_id
        assert metadata.type == AgentType.GENERALIST
    
    def test_model_serializer_class(self):
        """Test ModelSerializer class."""
        seriname="test-agent",
            type=AgentType.CLI,
            status=AgentStatus.ACTIVE,
            version="0.3.0",
        )
        
        # Serialize
        json_str = serializer.serialize(metadata)
        assert isinstance(json_str, str)
        
        # Deserialize
        restored = serializer.deserialize(json_str)
        assert restored.id == original_id
        assert restored.name == "test-agent"
        assert restored.type == AgentType.CLI
        
        # Deserialize
        restored = serializer.deserialize(json_str)
        assert restored.id == original_id
        assert restored.type == AgentType.SPECIALIST
    
    def test_model_serializer_file_operations(self):
        """Test ModelSerializer file save/load."""
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test_metadata.json"
            
            serializer = ModelSerializer(AgentMetadata)
            original_id = uuid4()
            metadata = AgentMetadata(
                id=original_id,
                type=AgentType.SPECIALIST,
                status=AgentStatus.ACTIVE,
            )
            
            # Save to file
            serializer.serialize_file(metadata, file_path)
            assert file_path.exists()
            
            # Load from file
            restored = serializer.deserialize_file(file_path)
            assert restored.id == original_id
            assert restored.type == AgentType.SPECIALIST


class TestEnums:
    """Test enum types."""
    
    def test_agent_type_enum(self):
        """Test AgentType enum values."""
        assert AgentType.CLI.value == "cli"
        assert AgentType.SERVICE.value == "service"
        assert AgentType.MISSION_CONTROL.value == "mission_control"
    
    def test_agent_status_enum(self):
        """Test AgentStatus enum values."""
        assert AgentStatus.ACTIVE.value == "active"
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.PAUSED.value == "paused"
    
    def test_message_role_enum(self):
        """Test MessageRole enum values."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"
    
    def test_suggestion_type_enum(self):
        """Test SuggestionType enum values."""
        assert SuggestionType.REFACTOR.value == "refactor"
        assert SuggestionType.BUG.value == "bug"
        assert SuggestionType.FEATURE.value == "feature"


class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_full_workflow_create_metadata_serialize_deserialize(self):
        """Test complete workflow: create metadata, serialize, deserialize."""
        agent_id = uuid4()
        
        # 1. Create metadata
        metadata = AgentMetadata(
            name="test-agent",
            type=AgentType.CLI,
            status=AgentStatus.ACTIVE,
            version="0.3.0",
        )
        
        # 2. Serialize to JSON
        json_str = serialize_to_json(metadata)
        assert isinstance(json_str, str)
        
        # 3. Deserialize back
        restored = deserialize_from_json(json_str, AgentMetadata)
        
        # 4. Verify
        assert restored.id == agent_id
        assert restored.name == "test-agent"
        assert restored.version == "0.3.0"
    
    def test_full_agent_identity_workflow(self):
        """Test creating complete agent identity and serializing."""
        agent_id = uuid4()
        
        identity = AgentIdentity(
            id=agent_id,
            personality=AgentPersonality(
                name="ArchitectureExpert",
                style="direct",
                communication="Clear and concise",
            ),
            goals=AgentGoals(
                primary=["Improve code architecture"],
                secondary=["Reduce cyclomatic complexity"],
            ),
            capabilities=AgentCapabilities(
                strengths=["Python", "Go", "Architecture"],
                weaknesses=["DevOps"],
            ),
            constraints=AgentConstraints(
                hard_rules=["Never delete code without tests"],
                soft_rules=["Keep functions under 50 lines"],
            ),
        )
        
        # Serialize
        json_str = identity.model_dump_json()
        assert isinstance(json_str, str)
        # Deserialize
        assert restored["id"] == str(agent_id)
        assert restored["personality"]["name"] == "ArchitectureExpert"
        assert "Python" in restored["capabilities"]["strength
        assert "Python" in restored["capabilities"]["supported_languages"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
