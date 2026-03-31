"""
Agent Workspace Manager - Manages agent workspace and git operations.

This module provides the AgentWorkspaceManager class which handles:
- Workspace initialization and isolation per agent
- Git repository operations (clone, branch, commit, push)
- GitHub integration (PR creation, status checks)
- Workspace file operations (read, write, scan)
- Diff tracking and workspace cleanup
"""

import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .config import AgentSDKSettings


class GitConfig(BaseModel):
    """Git configuration for workspace operations."""
    
    user_name: str = Field(..., description="Git author name")
    user_email: str = Field(..., description="Git author email")
    auto_commit: bool = Field(default=True, description="Auto-commit changes")
    push_on_complete: bool = Field(default=False, description="Push to remote on completion")
    branch_prefix: str = Field(default="agent-", description="Prefix for agent branches")


class WorkspaceFile(BaseModel):
    """Representation of a file in the workspace."""
    
    path: str = Field(..., description="Relative path from workspace root")
    absolute_path: Path = Field(..., description="Absolute file path")
    size_bytes: int = Field(..., description="File size in bytes")
    created_at: datetime = Field(..., description="File creation time")
    modified_at: datetime = Field(..., description="Last modification time")
    is_directory: bool = Field(..., description="Whether this is a directory")
    is_git_tracked: bool = Field(default=False, description="Whether file is git tracked")


class GitCommit(BaseModel):
    """Representation of a git commit."""
    
    hash: str = Field(..., description="Commit hash")
    message: str = Field(..., description="Commit message")
    author: str = Field(..., description="Author name")
    timestamp: datetime = Field(..., description="Commit timestamp")
    files_changed: int = Field(..., description="Number of files changed")
    insertions: int = Field(..., description="Number of insertions")
    deletions: int = Field(..., description="Number of deletions")


class GitPullRequest(BaseModel):
    """Representation of a GitHub pull request."""
    
    title: str = Field(..., description="PR title")
    description: str = Field(..., description="PR description")
    branch_name: str = Field(..., description="Source branch name")
    target_branch: str = Field(default="develop", description="Target branch (default: develop)")
    labels: List[str] = Field(default_factory=list, description="PR labels")
    draft: bool = Field(default=False, description="Whether to open as draft PR")
    requested_reviewers: List[str] = Field(default_factory=list, description="Requested reviewers")


