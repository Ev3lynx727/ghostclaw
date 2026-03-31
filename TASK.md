# Phase 1 Implementation Tasks

**Status**: Planning | **Target**: Weeks 1-2 | **Date**: 2026-03-31 | **Version**: v0.3.0 Foundation

---

## Overview

Phase 1 delivers **foundational agent system** for Ghostclaw v0.3.0 with persistent identity, memory management, workspace isolation, and interactive CLI architecture.

v0.3.0 is a **transitional foundation** release:
- ✅ Agent SDK scaffold structure in place
- ✅ Architecture documented (4 docs)
- ✅ Implementation roadmap created (TASK.md)
- ⏳ Implementations pending (Tasks 2-10)

### Deliverables
- ✅ Agent SDK module (`src/ghostclaw/core/agent-sdk/`)
- ✅ Agent identity & memory system
- ✅ Workspace isolation (git branches)
- ✅ Extended GhostAgent with `chat_turn()` method
- ✅ CLI interactive command (`ghostclaw agent spawn`)
- ✅ Local knowledge database (SQLite)

### Architecture (Agent-SDK)
```
src/ghostclaw/core/agent-sdk/
├── __init__.py
├── agent_identity.py       # Agent personality, goals, strengths
├── agent_memory.py         # Memory file management (IDENTITY, HOOK, USER, etc)
├── agent_workspace.py      # Git workspace isolation (agent/workspaces/{id})
└── agent_session.py        # Session state management
```

---

## Task 1: Directory & Module Setup

**Status**: ⏳ Not Started | **Priority**: 🔴 Critical | **Est. Hours**: 1

### Description
Create new agent-sdk module structure with proper __init__.py files and package metadata.

### Subtasks

- [ ] **1.1** Create directory: `src/ghostclaw/core/agent-sdk/`
- [ ] **1.2** Create `src/ghostclaw/core/agent-sdk/__init__.py`
  - Export main classes: `Agent`, `AgentIdentity`, `AgentMemory`, `AgentWorkspace`, `AgentSession`
  - Add docstring explaining agent-sdk purpose
  
- [ ] **1.3** Update `src/ghostclaw/core/__init__.py`
  - Import agent-sdk exports
  - Add to documentation

- [ ] **1.4** Create `src/ghostclaw/core/agent-sdk/py.typed`
  - Enable type checking for agent-sdk module

### Files Created
- `src/ghostclaw/core/agent-sdk/__init__.py`
- `src/ghostclaw/core/agent-sdk/py.typed`

### Tests Required
- [ ] Import test: `from ghostclaw.core.agent_sdk import Agent`
- [ ] Type checking: mypy passes for imports

---

## Task 2: Agent Identity Model

**Status**: ⏳ Not Started | **Priority**: 🔴 Critical | **Est. Hours**: 3

### Description
Create `AgentIdentity` class representing agent personality, goals, strengths, and weaknesses.

### Subtasks

- [ ] **2.1** Create `src/ghostclaw/core/agent-sdk/models.py`
  - Define dataclasses:
    - `AgentPersonality` (name, style, communication, decision-making)
    - `AgentGoals` (list of goals with priority)
    - `AgentCapabilities` (strengths, weaknesses, specialized knowledge)
    - `AgentConstraints` (hard rules, boundaries)

- [ ] **2.2** Create `src/ghostclaw/core/agent-sdk/agent_identity.py`
  - `AgentIdentity` class with methods:
    - `load_from_file(path)` - Load IDENTITY.md
    - `save_to_file(path)` - Save IDENTITY.md
    - `to_dict()` - Export to dict
    - `from_dict(data)` - Import from dict
    - `get_personality_description()` - Format for LLM context

- [ ] **2.3** Create template: `templates/IDENTITY_TEMPLATE.md`
  - Example IDENTITY.md for users
  - Sections: Personality, Goals, Constraints, Strengths, Weaknesses
  - Docstring explaining each field

- [ ] **2.4** Add type hints & docstrings
  - 100% type coverage
  - Comprehensive docstrings for all public methods

### Files Created
- `src/ghostclaw/core/agent-sdk/models.py`
- `src/ghostclaw/core/agent-sdk/agent_identity.py`
- `templates/IDENTITY_TEMPLATE.md`

### Tests Required
- [ ] Unit test: Load/save identity from file
- [ ] Unit test: Identity to/from dict conversion
- [ ] Unit test: Template validation

### Dependencies
- Pydantic for dataclasses
- Pathlib for file handling

---

## Task 3: Agent Memory System

**Status**: ⏳ Not Started | **Priority**: 🔴 Critical | **Est. Hours**: 5

