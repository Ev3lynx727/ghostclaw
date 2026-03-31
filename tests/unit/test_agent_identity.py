"""Tests for agent identity manager."""

from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest

from ghostclaw.core.agent_sdk.agent_identity import AgentIdentityManager
from ghostclaw.core.agent_sdk import (
    AgentPersonality,
    AgentGoals,
    AgentCapabilities,
    AgentConstraints,
)


def test_agent_identity_manager_create():
    """Test creating a new identity."""
    agent_id = uuid4()
    
    with TemporaryDirectory() as tmpdir:
        # Mock the settings to use temp directory
        import ghostclaw.core.agent_sdk.agent_identity as identity_module
        original_get_settings = identity_module.get_settings
        
        # Create mock settings
        class MockSettings:
            memory_base_dir = Path(tmpdir)
        
        try:
            identity_module.get_settings = lambda: MockSettings()
            
            manager = AgentIdentityManager(agent_id)
            
            personality = AgentPersonality(name="TestAgent")
            goals = AgentGoals(primary=["Test"])
            capabilities = AgentCapabilities()
            constraints = AgentConstraints()
            
            identity = manager.create(personality, goals, capabilities, constraints)
            
            assert identity.id == agent_id
            assert identity.personality.name == "TestAgent"
            assert manager.identity_file.exists()
        finally:
            identity_module.get_settings = original_get_settings


def test_agent_identity_manager_load():
    """Test loading saved identity."""
    agent_id = uuid4()
    
    with TemporaryDirectory() as tmpdir:
        import ghostclaw.core.agent_sdk.agent_identity as identity_module
        original_get_settings = identity_module.get_settings
        
        class MockSettings:
            memory_base_dir = Path(tmpdir)
        
        try:
            identity_module.get_settings = lambda: MockSettings()
            
            # Create and save
            manager1 = AgentIdentityManager(agent_id)
            personality = AgentPersonality(name="SaveTest")
            goals = AgentGoals(primary=["Test"])
            capabilities = AgentCapabilities()
            constraints = AgentConstraints()
            
            manager1.create(personality, goals, capabilities, constraints)
            
            # Load in new manager instance
            manager2 = AgentIdentityManager(agent_id)
            loaded = manager2.load()
            
            assert loaded is not None
            assert loaded.id == agent_id
            assert loaded.personality.name == "SaveTest"
        finally:
            identity_module.get_settings = original_get_settings


def test_agent_identity_manager_load_or_create_default():
    """Test load_or_create_default with defaults."""
    agent_id = uuid4()
    
    with TemporaryDirectory() as tmpdir:
        import ghostclaw.core.agent_sdk.agent_identity as identity_module
        original_get_settings = identity_module.get_settings
        
        class MockSettings:
            memory_base_dir = Path(tmpdir)
        
        try:
            identity_module.get_settings = lambda: MockSettings()
            
            manager = AgentIdentityManager(agent_id)
            identity = manager.load_or_create_default()
            
            assert identity.id == agent_id
            assert identity.personality.name == f"agent-{str(agent_id)[:8]}"
            assert len(identity.goals.primary) > 0
            assert len(identity.capabilities.strengths) > 0
        finally:
            identity_module.get_settings = original_get_settings


def test_agent_identity_manager_to_dict():
    """Test exporting identity as dictionary."""
    agent_id = uuid4()
    
    with TemporaryDirectory() as tmpdir:
        import ghostclaw.core.agent_sdk.agent_identity as identity_module
        original_get_settings = identity_module.get_settings
        
        class MockSettings:
            memory_base_dir = Path(tmpdir)
        
        try:
            identity_module.get_settings = lambda: MockSettings()
            
            manager = AgentIdentityManager(agent_id)
            manager.load_or_create_default()
            
            data = manager.to_dict()
            
            assert isinstance(data, dict)
            assert data["id"] == str(agent_id)
            assert "personality" in data
            assert "goals" in data
        finally:
            identity_module.get_settings = original_get_settings


def test_agent_identity_manager_get_summary():
    """Test getting human-readable summary."""
    agent_id = uuid4()
    
    with TemporaryDirectory() as tmpdir:
        import ghostclaw.core.agent_sdk.agent_identity as identity_module
        original_get_settings = identity_module.get_settings
        
        class MockSettings:
            memory_base_dir = Path(tmpdir)
        
        try:
            identity_module.get_settings = lambda: MockSettings()
            
            manager = AgentIdentityManager(agent_id)
            manager.load_or_create_default()
            
            summary = manager.get_summary()
            
            assert isinstance(summary, str)
            assert "Agent:" in summary
            assert "Personality" in summary
            assert "Goals" in summary
        finally:
            identity_module.get_settings = original_get_settings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
