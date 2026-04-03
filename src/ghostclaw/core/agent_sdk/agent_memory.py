"""
Agent Memory Manager - Manages persistent and session-based memory storage for agents.

This module provides the AgentMemoryManager class which handles:
- Creation and management of memory files
- Structured memory storage (long-term, session, task, learning, etc.)
- Memory search and retrieval
- Memory export and backup
- Memory lifecycle management
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .config import AgentSDKSettings
from .models import AgentIdentity


class MemoryEntry(BaseModel):
    """A single memory entry with metadata."""
    
    id: str = Field(..., description="Unique entry ID")
    title: str = Field(..., description="Entry title/summary")
    content: str = Field(..., description="Full entry content")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    source: Optional[str] = Field(None, description="Source of the memory (task, conversation, etc.)")
    confidence: float = Field(default=0.8, description="Confidence level (0.0-1.0)")


class MemoryFile(BaseModel):
    """Structure for a memory file with metadata and entries."""
    
    name: str = Field(..., description="Memory file name")
    description: str = Field(..., description="File description and purpose")
    entries: List[MemoryEntry] = Field(default_factory=list, description="Memory entries")
    version: str = Field(default="1.0", description="File format version")
    created_at: datetime = Field(default_factory=datetime.now, description="File creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")


class AgentMemoryManager:
    """
    Manages persistent and session-based memory storage for agents.
    
    Memory structure:
    - Long-term Memory: Persistent facts and patterns across all sessions
    - Session Memory: Context-specific to current conversation/session
    - Task Memory: Progress and notes for current task
    - Learning Memory: Patterns, best practices, and lessons learned
    - Context Memory: Current working context and state
    - References Memory: Links and external knowledge references
    - Index Memory: Searchable catalog of all memories
    """
    
    # Memory file names
    MEMORY_DIR = "memories"
    LONGTERM_FILE = "LONGTERM.md"
    SESSION_FILE = "SESSION.md"
    TASK_FILE = "TASK.md"
    LEARNING_FILE = "LEARNING.md"
    CONTEXT_FILE = "CONTEXT.md"
    REFERENCES_FILE = "REFERENCES.md"
    INDEX_FILE = "INDEX.md"
    
    # All memory files
    MEMORY_FILES = [
        LONGTERM_FILE,
        SESSION_FILE,
        TASK_FILE,
        LEARNING_FILE,
        CONTEXT_FILE,
        REFERENCES_FILE,
        INDEX_FILE,
    ]
    
    MEMORY_DESCRIPTIONS = {
        LONGTERM_FILE: "Persistent facts, patterns, and insights across all sessions",
        SESSION_FILE: "Current conversation and session-specific context",
        TASK_FILE: "Progress, notes, and state for current task",
        LEARNING_FILE: "Learned patterns, best practices, and lessons",
        CONTEXT_FILE: "Current working context and state variables",
        REFERENCES_FILE: "External links, documents, and knowledge references",
        INDEX_FILE: "Searchable index and catalog of all memories",
    }
    
    def __init__(self, agent_id: UUID, memory_root: Optional[Path] = None):
        """
        Initialize the memory manager.
        
        Args:
            agent_id: Agent ID for memory organization
            memory_root: Root directory for memory storage (defaults to ~/.ghostclaw/memories)
        """
        self.agent_id = agent_id
        self.settings = AgentSDKSettings()
        
        if memory_root:
            self.memory_root = memory_root
        else:
            # Default to ~/.ghostclaw/memories/agent_id/
            self.memory_root = Path.home() / ".ghostclaw" / "memories" / str(agent_id)
        
        # Ensure memory directory exists
        self.memory_root.mkdir(parents=True, exist_ok=True)
        
        # Memory store (in-memory cache)
        self._memory_cache: Dict[str, MemoryFile] = {}
        self._is_initialized = False
    
    def initialize(self) -> None:
        """Initialize memory files and structure."""
        if self._is_initialized:
            return
        
        for memory_file in self.MEMORY_FILES:
            filepath = self.memory_root / memory_file
            if not filepath.exists():
                # Create new memory file
                memory = MemoryFile(
                    name=memory_file,
                    description=self.MEMORY_DESCRIPTIONS[memory_file],
                )
                self._save_memory_file(memory_file, memory)
        
        self._is_initialized = True
    
    def add_entry(
        self,
        memory_type: str,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
        confidence: float = 0.8,
    ) -> MemoryEntry:
        """
        Add a new entry to a memory file.
        
        Args:
            memory_type: Type of memory file (LONGTERM_FILE, SESSION_FILE, etc.)
            title: Entry title
            content: Entry content
            tags: Optional tags for categorization
            source: Optional source of the memory
            confidence: Confidence level (0.0-1.0)
        
        Returns:
            Created MemoryEntry
        """
        if not self._is_initialized:
            self.initialize()
        
        if memory_type not in self.MEMORY_FILES:
            raise ValueError(f"Invalid memory type: {memory_type}")
        
        # Load memory file
        memory = self._load_memory_file(memory_type)
        
        # Create entry
        entry_id = f"{memory_type.split('.')[0].lower()}_{len(memory.entries)}_{int(datetime.now().timestamp())}"
        entry = MemoryEntry(
            id=entry_id,
            title=title,
            content=content,
            tags=tags or [],
            source=source,
            confidence=confidence,
        )
        
        memory.entries.append(entry)
        memory.updated_at = datetime.now()
        
        # Save updated memory file
        self._save_memory_file(memory_type, memory)
        
        # Update index
        self._update_index_entry(memory_type, entry)
        
        return entry
    
    def get_entries(
        self,
        memory_type: str,
        tags: Optional[List[str]] = None,
        search_term: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[MemoryEntry]:
        """
        Retrieve entries from a memory file.
        
        Args:
            memory_type: Type of memory file
            tags: Optional filter by tags (matches any)
            search_term: Optional search in title/content
            limit: Optional limit on results
        
        Returns:
            List of matching MemoryEntry objects
        """
        if not self._is_initialized:
            self.initialize()
        
        memory = self._load_memory_file(memory_type)
        entries = memory.entries
        
        # Filter by tags
        if tags:
            entries = [
                e for e in entries 
                if any(tag in e.tags for tag in tags)
            ]
        
        # Filter by search term (case-insensitive)
        if search_term:
            pattern = re.compile(search_term, re.IGNORECASE)
            entries = [
                e for e in entries
                if pattern.search(e.title) or pattern.search(e.content)
            ]
        
        # Limit results
        if limit:
            entries = entries[-limit:]  # Return most recent N entries
        
        return entries
    
    def update_entry(
        self,
        memory_type: str,
        entry_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[MemoryEntry]:
        """
        Update an existing memory entry.
        
        Args:
            memory_type: Type of memory file
            entry_id: Entry ID to update
            title: Optional new title
            content: Optional new content
            tags: Optional new tags
        
        Returns:
            Updated MemoryEntry or None if not found
        """
        if not self._is_initialized:
            self.initialize()
        
        memory = self._load_memory_file(memory_type)
        
        for entry in memory.entries:
            if entry.id == entry_id:
                if title:
                    entry.title = title
                if content:
                    entry.content = content
                if tags:
                    entry.tags = tags
                entry.updated_at = datetime.now()
                
                # Save updated memory file
                self._save_memory_file(memory_type, memory)
                return entry
        
        return None
    
    def delete_entry(self, memory_type: str, entry_id: str) -> bool:
        """
        Delete a memory entry.
        
        Args:
            memory_type: Type of memory file
            entry_id: Entry ID to delete
        
        Returns:
            True if deleted, False if not found
        """
        if not self._is_initialized:
            self.initialize()
        
        memory = self._load_memory_file(memory_type)
        initial_count = len(memory.entries)
        
        memory.entries = [e for e in memory.entries if e.id != entry_id]
        
        if len(memory.entries) < initial_count:
            memory.updated_at = datetime.now()
            self._save_memory_file(memory_type, memory)
            return True
        
        return False
    
    def search_all(
        self,
        search_term: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, List[MemoryEntry]]:
        """
        Search across all memory files.
        
        Args:
            search_term: Search term (regex supported)
            tags: Optional filter by tags
        
        Returns:
            Dict mapping memory type to matching entries
        """
        if not self._is_initialized:
            self.initialize()
        
        results = {}
        pattern = re.compile(search_term, re.IGNORECASE)
        
        for memory_file in self.MEMORY_FILES:
            if memory_file == self.INDEX_FILE:
                continue
            
            entries = self.get_entries(memory_file, tags=tags)
            matching = [
                e for e in entries
                if pattern.search(e.title) or pattern.search(e.content)
            ]
            
            if matching:
                results[memory_file] = matching
        
        return results
    
    def export_memory(self, memory_type: str) -> Dict[str, Any]:
        """
        Export a memory file as a dictionary.
        
        Args:
            memory_type: Type of memory file
        
        Returns:
            Dictionary representation of the memory file
        """
        if not self._is_initialized:
            self.initialize()
        
        memory = self._load_memory_file(memory_type)
        return {
            "name": memory.name,
            "description": memory.description,
            "version": memory.version,
            "created_at": memory.created_at.isoformat(),
            "updated_at": memory.updated_at.isoformat(),
            "entry_count": len(memory.entries),
            "entries": [
                {
                    "id": e.id,
                    "title": e.title,
                    "content": e.content,
                    "tags": e.tags,
                    "created_at": e.created_at.isoformat(),
                    "updated_at": e.updated_at.isoformat(),
                    "source": e.source,
                    "confidence": e.confidence,
                }
                for e in memory.entries
            ],
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics across all memory files.
        
        Returns:
            Statistics dictionary
        """
        if not self._is_initialized:
            self.initialize()
        
        stats = {
            "total_entries": 0,
            "total_size_bytes": 0,
            "files": {},
            "agent_id": str(self.agent_id),
            "memory_root": str(self.memory_root),
        }
        
        for memory_file in self.MEMORY_FILES:
            if memory_file == self.INDEX_FILE:
                continue
            
            try:
                memory = self._load_memory_file(memory_file)
                file_entries = len(memory.entries)
                file_size = len(memory.model_dump_json().encode('utf-8'))
                
                stats["files"][memory_file] = {
                    "entries": file_entries,
                    "size_bytes": file_size,
                }
                stats["total_entries"] += file_entries
                stats["total_size_bytes"] += file_size
            except Exception as e:
                stats["files"][memory_file] = {"error": str(e)}
        
        return stats
    
    def clear_memory(
        self,
        memory_type: Optional[str] = None,
        before_date: Optional[datetime] = None,
    ) -> int:
        """
        Clear memory entries.
        
        Args:
            memory_type: Specific file to clear, or None for all
            before_date: Only delete entries before this date
        
        Returns:
            Number of entries deleted
        """
        if not self._is_initialized:
            self.initialize()
        
        deleted_count = 0
        files_to_clear = [memory_type] if memory_type else self.MEMORY_FILES
        
        for memory_file in files_to_clear:
            if memory_file == self.INDEX_FILE:
                continue
            
            memory = self._load_memory_file(memory_file)
            
            if before_date:
                # Delete entries older than before_date
                original_count = len(memory.entries)
                memory.entries = [
                    e for e in memory.entries
                    if e.created_at >= before_date
                ]
                deleted_count += original_count - len(memory.entries)
            else:
                # Delete all entries
                deleted_count += len(memory.entries)
                memory.entries = []
            
            file_deleted = (original_count - len(memory.entries)) if before_date else (deleted_count - (deleted_count - len(memory.entries) if not before_date else 0))
            if len(memory.entries) == 0 or (before_date and original_count != len(memory.entries)) or (not before_date):
                memory.updated_at = datetime.now()
                self._save_memory_file(memory_file, memory)
        
        return deleted_count
    
    # Private helper methods
    
    def _load_memory_file(self, memory_type: str) -> MemoryFile:
        """Load a memory file from disk or cache."""
        # Return from cache if available
        if memory_type in self._memory_cache:
            return self._memory_cache[memory_type]
        
        filepath = self.memory_root / memory_type
        
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                # Try to load as JSON first (structured format)
                try:
                    data = json.load(f)
                    memory = MemoryFile(**data)
                except (json.JSONDecodeError, ValueError):
                    # If JSON fails, create empty memory
                    memory = MemoryFile(
                        name=memory_type,
                        description=self.MEMORY_DESCRIPTIONS.get(memory_type, ""),
                    )
        else:
            # Create new memory file
            memory = MemoryFile(
                name=memory_type,
                description=self.MEMORY_DESCRIPTIONS.get(memory_type, ""),
            )
        
        # Cache the memory
        self._memory_cache[memory_type] = memory
        return memory
    
    def _save_memory_file(self, memory_type: str, memory: MemoryFile) -> None:
        """Save a memory file to disk and cache."""
        filepath = self.memory_root / memory_type
        
        # Save as JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(memory.model_dump(mode='json'), f, indent=2, default=str)
        
        # Update cache
        self._memory_cache[memory_type] = memory
    
    def _update_index_entry(self, memory_type: str, entry: MemoryEntry) -> None:
        """Update the index file with new entry metadata."""
        index = self._load_memory_file(self.INDEX_FILE)
        
        # Create index entry
        index_entry = MemoryEntry(
            id=f"idx_{entry.id}",
            title=f"[{memory_type}] {entry.title}",
            content=f"Entry: {entry.id}\nMemory Type: {memory_type}\nTags: {', '.join(entry.tags)}",
            tags=["index", memory_type] + entry.tags,
            source=f"Indexed from {memory_type}",
        )
        
        index.entries.append(index_entry)
        index.updated_at = datetime.now()
        
        self._save_memory_file(self.INDEX_FILE, index)


__all__ = ["AgentMemoryManager", "MemoryEntry", "MemoryFile"]