### Description
Create `AgentMemory` class managing all 7 memory files (IDENTITY, HOOK, USER, AGENT, RULES, CONTEXT, LEARNINGS).

### Subtasks

- [ ] **3.1** Create `src/ghostclaw/core/agent-sdk/agent_memory.py`
  - `AgentMemory` class with:
    - `memory_dir: Path` - ~/.ghostclaw/agents/{agent-id}/memory/
    - `identity: AgentIdentity`
    - `hooks: Dict[str, Hook]`
    - `user: UserProfile`
    - `rules: AgentRules`
    - `context: SessionContext`
    - `learnings: Learnings`
    - `agent_notes: AgentNotes`

- [ ] **3.2** Implement memory file I/O
  - `load_memories()` - Load all 7 files from disk
  - `save_all()` - Write all 7 files to disk
  - `save_file(filename)` - Write single file
  - `load_file(filename)` - Load single file
  - Error handling for missing files (create defaults)

- [ ] **3.3** Implement dirty tracking
  - `mark_dirty(filename)` - Track changed files
  - `should_save_periodic()` - Determine if time to save
  - Triggers: every 10 messages, every 30 min, on suggestion applied

- [ ] **3.4** Create memory update methods
  - `update_context(project_path)` - Update CONTEXT.md
  - `log_decision(turn_result)` - Log to AGENT.md
  - `track_learning(outcome)` - Update LEARNINGS.md
  - `on_turn_complete(turn_result)` - Called after each chat turn

- [ ] **3.5** Create memory templates
  - `templates/HOOK_TEMPLATE.md`
  - `templates/USER_TEMPLATE.md`
  - `templates/AGENT_TEMPLATE.md`
  - `templates/RULES_TEMPLATE.md`
  - `templates/CONTEXT_TEMPLATE.md`
  - `templates/LEARNINGS_TEMPLATE.md`

- [ ] **3.6** Add type hints & docstrings
  - 100% type coverage
  - Comprehensive docstrings

### Files Created
- `src/ghostclaw/core/agent-sdk/agent_memory.py`
- `templates/HOOK_TEMPLATE.md`
- `templates/USER_TEMPLATE.md`
- `templates/AGENT_TEMPLATE.md`
- `templates/RULES_TEMPLATE.md`
- `templates/CONTEXT_TEMPLATE.md`
- `templates/LEARNINGS_TEMPLATE.md`

### Tests Required
- [ ] Unit test: Load memory files
- [ ] Unit test: Save memory files
- [ ] Unit test: Dirty file tracking
- [ ] Unit test: Missing file handling (defaults)
- [ ] Unit test: Memory update methods

### Dependencies
- YAML or JSON for structured memory files (or markdown with frontmatter)
- Pathlib for file I/O

---

## Task 4: Agent Workspace Isolation

**Status**: ⏳ Not Started | **Priority**: 🔴 Critical | **Est. Hours**: 4

### Description
Create `AgentWorkspace` class managing isolated git branches for agent edits.

### Subtasks

- [ ] **4.1** Create `src/ghostclaw/core/agent-sdk/agent_workspace.py`
  - `AgentWorkspace` class with:
    - `agent_id: UUID`
    - `project_path: str`
    - `workspace_branch: str` (agent/workspaces/{id})
    - `git: GitClient` (for operations)

- [ ] **4.2** Implement workspace operations
  - `create_workspace()` - Create isolated branch
  - `apply_suggestion(file_path, new_code)` - Apply code change
  - `commit(message, details)` - Create git commit
  - `run_tests()` - Execute test suite (optional)
  - `cleanup_workspace()` - Delete branch on exit

- [ ] **4.3** Implement GitHub integration
  - `detect_github_remote()` - Check if repo has GitHub
  - `create_pr_branch()` - Push to remote
  - `create_pull_request(title, body)` - Create PR on GitHub
  - `get_diff_url()` - Generate GitHub diff URL

- [ ] **4.4** Implement checkout context manager
  - `with self.checkout_branch():` - Temporarily switch branch
  - Auto-restore original branch on exit

- [ ] **4.5** Add type hints & docstrings
  - 100% type coverage
  - Comprehensive docstrings

### Files Created
- `src/ghostclaw/core/agent-sdk/agent_workspace.py`

### Tests Required
- [ ] Unit test: Create workspace branch
- [ ] Unit test: Apply suggestion to file
- [ ] Unit test: Commit with message
- [ ] Unit test: Checkout context manager
- [ ] Integration test: GitHub remote detection

