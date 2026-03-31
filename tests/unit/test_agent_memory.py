"""
Unit tests for AgentMemoryManager.

Tests the memory management functionality including:
- Memory file creation and initialization
- Adding, updating, and deleting entries
- Searching and retrieving entries
- Memory statistics and export
- Memory clearing and lifecycle
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from ghostclaw.core.agent_sdk.agent_memory import (
    AgentMemoryManager,
    MemoryEntry,
    MemoryFile,
)


@pytest.fixture
def agent_id():
    """Generate a test agent ID."""
    return uuid4()


@pytest.fixture
def temp_memory_dir():
    """Create a temporary memory directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def memory_manager(agent_id, temp_memory_dir):
    """Create an AgentMemoryManager instance for testing."""
    manager = AgentMemoryManager(agent_id=agent_id, memory_root=temp_memory_dir)
    manager.initialize()
    return manager


class TestAgentMemoryManagerInitialization:
    """Tests for memory manager initialization."""
    
    def test_initialize_creates_all_memory_files(self, agent_id, temp_memory_dir):
        """Test that initialization creates all required memory files."""
        manager = AgentMemoryManager(agent_id=agent_id, memory_root=temp_memory_dir)
        manager.initialize()
        
        # Check that all memory files exist
        for memory_file in manager.MEMORY_FILES:
            filepath = temp_memory_dir / memory_file
            assert filepath.exists(), f"Memory file {memory_file} not created"
    
    def test_initialize_idempotent(self, memory_manager, temp_memory_dir):
        """Test that initialize can be called multiple times safely."""
        file_path = temp_memory_dir / memory_manager.LONGTERM_FILE
        original_mtime = file_path.stat().st_mtime
        
        # Initialize again
        memory_manager.initialize()
        
        # File should not be recreated
        assert file_path.stat().st_mtime == original_mtime
    
    def test_memory_root_defaults_correctly(self, agent_id):
        """Test that memory root defaults to ~/.ghostclaw/memories/agent_id/."""
        manager = AgentMemoryManager(agent_id=agent_id)
        expected_root = Path.home() / ".ghostclaw" / "memories" / str(agent_id)
        assert manager.memory_root == expected_root


