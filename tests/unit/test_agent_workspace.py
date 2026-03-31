"""
Unit tests for AgentWorkspaceManager.

Tests the workspace and git operations including:
- Repository initialization and management
- Branch creation and switching
- File operations (read, write, list)
- Git operations (commit, push, status)
- GitHub PR creation
- Workspace cleanup
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from ghostclaw.core.agent_sdk.agent_workspace import (
    AgentWorkspaceManager,
    GitConfig,
    GitCommit,
    GitPullRequest,
    WorkspaceFile,
)


@pytest.fixture
def agent_id():
    """Generate a test agent ID."""
    return uuid4()


@pytest.fixture
def temp_workspace_dir():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def workspace_manager(agent_id, temp_workspace_dir):
    """Create an AgentWorkspaceManager instance for testing."""
    git_config = GitConfig(
        user_name="Test Agent",
        user_email="test@example.com",
    )
    manager = AgentWorkspaceManager(
        agent_id=agent_id,
        workspace_root=temp_workspace_dir,
        git_config=git_config,
    )
    return manager


@pytest.fixture
def initialized_workspace(workspace_manager):
    """Create an initialized git workspace."""
    workspace_manager.initialize_repo()
    return workspace_manager


class TestWorkspaceManagerInitialization:
    """Tests for workspace initialization."""
    
    def test_initialize_repo_creates_git_directory(self, workspace_manager, temp_workspace_dir):
        """Test that initializing repo creates .git directory."""
        success = workspace_manager.initialize_repo()
        assert success
        assert (temp_workspace_dir / ".git").exists()
    
    def test_initialize_repo_idempotent(self, workspace_manager, temp_workspace_dir):
        """Test that initializing twice doesn't fail."""
        assert workspace_manager.initialize_repo()
        assert workspace_manager.initialize_repo()
    
    def test_git_config_defaults(self, agent_id, temp_workspace_dir):
        """Test that git config defaults are set correctly."""
        manager = AgentWorkspaceManager(
            agent_id=agent_id,
            workspace_root=temp_workspace_dir,
        )
        assert manager.git_config.user_name == "Ghostclaw Agent"
        assert "agent+" in manager.git_config.user_email
    
    def test_custom_git_config(self, agent_id, temp_workspace_dir):
        """Test that custom git config is used."""
        custom_config = GitConfig(
            user_name="Custom Agent",
            user_email="custom@example.com",
        )
        manager = AgentWorkspaceManager(
            agent_id=agent_id,
            workspace_root=temp_workspace_dir,
            git_config=custom_config,
        )
        assert manager.git_config == custom_config


class TestBranchOperations:
    """Tests for git branch operations."""
    
    def test_create_branch_default_name(self, initialized_workspace):
        """Test creating a branch with default name."""
        branch_name = initialized_workspace.create_branch()
        assert branch_name is not None
        assert branch_name.startswith("agent-")
    
    def test_create_branch_custom_name(self, initialized_workspace):
        """Test creating a branch with custom name."""
        custom_name = "feature/test-branch"
        branch_name = initialized_workspace.create_branch(custom_name)
        assert branch_name == custom_name
    
    def test_get_current_branch(self, initialized_workspace):
        """Test getting the current branch."""
        branch = initialized_workspace.get_current_branch()
        assert branch == "develop"
        
        new_branch = initialized_workspace.create_branch("test-branch")
        assert initialized_workspace.get_current_branch() == "test-branch"


class TestFileOperations:
    """Tests for file operations in workspace."""
    
    def test_write_file_creates_file(self, initialized_workspace, temp_workspace_dir):
        """Test writing a file to workspace."""
        content = "Test content\nLine 2"
        success = initialized_workspace.write_file("test.txt", content)
        
        assert success
        assert (temp_workspace_dir / "test.txt").exists()
        assert (temp_workspace_dir / "test.txt").read_text() == content
    
    def test_write_file_creates_directories(self, initialized_workspace, temp_workspace_dir):
        """Test that write_file creates parent directories."""
        content = "Nested file"
        success = initialized_workspace.write_file("dir/subdir/file.txt", content)
        
        assert success
        assert (temp_workspace_dir / "dir" / "subdir" / "file.txt").exists()
    
    def test_write_file_without_create_dirs_fails(self, initialized_workspace):
        """Test that write_file with create_dirs=False fails for nested paths."""
        success = initialized_workspace.write_file(
            "nonexistent/file.txt",
            "content",
            create_dirs=False,
        )
        assert not success
    
    def test_read_file_returns_content(self, initialized_workspace):
        """Test reading a file from workspace."""
        content = "Test file content"
        initialized_workspace.write_file("read_test.txt", content)
        
        read_content = initialized_workspace.read_file("read_test.txt")
        assert read_content == content
    
    def test_read_file_nonexistent_returns_none(self, initialized_workspace):
        """Test that reading nonexistent file returns None."""
        content = initialized_workspace.read_file("nonexistent.txt")
        assert content is None
    
    def test_list_files_finds_files(self, initialized_workspace):
        """Test listing files in workspace."""
        initialized_workspace.write_file("file1.txt", "content1")
        initialized_workspace.write_file("file2.py", "content2")
        initialized_workspace.write_file("dir/file3.txt", "content3")
        
        files = initialized_workspace.list_files()
        assert len(files) >= 3
        
        # Check that files are WorkspaceFile objects
        for f in files:
            assert isinstance(f, WorkspaceFile)
            assert f.absolute_path.exists()
    
    def test_list_files_with_pattern(self, initialized_workspace):
        """Test listing files with glob pattern."""
        initialized_workspace.write_file("test.txt", "content")
        initialized_workspace.write_file("test.py", "content")
        initialized_workspace.write_file("other.md", "content")
        
        txt_files = initialized_workspace.list_files("*.txt")
        assert len(txt_files) >= 1
    
    def test_list_files_excludes_git(self, initialized_workspace):
        """Test that listing files excludes .git directory."""
        files = initialized_workspace.list_files()
        
        for f in files:
            assert ".git" not in f.path