### Dependencies
- GitPython for git operations
- PyGithub for GitHub API (optional, if GitHub integration enabled)

---

## Task 5: Agent Session Management

**Status**: ⏳ Not Started | **Priority**: 🟠 Important | **Est. Hours**: 3

### Description
Create `AgentSession` class managing session state, message history, and conversation context.

### Subtasks

- [ ] **5.1** Create `src/ghostclaw/core/agent-sdk/agent_session.py`
  - `AgentSession` class with:
    - `id: UUID` - Session ID
    - `agent_id: UUID` - Parent agent
    - `project_path: str`
    - `messages: List[AgentMessage]`
    - `suggestions: List[Suggestion]`
    - `created_at: datetime`
    - `workspace: AgentWorkspace`

- [ ] **5.2** Implement message management
  - `add_message(role, content)` - Add user/assistant message
  - `get_messages(last_n)` - Get recent messages
  - `save_to_db(db)` - Persist to database
  - `load_from_db(db, session_id)` - Load from database

- [ ] **5.3** Implement context building
  - `build_context()` - Create LLM context from scan + memory
  - `get_conversation_history()` - Format for LLM
  - `get_recent_decisions()` - Recent choices made

- [ ] **5.4** Implement suggestion tracking
  - `add_suggestion(suggestion)` - Add to session
  - `apply_suggestion(suggestion_id)` - Mark as applied
  - `get_pending_suggestions()` - Not yet applied

- [ ] **5.5** Add type hints & docstrings
  - 100% type coverage
  - Comprehensive docstrings

### Files Created
- `src/ghostclaw/core/agent-sdk/agent_session.py`

### Tests Required
- [ ] Unit test: Add/retrieve messages
- [ ] Unit test: Context building
- [ ] Unit test: Suggestion tracking
- [ ] Unit test: Save/load from DB

### Dependencies
- SQLAlchemy for database operations
- UUID for session IDs

---

## Task 6: GhostAgent Extension

**Status**: ⏳ Not Started | **Priority**: 🟠 Important | **Est. Hours**: 3

### Description
Extend existing `GhostAgent` class with `chat_turn()` method and memory integration.

### Subtasks

- [ ] **6.1** Review current `src/ghostclaw/core/agent.py`
  - Understand existing structure
  - Identify where to add `chat_turn()` method

- [ ] **6.2** Implement `chat_turn()` method
  - Signature: `async def chat_turn(query: str, session: AgentSession) -> str`
  - Load memory context (IDENTITY, RULES, LEARNINGS, USER)
  - Build LLM prompt from:
    - Agent identity
    - User preferences
    - Recent decisions
    - Session history
  - Call LLM (OpenRouter, Anthropic, etc.)
  - Return streamed response

- [ ] **6.3** Implement response parsing
  - Parse suggestions from response
  - Extract confidence scores if provided
  - Mark suggestions with type (bug, refactor, docs, etc)
  - Generate suggestion IDs

- [ ] **6.4** Hook memory updates
  - After chat turn complete, trigger memory save
  - Update CONTEXT.md
  - Log to AGENT.md

- [ ] **6.5** Add type hints & docstrings
  - 100% type coverage
  - Comprehensive docstrings

### Files Created
- Updated: `src/ghostclaw/core/agent.py`

### Tests Required
- [ ] Unit test: chat_turn basic flow
- [ ] Unit test: Response parsing
- [ ] Unit test: Memory update triggers
- [ ] Integration test: Full chat turn with LLM mock

### Dependencies
- Existing Ghostclaw core (agent, analyzer, llm_client)
- agent-sdk modules (identity, memory, session)

---

## Task 7: Local Storage & Database

**Status**: ⏳ Not Started | **Priority**: 🟠 Important | **Est. Hours**: 3

### Description
Create `LocalDB` class for SQLite persistence of projects, scans, sessions, and suggestions.

### Subtasks

- [ ] **7.1** Extend/refactor `src/ghostclaw/lib/local_storage.py`
  - Existing code may need updates for agent system
  - Or create new file if starting fresh

- [ ] **7.2** Implement database schema
  - Create SQLAlchemy models:
    - `Project` (path, name, created_at, last_analyzed)
    - `Scan` (project_id, report JSONB, metrics JSONB)
    - `AgentSession` (agent_id, project_id, scan_id, messages)
    - `Message` (session_id, role, content, created_at)
    - `Suggestion` (session_id, file_path, original, suggested, applied)
    - `Edit` (session_id, file_path, before, after, git_commit)
    - `AgentRegistry` (agent_id, name, type, status, hostname, project_path)