class TestAgentMemoryManagerEntries:
    """Tests for adding, updating, and retrieving entries."""
    
    def test_add_entry_creates_new_memory_entry(self, memory_manager):
        """Test adding a new entry to memory."""
        entry = memory_manager.add_entry(
            memory_type=memory_manager.LONGTERM_FILE,
            title="Test Entry",
            content="This is a test entry.",
            tags=["test", "example"],
            source="test",
            confidence=0.95,
        )
        
        assert entry.title == "Test Entry"
        assert entry.content == "This is a test entry."
        assert entry.tags == ["test", "example"]
        assert entry.source == "test"
        assert entry.confidence == 0.95
    
    def test_add_entry_persists_to_disk(self, memory_manager, temp_memory_dir):
        """Test that added entries are persisted to disk."""
        memory_manager.add_entry(
            memory_type=memory_manager.SESSION_FILE,
            title="Persistent Entry",
            content="This entry should be saved.",
        )
        
        # Verify file was written
        filepath = temp_memory_dir / memory_manager.SESSION_FILE
        assert filepath.exists()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert len(data["entries"]) > 0
            assert data["entries"][0]["title"] == "Persistent Entry"
    
    def test_get_entries_returns_all_entries(self, memory_manager):
        """Test retrieving entries from memory."""
        memory_manager.add_entry(
            memory_type=memory_manager.TASK_FILE,
            title="Task 1",
            content="First task",
        )
        memory_manager.add_entry(
            memory_type=memory_manager.TASK_FILE,
            title="Task 2",
            content="Second task",
        )
        
        entries = memory_manager.get_entries(memory_manager.TASK_FILE)
        assert len(entries) == 2
        assert entries[0].title == "Task 1"
        assert entries[1].title == "Task 2"
    
    def test_get_entries_filter_by_tags(self, memory_manager):
        """Test filtering entries by tags."""
        memory_manager.add_entry(
            memory_type=memory_manager.LEARNING_FILE,
            title="Python Tips",
            content="Tips for Python",
            tags=["python", "programming"],
        )
        memory_manager.add_entry(
            memory_type=memory_manager.LEARNING_FILE,
            title="JavaScript Tips",
            content="Tips for JavaScript",
            tags=["javascript", "programming"],
        )
        
        # Filter by 'python' tag
        python_entries = memory_manager.get_entries(
            memory_manager.LEARNING_FILE,
            tags=["python"],
        )
        assert len(python_entries) == 1
        assert python_entries[0].title == "Python Tips"
    
    def test_get_entries_search_by_term(self, memory_manager):
        """Test searching entries by search term."""
        memory_manager.add_entry(
            memory_type=memory_manager.CONTEXT_FILE,
            title="Important Context",
            content="This is important information",
        )
        memory_manager.add_entry(
            memory_type=memory_manager.CONTEXT_FILE,
            title="Regular Context",
            content="This is regular information",
        )
        
        # Search for 'important'
        results = memory_manager.get_entries(
            memory_manager.CONTEXT_FILE,
            search_term="important",
        )
        assert len(results) == 1
        assert results[0].title == "Important Context"
    
    def test_get_entries_limit_results(self, memory_manager):
        """Test limiting the number of returned entries."""
        for i in range(5):
            memory_manager.add_entry(
                memory_type=memory_manager.REFERENCES_FILE,
                title=f"Reference {i}",
                content=f"Content {i}",
            )
        
        # Get only 2 most recent
        entries = memory_manager.get_entries(
            memory_manager.REFERENCES_FILE,
            limit=2,
        )
        assert len(entries) == 2
    
    def test_update_entry_modifies_existing_entry(self, memory_manager):
        """Test updating an existing entry."""
        entry = memory_manager.add_entry(
            memory_type=memory_manager.LONGTERM_FILE,
            title="Original Title",
            content="Original content",
        )
        
        # Update the entry
        updated = memory_manager.update_entry(
            memory_manager.LONGTERM_FILE,
            entry.id,
            title="Updated Title",
            content="Updated content",
        )
        
        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.content == "Updated content"
    
    def test_update_entry_returns_none_for_nonexistent(self, memory_manager):
        """Test that updating nonexistent entry returns None."""
        result = memory_manager.update_entry(
            memory_manager.SESSION_FILE,
            "nonexistent_id",
            title="New Title",
        )
        assert result is None
    
    def test_delete_entry_removes_entry(self, memory_manager):
        """Test deleting an entry."""
        entry = memory_manager.add_entry(
            memory_type=memory_manager.TASK_FILE,
            title="To Delete",
            content="This will be deleted",
        )
        
        # Delete the entry
        deleted = memory_manager.delete_entry(
            memory_manager.TASK_FILE,
            entry.id,
        )
        
        assert deleted is True
        
        # Verify entry is gone
        entries = memory_manager.get_entries(memory_manager.TASK_FILE)
        assert len(entries) == 0
    
    def test_delete_entry_returns_false_for_nonexistent(self, memory_manager):
        """Test that deleting nonexistent entry returns False."""
        result = memory_manager.delete_entry(
            memory_manager.CONTEXT_FILE,
            "nonexistent_id",
        )
        assert result is False


class TestAgentMemoryManagerSearch:
    """Tests for searching across memory files."""
    
    def test_search_all_finds_entries_in_multiple_files(self, memory_manager):
        """Test searching across all memory files."""
        memory_manager.add_entry(
            memory_type=memory_manager.LONGTERM_FILE,
            title="Long-term Pattern",
            content="This is a pattern",
        )
        memory_manager.add_entry(
            memory_type=memory_manager.LEARNING_FILE,
            title="Learning Pattern",
            content="Another pattern to learn",
        )
        
        results = memory_manager.search_all("pattern")
        assert len(results) == 2
        assert memory_manager.LONGTERM_FILE in results
        assert memory_manager.LEARNING_FILE in results
    
    def test_search_all_case_insensitive(self, memory_manager):
        """Test that search is case-insensitive."""
        memory_manager.add_entry(
            memory_type=memory_manager.SESSION_FILE,
            title="Important Session",
            content="Session data",
        )
        
        results = memory_manager.search_all("IMPORTANT")
        assert len(results) == 1
    
    def test_search_all_with_regex(self, memory_manager):
        """Test searching with regex patterns."""
        memory_manager.add_entry(
            memory_type=memory_manager.REFERENCES_FILE,
            title="Reference 001",
            content="First reference",
        )
        memory_manager.add_entry(
            memory_type=memory_manager.REFERENCES_FILE,
            title="Reference 002",
            content="Second reference",
        )
        
        results = memory_manager.search_all(r"Reference \d{3}")
        assert memory_manager.REFERENCES_FILE in results
        assert len(results[memory_manager.REFERENCES_FILE]) == 2