class AgentWorkspaceManager:
    """
    Manages agent workspace and git operations.
    
    Features:
    - Isolated workspace per agent
    - Git repository management
    - GitHub PR operations
    - File operations and workspace scanning
    - Automatic commit and push workflows
    """
    
    def __init__(
        self,
        agent_id: UUID,
        workspace_root: Optional[Path] = None,
        git_config: Optional[GitConfig] = None,
    ):
        """
        Initialize the workspace manager.
        
        Args:
            agent_id: Agent ID for workspace isolation
            workspace_root: Root directory for workspace (defaults to ~/.ghostclaw/workspaces)
            git_config: Git configuration for commits and pushes
        """
        self.agent_id = agent_id
        self.settings = AgentSDKSettings()
        
        # Setup workspace directory
        if workspace_root:
            self.workspace_root = workspace_root
        else:
            # Default to ~/.ghostclaw/workspaces/agent_id/
            self.workspace_root = Path.home() / ".ghostclaw" / "workspaces" / str(agent_id)
        
        # Ensure workspace directory exists
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        
        # Git configuration
        self.git_config = git_config or self._get_default_git_config()
        
        # Track current branch and repo state
        self._current_branch = "develop"
        self._repo_initialized = False
    
    def _get_default_git_config(self) -> GitConfig:
        """Get default git configuration from environment or defaults."""
        return GitConfig(
            user_name=os.getenv("GIT_USER_NAME", "Ghostclaw Agent"),
            user_email=os.getenv("GIT_USER_EMAIL", f"agent+{self.agent_id}@ghostclaw.local"),
        )
    
    def initialize_repo(self, repo_url: Optional[str] = None) -> bool:
        """
        Initialize or clone git repository.
        
        Args:
            repo_url: Optional repository URL to clone
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if already a git repo
            git_dir = self.workspace_root / ".git"
            if git_dir.exists():
                self._repo_initialized = True
                return True
            
            if repo_url:
                # Clone repository
                result = subprocess.run(
                    ["git", "clone", repo_url, str(self.workspace_root)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"Failed to clone: {result.stderr}")
            else:
                # Initialize empty repository
                result = subprocess.run(
                    ["git", "init"],
                    cwd=self.workspace_root,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"Failed to init: {result.stderr}")
            
            # Configure git user
            self._run_git_command(["config", "user.name", self.git_config.user_name])
            self._run_git_command(["config", "user.email", self.git_config.user_email])
            
            self._repo_initialized = True
            return True
        except Exception:
            return False
    
    def create_branch(self, branch_name: Optional[str] = None) -> Optional[str]:
        """
        Create and checkout a new branch.
        
        Args:
            branch_name: Optional custom branch name (defaults to agent-{timestamp})
        
        Returns:
            Created branch name or None on failure
        """
        try:
            if not self._repo_initialized:
                self.initialize_repo()
            
            if not branch_name:
                # Generate branch name
                timestamp = int(datetime.now().timestamp())
                branch_name = f"{self.git_config.branch_prefix}{timestamp}"
            
            # Create and checkout branch
            self._run_git_command(["checkout", "-b", branch_name])
            self._current_branch = branch_name
            return branch_name
        except Exception:
            return None
    
    def get_current_branch(self) -> str:
        """Get the current git branch."""
        return self._current_branch
    
    def commit_changes(
        self,
        message: str,
        files: Optional[List[str]] = None,
        allow_empty: bool = False,
    ) -> Optional[str]:
        """
        Commit changes to git.
        
        Args:
            message: Commit message
            files: Optional list of files to stage (defaults to all)
            allow_empty: Whether to allow empty commits
        
        Returns:
            Commit hash or None on failure
        """
        try:
            if not self._repo_initialized:
                self.initialize_repo()
            
            # Stage files
            if files:
                for file in files:
                    self._run_git_command(["add", file])
            else:
                self._run_git_command(["add", "."])
            
            # Commit
            cmd = ["commit", "-m", message]
            if allow_empty:
                cmd.append("--allow-empty")
            
            result = self._run_git_command(cmd)
            
            # Extract commit hash from output
            for line in result.split('\n'):
                if 'create mode' in line or 'changed' in line:
                    continue
                if line.strip():
                    return line.split()[-1] if line.split() else "committed"
            
            return "committed"
        except Exception:
            return None
    
    def push_changes(self, branch: Optional[str] = None, remote: str = "origin") -> bool:
        """
        Push changes to remote repository.
        
        Args:
            branch: Branch to push (defaults to current)
            remote: Remote name (defaults to 'origin')
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self._repo_initialized:
                return False
            
            branch = branch or self._current_branch
            self._run_git_command(["push", "-u", remote, branch])
            return True
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get repository status.
        
        Returns:
            Dict with status information
        """
        try:
            if not self._repo_initialized:
                return {"status": "not_initialized"}
            
            status_output = self._run_git_command(["status", "--porcelain"])
            
            staged = []
            unstaged = []
            untracked = []
            
            for line in status_output.split('\n'):
                if not line.strip():
                    continue
                
                status_code = line[:2]
                filename = line[3:]
                
                if status_code[0] in ['A', 'M', 'D']:
                    staged.append(filename)
                elif status_code[1] in ['M', 'D']:
                    unstaged.append(filename)
                elif status_code == '??':
                    untracked.append(filename)
            
            return {
                "status": "clean" if not any([staged, unstaged, untracked]) else "dirty",
                "current_branch": self._current_branch,
                "staged_files": staged,
                "unstaged_files": unstaged,
                "untracked_files": untracked,
            }
        except Exception:
            return {"status": "error"}
    
    def get_commit_history(self, limit: int = 10) -> List[GitCommit]:
        """
        Get recent commit history.
        
        Args:
            limit: Number of commits to retrieve
        
        Returns:
            List of GitCommit objects
        """
        try:
            if not self._repo_initialized:
                return []
            
            log_output = self._run_git_command([
                "log",
                f"--max-count={limit}",
                "--format=%H|%s|%an|%ai|%an",
            ])
            
            commits = []
            for line in log_output.split('\n'):
                if not line.strip():
                    continue
                
                parts = line.split('|')
                if len(parts) >= 5:
                    commits.append(GitCommit(
                        hash=parts[0][:7],
                        message=parts[1],
                        author=parts[2],
                        timestamp=datetime.fromisoformat(parts[3].replace(' ', 'T')),
                        files_changed=0,
                        insertions=0,
                        deletions=0,
                    ))
            
            return commits
        except Exception:
            return []
    
    def read_file(self, filepath: str) -> Optional[str]:
        """
        Read a file from the workspace.
        
        Args:
            filepath: Relative path from workspace root
        
        Returns:
            File contents or None on error
        """
        try:
            full_path = self.workspace_root / filepath
            if full_path.exists() and full_path.is_file():
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return None
        except Exception:
            return None
    
    def write_file(self, filepath: str, content: str, create_dirs: bool = True) -> bool:
        """
        Write content to a file in the workspace.
        
        Args:
            filepath: Relative path from workspace root
            content: Content to write
            create_dirs: Whether to create parent directories
        
        Returns:
            True if successful, False otherwise
        """
        try:
            full_path = self.workspace_root / filepath
            
            if create_dirs:
                full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        except Exception:
            return False
    
    def list_files(
        self,
        pattern: str = "*",
        recursive: bool = True,
        exclude_git: bool = True,
    ) -> List[WorkspaceFile]:
        """
        List files in the workspace.
        
        Args:
            pattern: Glob pattern for files
            recursive: Whether to search recursively
            exclude_git: Whether to exclude .git directory
        
        Returns:
            List of WorkspaceFile objects
        """
        try:
            files = []
            glob_method = "rglob" if recursive else "glob"
            
            for filepath in getattr(self.workspace_root, glob_method)(pattern):
                if exclude_git and ".git" in filepath.parts:
                    continue
                
                stat = filepath.stat()
                files.append(WorkspaceFile(
                    path=str(filepath.relative_to(self.workspace_root)),
                    absolute_path=filepath,
                    size_bytes=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    is_directory=filepath.is_dir(),
                    is_git_tracked=self._is_git_tracked(filepath),
                ))
            
            return files
        except Exception:
            return []
    
    def create_pull_request(
        self,
        pr: GitPullRequest,
        github_token: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a GitHub pull request.
        
        Args:
            pr: PullRequest object with PR details
            github_token: GitHub API token (reads from GITHUB_TOKEN env if not provided)
        
        Returns:
            PR details dict or None on failure
        """
        try:
            token = github_token or os.getenv("GITHUB_TOKEN")
            if not token:
                return None
            
            # Get remote URL
            remote_url = self._run_git_command(["config", "--get", "remote.origin.url"])
            
            # Parse owner/repo from URL
            # Handles both HTTPS and SSH URLs
            if "github.com" in remote_url:
                if remote_url.startswith("git@"):
                    # SSH: git@github.com:owner/repo.git
                    parts = remote_url.replace("git@github.com:", "").split("/")
                else:
                    # HTTPS: https://github.com/owner/repo.git
                    parts = remote_url.rstrip("/").split("/")
                
                owner = parts[-2]
                repo = parts[-1].replace(".git", "")
            else:
                return None
            
            # Create PR using GitHub API
            api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
            
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            
            data = {
                "title": pr.title,
                "body": pr.description,
                "head": pr.branch_name,
                "base": pr.target_branch,
                "draft": pr.draft,
            }
            
            req = urllib.request.Request(
                api_url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method="POST",
            )
            
            try:
                with urllib.request.urlopen(req) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    return {
                        "url": result.get("html_url"),
                        "number": result.get("number"),
                        "state": result.get("state"),
                    }
            except urllib.error.HTTPError:
                # Log error details
                return None
        except Exception:
            return None
    
    def cleanup(self, remove_repo: bool = False) -> bool:
        """
        Clean up workspace.
        
        Args:
            remove_repo: Whether to remove entire workspace directory
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Reset git state if repo exists
            if self._repo_initialized:
                try:
                    # Only try to reset and checkout if git is initialized
                    self._run_git_command(["reset", "--hard"])
                    # Try to checkout develop, but don't fail if it doesn't exist
                    try:
                        self._run_git_command(["checkout", "develop"])
                    except Exception:
                        pass  # develop branch might not exist in empty repo
                except Exception:
                    pass  # Ignore git errors during cleanup
            
            if remove_repo:
                import shutil
                shutil.rmtree(self.workspace_root, ignore_errors=True)
            
            return True
        except Exception:
            return False
    
    def get_workspace_size(self) -> int:
        """
        Get total size of workspace in bytes.
        
        Returns:
            Size in bytes
        """
        try:
            total_size = 0
            for file in self.list_files("**/*"):
                if not file.is_directory:
                    total_size += file.size_bytes
            return total_size
        except Exception:
            return 0
    
    # Private helper methods
    
    def _run_git_command(self, args: List[str]) -> str:
        """Run a git command in the workspace."""
        result = subprocess.run(
            ["git"] + args,
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Git command failed: {result.stderr}")
        
        return result.stdout.strip()
    
    def _is_git_tracked(self, filepath: Path) -> bool:
        """Check if a file is tracked by git."""
        try:
            if not self._repo_initialized:
                return False
            
            rel_path = filepath.relative_to(self.workspace_root)
            result = subprocess.run(
                ["git", "ls-files", str(rel_path)],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0 and result.stdout.strip() != ""
        except Exception:
            return False


__all__ = [
    "AgentWorkspaceManager",
    "GitConfig",
    "GitCommit",
    "GitPullRequest",
    "WorkspaceFile",
]