- [ ] **7.3** Implement LocalDB class
  - `create_tables()` - Initialize schema
  - `projects.create()`, `.get()`, `.list()`
  - `scans.create()`, `.get_latest()`
  - `sessions.create()`, `.get()`, `.list()`
  - `messages.create()`, `.list_by_session()`
  - `suggestions.create()`, `.get_pending()`

- [ ] **7.4** Add migration support
  - Alembic for schema migrations (optional for MVP)
  - Or simple version tracking

- [ ] **7.5** Add type hints & docstrings
  - 100% type coverage
  - Comprehensive docstrings

### Files Created
- Updated: `src/ghostclaw/lib/local_storage.py`
- Optional: `src/ghostclaw/lib/db/models.py` (if separate file)

### Tests Required
- [ ] Unit test: Table creation
- [ ] Unit test: CRUD operations for each model
- [ ] Integration test: Multi-table queries
- [ ] Integration test: Database migration

### Dependencies
- SQLAlchemy >=2.0
- SQLite (bundled)
- Alembic (optional)

---

## Task 8: CLI Interactive Command

**Status**: ⏳ Not Started | **Priority**: 🟠 Important | **Est. Hours**: 4

### Description
Create/update CLI command `ghostclaw agent spawn` for interactive agent sessions.

### Subtasks

- [ ] **8.1** Create `src/ghostclaw/cli/commands/agent.py`
  - Main command class: `AgentCommand`
  - Subcommands:
    - `spawn` - Start interactive session
    - `list` - List all agents
    - `resume` - Resume previous session
    - `remove` - Delete agent & memory

- [ ] **8.2** Implement `spawn` subcommand
  - Parse args: `ghostclaw agent spawn --name {name} /path/to/repo`
  - Load or create agent
  - Create workspace
  - Scan project
  - Enter interactive loop
  - Save on exit

- [ ] **8.3** Implement interactive loop
  - Display prompt: `[project-name] >_`
  - Read user input
  - Call `agent.chat_turn(query, session)`
  - Stream response
  - Handle special commands:
    - `.exit` or `.quit` - Exit session
    - `.accept {id}` - Accept suggestion
    - `.reject {id}` - Reject suggestion
    - `.list suggestions` - Show pending
    - `.git status` - Show git status
    - `.help` - Show help

- [ ] **8.4** Implement session persistence
  - Auto-save session on exit
  - Option to resume: `ghostclaw agent resume {session-id}`
  - Show full conversation history on resume

- [ ] **8.5** Add colorized output
  - User queries: default color
  - Agent responses: blue
  - Suggestions: green
  - Errors: red
  - Status: yellow

- [ ] **8.6** Add help text & documentation
  - Comprehensive help for all commands
  - Examples in --help output

- [ ] **8.7** Add type hints & docstrings
  - 100% type coverage
  - Comprehensive docstrings

### Files Created
- `src/ghostclaw/cli/commands/agent.py`

### Tests Required
- [ ] Unit test: Command parsing
- [ ] Unit test: Argument validation
- [ ] Integration test: Full spawn flow (with mocked LLM)
- [ ] Integration test: Special commands (accept, reject, etc)

### Dependencies
- Click (for CLI framework)
- Ghostclaw core & agent-sdk
- Rich (for colored output, optional)

---

## Task 9: Agent Registry & Global Index

**Status**: ⏳ Not Started | **Priority**: 🟡 Nice-to-Have | **Est. Hours**: 2

### Description
Create agent registry and global index for agent discovery.

### Subtasks

- [ ] **9.1** Create agent registry file structure
  - `~/.ghostclaw/agents/AGENTS_INDEX.json` - Global registry
  - `~/.ghostclaw/agents/{agent-id}/metadata.json` - Per-agent metadata

- [ ] **9.2** Implement `AgentRegistry` class
  - `register_agent(agent) -> UUID` - Create new agent entry
  - `list_agents() -> List[Agent]` - List all
  - `get_agent(agent_id) -> Agent` - Get by ID
  - `deregister_agent(agent_id)` - Remove agent
  - `update_status(agent_id, status)` - Update heartbeat/status

- [ ] **9.3** Implement agent discovery
  - Search by name
  - Search by project path
  - Filter by status (active, idle, offline)
  - Sort by last_active

- [ ] **9.4** Add periodic cleanup
  - Mark as offline if no heartbeat for 24h
  - Archive old sessions (optional)

### Files Created
- New class in agent-sdk
- JSON schema files (examples)

### Tests Required
- [ ] Unit test: Agent registration
- [ ] Unit test: Agent listing/search
- [ ] Unit test: Status updates