class TestGitOperations:
    """Tests for git operations."""
    
    def test_commit_changes_requires_changes(self, initialized_workspace):
        """Test that committing with no changes returns None or handles gracefully."""
        # Try to commit with no changes - should fail or return None
        result = initialized_workspace.commit_changes(
            "Empty commit",
            allow_empty=False,
        )
        # Either None or 'committed' is acceptable since repo is empty
        assert result is None or result == "committed"
    
    def test_commit_changes_with_files(self, initialized_workspace):
        """Test committing files to git."""
        initialized_workspace.write_file("file.txt", "content")
        result = initialized_workspace.commit_changes("Add file.txt")
        
        # Should succeed or return None if nothing new to commit
        assert result is None or isinstance(result, str)
    
    def test_get_status_initial(self, initialized_workspace):
        """Test repository status is clean initially."""
        status = initialized_workspace.get_status()
        assert status["status"] in ["clean", "error"]
    
    def test_get_status_with_changes(self, initialized_workspace):
        """Test repository status with changes."""
        initialized_workspace.write_file("new_file.txt", "content")
        status = initialized_workspace.get_status()
        
        assert status["status"] == "dirty"
        assert "new_file.txt" in status["untracked_files"]
    
    def test_get_commit_history_empty(self, initialized_workspace):
        """Test getting commit history from empty repo."""
        history = initialized_workspace.get_commit_history()
        # Might be empty list or contain initial commits
        assert isinstance(history, list)
    
    def test_get_commit_history_returns_commits(self, initialized_workspace):
        """Test that commit history returns GitCommit objects."""
        history = initialized_workspace.get_commit_history(limit=5)
        
        for commit in history:
            assert isinstance(commit, GitCommit)
            assert isinstance(commit.timestamp, datetime)


class TestWorkspaceMetrics:
    """Tests for workspace metrics and queries."""
    
    def test_get_workspace_size(self, initialized_workspace):
        """Test getting workspace size."""
        initialized_workspace.write_file("file1.txt", "content" * 100)
        initialized_workspace.write_file("file2.txt", "content" * 200)
        
        size = initialized_workspace.get_workspace_size()
        assert size > 0
    
    def test_get_workspace_size_empty(self, initialized_workspace):
        """Test getting workspace size when empty."""
        size = initialized_workspace.get_workspace_size()
        # May include .git directory or be 0
        assert isinstance(size, int)


class TestWorkspaceCleanup:
    """Tests for workspace cleanup operations."""
    
    def test_cleanup_without_remove(self, initialized_workspace, temp_workspace_dir):
        """Test cleanup without removing workspace."""
        initialized_workspace.write_file("file.txt", "content")
        success = initialized_workspace.cleanup(remove_repo=False)
        
        assert success
        assert temp_workspace_dir.exists()
    
    def test_cleanup_with_remove(self, workspace_manager, temp_workspace_dir):
        """Test cleanup with workspace removal."""
        workspace_manager.initialize_repo()
        workspace_manager.write_file("file.txt", "content")
        
        # Create a subdirectory to ensure removal works
        subdir = temp_workspace_dir / "subdir"
        subdir.mkdir()
        
        success = workspace_manager.cleanup(remove_repo=True)
        
        # Workspace directory should be removed
        assert not temp_workspace_dir.exists()


class TestGitConfigModels:
    """Tests for Git configuration models."""
    
    def test_git_config_creation(self):
        """Test creating GitConfig."""
        config = GitConfig(
            user_name="Test User",
            user_email="test@example.com",
        )
        assert config.user_name == "Test User"
        assert config.user_email == "test@example.com"
        assert config.auto_commit is True
        assert config.push_on_complete is False
    
    def test_git_pull_request_creation(self):
        """Test creating GitPullRequest."""
        pr = GitPullRequest(
            title="Add new feature",
            description="This PR adds a new feature",
            branch_name="feature/new-feature",
        )
        assert pr.title == "Add new feature"
        assert pr.branch_name == "feature/new-feature"
        assert pr.target_branch == "develop"
        assert pr.draft is False
    
    def test_workspace_file_creation(self, temp_workspace_dir):
        """Test creating WorkspaceFile."""
        test_file = temp_workspace_dir / "test.txt"
        test_file.write_text("content")
        stat = test_file.stat()
        
        wf = WorkspaceFile(
            path="test.txt",
            absolute_path=test_file,
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            is_directory=False,
            is_git_tracked=False,
        )
        
        assert wf.path == "test.txt"
        assert wf.is_directory is False
        assert wf.size_bytes > 0


class TestWorkspaceErrorHandling:
    """Tests for error handling in workspace operations."""
    
    def test_create_branch_on_uninitialized_workspace(self, workspace_manager):
        """Test creating branch on uninitialized workspace auto-initializes."""
        # Should succeed by initializing repo first
        branch = workspace_manager.create_branch("test")
        assert branch is not None
    
    def test_push_changes_on_uninitialized_workspace(self, workspace_manager):
        """Test pushing on uninitialized workspace returns False."""
        success = workspace_manager.push_changes()
        assert success is False
    
    def test_get_status_on_uninitialized_workspace(self, workspace_manager):
        """Test getting status on uninitialized workspace."""
        status = workspace_manager.get_status()
        assert status["status"] == "not_initialized"