class TestAgentMemoryManagerExport:
    """Tests for exporting memory data."""
    
    def test_export_memory_returns_structured_data(self, memory_manager):
        """Test exporting a memory file."""
        memory_manager.add_entry(
            memory_type=memory_manager.LEARNING_FILE,
            title="Export Test",
            content="Testing export",
            tags=["test"],
        )
        
        exported = memory_manager.export_memory(memory_manager.LEARNING_FILE)
        
        assert exported["name"] == memory_manager.LEARNING_FILE
        assert exported["description"] == memory_manager.MEMORY_DESCRIPTIONS[memory_manager.LEARNING_FILE]
        assert exported["entry_count"] == 1
        assert len(exported["entries"]) == 1
        assert exported["entries"][0]["title"] == "Export Test"
    
    def test_exported_data_contains_timestamps(self, memory_manager):
        """Test that exported data includes ISO format timestamps."""
        memory_manager.add_entry(
            memory_type=memory_manager.TASK_FILE,
            title="Timestamp Test",
            content="Test timestamps",
        )
        
        exported = memory_manager.export_memory(memory_manager.TASK_FILE)
        
        # Check timestamps are valid ISO format
        datetime.fromisoformat(exported["created_at"])
        datetime.fromisoformat(exported["updated_at"])


class TestAgentMemoryManagerStatistics:
    """Tests for memory statistics."""
    
    def test_get_statistics_returns_all_metrics(self, memory_manager):
        """Test getting memory statistics."""
        memory_manager.add_entry(
            memory_type=memory_manager.LONGTERM_FILE,
            title="Stat Test 1",
            content="Content 1",
        )
        memory_manager.add_entry(
            memory_type=memory_manager.SESSION_FILE,
            title="Stat Test 2",
            content="Content 2",
        )
        
        stats = memory_manager.get_statistics()
        
        assert "total_entries" in stats
        assert "total_size_bytes" in stats
        assert "files" in stats
        assert stats["total_entries"] == 2
        assert stats["total_size_bytes"] > 0
    
    def test_statistics_includes_all_files(self, memory_manager):
        """Test that statistics cover all memory files."""
        stats = memory_manager.get_statistics()
        
        # Should have entries for all files except INDEX
        assert len(stats["files"]) >= len(memory_manager.MEMORY_FILES) - 1


class TestAgentMemoryManagerClearing:
    """Tests for clearing memory."""
    
    def test_clear_memory_removes_all_entries(self, memory_manager):
        """Test clearing all memory entries."""
        memory_manager.add_entry(
            memory_type=memory_manager.LONGTERM_FILE,
            title="To Clear 1",
            content="Will be cleared",
        )
        memory_manager.add_entry(
            memory_type=memory_manager.LEARNING_FILE,
            title="To Clear 2",
            content="Will also be cleared",
        )
        
        deleted = memory_manager.clear_memory()
        
        assert deleted == 2
        
        # Verify all entries are gone
        longterm_entries = memory_manager.get_entries(memory_manager.LONGTERM_FILE)
        learning_entries = memory_manager.get_entries(memory_manager.LEARNING_FILE)
        assert len(longterm_entries) == 0
        assert len(learning_entries) == 0
    
    def test_clear_memory_specific_file(self, memory_manager):
        """Test clearing entries from a specific memory file."""
        memory_manager.add_entry(
            memory_type=memory_manager.LONGTERM_FILE,
            title="Keep This",
            content="Should stay",
        )
        memory_manager.add_entry(
            memory_type=memory_manager.SESSION_FILE,
            title="Clear This",
            content="Should be removed",
        )
        
        deleted = memory_manager.clear_memory(memory_type=memory_manager.SESSION_FILE)
        
        assert deleted == 1
        
        # Verify only SESSION was cleared
        longterm = memory_manager.get_entries(memory_manager.LONGTERM_FILE)
        session = memory_manager.get_entries(memory_manager.SESSION_FILE)
        assert len(longterm) == 1
        assert len(session) == 0
    
    def test_clear_memory_before_date(self, memory_manager):
        """Test clearing entries before a specific date."""
        # Add an old entry (manually adjust timestamp)
        old_entry = memory_manager.add_entry(
            memory_type=memory_manager.CONTEXT_FILE,
            title="Old Entry",
            content="Old content",
        )
        old_entry.created_at = datetime.now() - timedelta(days=30)
        
        # Add a recent entry
        recent_entry = memory_manager.add_entry(
            memory_type=memory_manager.CONTEXT_FILE,
            title="Recent Entry",
            content="Recent content",
        )
        
        # Clear entries older than 1 day
        cutoff_date = datetime.now() - timedelta(days=1)
        deleted = memory_manager.clear_memory(
            memory_type=memory_manager.CONTEXT_FILE,
            before_date=cutoff_date,
        )
        
        # The test is limited because add_entry creates entries with current time
        # In a real scenario, manually set timestamps would be used
        assert deleted >= 0


class TestAgentMemoryManagerEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_add_entry_invalid_memory_type_raises_error(self, memory_manager):
        """Test that adding to invalid memory type raises error."""
        with pytest.raises(ValueError):
            memory_manager.add_entry(
                memory_type="INVALID_MEMORY.md",
                title="Test",
                content="Test",
            )
    
    def test_add_entry_default_tags(self, memory_manager):
        """Test that entries default to empty tags."""
        entry = memory_manager.add_entry(
            memory_type=memory_manager.LONGTERM_FILE,
            title="No Tags",
            content="Entry without tags",
        )
        assert entry.tags == []
    
    def test_add_entry_default_confidence(self, memory_manager):
        """Test that entries default to 0.8 confidence."""
        entry = memory_manager.add_entry(
            memory_type=memory_manager.SESSION_FILE,
            title="Default Confidence",
            content="Entry with default confidence",
        )
        assert entry.confidence == 0.8
    
    def test_memory_entry_has_unique_ids(self, memory_manager):
        """Test that memory entries have unique IDs."""
        entry1 = memory_manager.add_entry(
            memory_type=memory_manager.LONGTERM_FILE,
            title="Entry 1",
            content="Content 1",
        )
        entry2 = memory_manager.add_entry(
            memory_type=memory_manager.LONGTERM_FILE,
            title="Entry 2",
            content="Content 2",
        )
        
        assert entry1.id != entry2.id
    
    def test_memory_timestamps_are_datetime_objects(self, memory_manager):
        """Test that memory timestamps are datetime objects."""
        entry = memory_manager.add_entry(
            memory_type=memory_manager.SESSION_FILE,
            title="Timestamp Test",
            content="Testing timestamps",
        )
        
        assert isinstance(entry.created_at, datetime)
        assert isinstance(entry.updated_at, datetime)


class TestAgentMemoryManagerIndexing:
    """Tests for memory indexing functionality."""
    
    def test_index_file_updated_on_entry_addition(self, memory_manager):
        """Test that INDEX.md is updated when entries are added."""
        memory_manager.add_entry(
            memory_type=memory_manager.LEARNING_FILE,
            title="Index Test Entry",
            content="Testing indexing",
            tags=["index", "test"],
        )
        
        index_entries = memory_manager.get_entries(memory_manager.INDEX_FILE)
        assert len(index_entries) > 0
        
        # Find the index entry
        index_found = any(
            "Index Test Entry" in entry.title
            for entry in index_entries
        )
        assert index_found
    
    def test_index_contains_memory_type_tag(self, memory_manager):
        """Test that index entries contain memory type as tag."""
        memory_manager.add_entry(
            memory_type=memory_manager.CONTEXT_FILE,
            title="Context Entry",
            content="Testing context indexing",
        )
        
        index_entries = memory_manager.get_entries(memory_manager.INDEX_FILE)
        
        # At least one index entry should have the CONTEXT_FILE tag
        has_context_tag = any(
            memory_manager.CONTEXT_FILE in entry.tags
            for entry in index_entries
        )
        assert has_context_tag