### Dependencies
- JSON file I/O
- Pathlib for file management

---

## Task 10: Integration & Documentation

**Status**: ⏳ Not Started | **Priority**: 🟠 Important | **Est. Hours**: 2

### Description
Integration tests and documentation for Phase 1.

### Subtasks

- [ ] **10.1** Create integration test file
  - `tests/integration/test_agent_flow.py`
  - Full flow: spawn → scan → chat → apply → save

- [ ] **10.2** Create docstrings guide
  - Example docstrings for agent-sdk modules
  - API reference format

- [ ] **10.3** Update main documentation
  - Add agent-sdk section to README
  - Show example: `ghostclaw agent spawn --name my-agent /path`

- [ ] **10.4** Update CONTRIBUTING.md
  - Agent-sdk coding standards
  - Type hinting requirements
  - Testing expectations

### Files Created
- `tests/integration/test_agent_flow.py`
- Updated: `docs/AGENT_SDK.md` (new)
- Updated: `README.md`
- Updated: `CONTRIBUTING.md`

### Tests Required
- [ ] Full end-to-end integration test
- [ ] All phase 1 unit tests passing
- [ ] Type checking passes (mypy)
- [ ] Linting passes (pylint/flake8)

---

## Summary by Timeline

### Week 1
- Task 1: Directory setup (1h) ✓
- Task 2: Agent identity (3h)
- Task 3: Agent memory (5h)
- Task 4: Agent workspace (4h)
- Total: 13 hours

### Week 2
- Task 5: Agent session (3h)
- Task 6: GhostAgent extension (3h)
- Task 7: Local storage & DB (3h)
- Task 8: CLI interactive command (4h)
- Task 9: Agent registry (2h)
- Task 10: Integration & docs (2h)
- Total: 17 hours

**Total Phase 1: ~30 hours (4 weeks at 8h/day)**

---

## Dependencies & Prerequisites

### Required Changes to Existing Code
- Extend `src/ghostclaw/core/agent.py` with `chat_turn()` method
- Update `src/ghostclaw/cli/__init__.py` to register `agent` command
- Possibly update `src/ghostclaw/lib/local_storage.py` for new DB schema

### New Dependencies (pip install)
- SQLAlchemy >=2.0.0 (if not already present)
- PyGithub >=1.58 (for GitHub API, optional)
- GitPython >=3.1.0 (if not already present)
- Click >=8.0 (for CLI, if not already present)
- Rich >=13.0 (for colored output, optional)

### Optional Enhancements
- Alembic for database migrations
- pytest-asyncio for async tests
- Pytest-mock for mocking

---

## Definition of Done (Phase 1)

✅ Code is written with full type hints and docstrings  
✅ All unit tests pass (>80% coverage for agent-sdk)  
✅ Integration test for full spawn → chat → apply flow passes  
✅ CLI `ghostclaw agent spawn` works end-to-end  
✅ Memory files created and persisted correctly  
✅ Git workspace isolation verified  
✅ Documentation updated  
✅ Code review ready for PR  

---

## Notes & Considerations

### Architecture Decisions
- Agent-sdk is organized submodule for scalability
- Memory files are local-only (not in repo) for privacy
- Session data goes to SQLite for offline capability
- Git isolation prevents accidental main repo changes

### Known Unknowns
- How to handle async/await in CLI (maybe use asyncio.run)
- LLM streaming best practices for CLI (line-by-line vs buffered)
- Database schema might need adjustments after MVP testing

### Risk Mitigation
- Start with simple implementations, refactor later
- Use mocks for GitHub API until integration ready
- Test database operations thoroughly (reset on test run)
- Version memory file formats (add VERSION field)

---

## Status & Progress

| Task | Status | Priority | Hours |
|------|--------|----------|-------|
| 1. Directory setup | ⏳ Ready | 🔴 | 1 |
| 2. Agent identity | ⏳ Ready | 🔴 | 3 |
| 3. Agent memory | ⏳ Ready | 🔴 | 5 |
| 4. Agent workspace | ⏳ Ready | 🔴 | 4 |
| 5. Agent session | ⏳ Ready | 🟠 | 3 |
| 6. GhostAgent ext | ⏳ Ready | 🟠 | 3 |
| 7. Local storage | ⏳ Ready | 🟠 | 3 |
| 8. CLI command | ⏳ Ready | 🟠 | 4 |
| 9. Agent registry | ⏳ Ready | 🟡 | 2 |
| 10. Integration | ⏳ Ready | 🟠 | 2 |

**Overall Status**: Ready to begin implementation 🚀
