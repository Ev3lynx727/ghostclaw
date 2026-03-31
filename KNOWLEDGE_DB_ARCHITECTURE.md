# Knowledge Database Architecture

**Status**: Design Phase | **For**: Ghostclaw v1.0.0 Unified Interactive System  
**Updated**: 2026-03-30

---

## Executive Summary

Ghostclaw v1.0.0 memerlukan **Knowledge Database** untuk menyimpan hasil scan/analyze, sehingga interactive CLI chat bisa:
1. Reference historical analyses
2. Generate targeted architecture plans  
3. Suggest code fixes dengan konteks yang akurat
4. Track conversation history per project

**Strategi**: Local-first (SQLite) + Cloud-ready (Supabase/PostgreSQL)

---

## 1. Knowledge Database Purpose & Scope

### What It Stores
```
├─ Scan Results (ArchitectureReport + metrics)
├─ Chat Sessions (conversation history per project)
├─ User Preferences & Projects
├─ Code Suggestions / Plans (AI-generated)
└─ Applied Edits & Changes (audit trail)
```

### Scope per Mode

| Mode | Storage | Scope | Sync |
|------|---------|-------|------|
| **CLI Batch** (`ghostclaw /path`) | Transient (memory) | Single run | No |
| **CLI Interactive** (`ghostclaw agent spawn`) | Local SQLite | Single project session | Manual upload |
| **Backend Service** (`/api/v1/analyses`) | PostgreSQL | Multi-user, multi-project | Auto |

---

## 2. Data Model & Schema

### 2.1. SQLite Local Schema (CLI)

```sql
-- ~/.ghostclaw/ghostclaw.db (SQLite)

CREATE TABLE projects (
    id TEXT PRIMARY KEY,          -- hash of repo path
    path TEXT UNIQUE NOT NULL,    -- /absolute/path/to/repo
    name TEXT NOT NULL,
    created_at DATETIME,
    last_analyzed DATETIME,
    last_session DATETIME
);

CREATE TABLE scans (
    id TEXT PRIMARY KEY,          -- UUID
    project_id TEXT NOT NULL,
    report JSONB NOT NULL,        -- Full ArchitectureReport
    metrics JSONB NOT NULL,       -- Complexity, CC, LoC per file
    timestamp DATETIME,
    metadata JSONB,               -- AI model used, options, etc
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE TABLE agent_sessions (
    id TEXT PRIMARY KEY,          -- UUID
    project_id TEXT NOT NULL,
    scan_id TEXT NOT NULL,        -- most recent scan
    created_at DATETIME,
    updated_at DATETIME,
    conversation_json JSONB,      -- all messages (ephemeral)
    FOREIGN KEY(project_id) REFERENCES projects(id),
    FOREIGN KEY(scan_id) REFERENCES scans(id)
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,          -- UUID
    session_id TEXT NOT NULL,
    role TEXT,                    -- 'user' | 'assistant'
    content TEXT NOT NULL,
    message_type TEXT,            -- 'query' | 'plan' | 'suggestion' | 'status'
    metadata JSONB,               -- token count, model, latency
    created_at DATETIME,
    FOREIGN KEY(session_id) REFERENCES agent_sessions(id)
);

CREATE TABLE suggestions (
    id TEXT PRIMARY KEY,          -- UUID
    session_id TEXT NOT NULL,
    message_id TEXT,              -- reference to which assistant message
    type TEXT,                    -- 'architectural' | 'code_fix' | 'refactor' | 'plan'
    file_path TEXT,
    original_code TEXT,
    suggested_code TEXT,
    applied BOOLEAN DEFAULT FALSE,
    applied_at DATETIME,
    FOREIGN KEY(session_id) REFERENCES agent_sessions(id)
);

CREATE TABLE edits (
    id TEXT PRIMARY KEY,          -- UUID
    session_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    before JSONB,                 -- {checksum, size, lines}
    after JSONB,                  -- {checksum, size, lines}
    applied_at DATETIME,
    git_commit TEXT,              -- if git commit made
    FOREIGN KEY(session_id) REFERENCES agent_sessions(id)
);
```

### 2.2. PostgreSQL Schema (Backend Service)

```sql
-- Production PostgreSQL (Supabase compatible)

CREATE TABLE users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT,
    created_at TIMESTAMP
);

CREATE TABLE teams (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id UUID NOT NULL,
    created_at TIMESTAMP,
    FOREIGN KEY(owner_id) REFERENCES users(id)
);

CREATE TABLE projects (
    id UUID PRIMARY KEY,
    team_id UUID NOT NULL,
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    repo_url TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY(team_id) REFERENCES teams(id)
);

CREATE TABLE scans (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    report JSONB NOT NULL,
    metrics JSONB NOT NULL,
    created_at TIMESTAMP,
    created_by UUID NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id),
    FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    user_id UUID NOT NULL,
    scan_id UUID NOT NULL,
    title TEXT,
    status TEXT DEFAULT 'active',  -- 'active' | 'archived' | 'shared'
    created_at TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(scan_id) REFERENCES scans(id)
);

CREATE TABLE messages (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    role TEXT,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES agent_sessions(id)
);

-- Similar tables for suggestions, edits, audit logs...
```

---

## 3. Storage Layer Architecture

### 3.1. CLI Local Storage

```
~/.ghostclaw/
├── ghostclaw.db              # SQLite database
├── projects/
│   └── {project_id}/
│       ├── last_scan.json    # Cache of most recent scan
│       ├── sessions/         # Conversation history
│       │   └── {session_id}.json
│       └── suggestions/      # Applied & pending suggestions
│           └── {suggestion_id}.json
└── config.json               # User preferences, API keys
```

**Local Storage Responsibilities**:
- ✅ Single-file SQLite DB for structured data
- ✅ JSON cache for performance (avoid re-parsing)
- ✅ Session persistence (ephemeral during chat, saved on exit)
- ✅ Full conversation history (for offline review)

### 3.2. Backend Service Storage (PostgreSQL)

```
Supabase / PostgreSQL Cloud
├── All scans, sessions, messages (same schema as SQLite)
├── Additional: users, teams, permissions
├── Full audit trail (created_by, created_at)
└── Replication from CLI (manual / scheduled)
```

**Service Storage Responsibilities**:
- ✅ Multi-user projects
- ✅ Team collaboration
- ✅ Full audit trail
- ✅ Backup & disaster recovery
- ✅ Analytics & reporting

---

## 4. Data Flow & Sync Patterns

### 4.1. CLI Interactive Session Flow

```
┌─────────────────────────────────────────────────────┐
│  $ ghostclaw agent spawn /path/to/repo              │
└──────────────────────────────────────────────────────┘
         │
         ├─→ Load/Create project in ~.ghostclaw/ghostclaw.db
         └─→ Run fresh scan (GhostAgent.analyze())
                └─→ Save to scans table + JSON cache
         │
         ├─→ Create agent_session
         │   ├─→ Load last scan as context
         │   ├─→ Initialize chat session
         │   └─→ Save session_id
         │
         ├─→ Interactive Loop
         │   ├─→ User input
         │   ├─→ Save to messages table
         │   ├─→ GhostAgent.chat_turn(query, session_context)
         │   ├─→ Save assistant response
         │   ├─→ Parse suggestions (if any)
         │   └─→ Loop until exit
         │
         └─→ On Exit
             ├─→ Save full session to ~/ghostclaw/projects/{id}/sessions/
             ├─→ Option: Upload to service (ghostclaw sync)
             └─→ Close DB connection
```

### 4.2. Sync: Local → Cloud

```
╔════════════════════════╗
║ CLI Local Machine      ║
║ ~/.ghostclaw/          ║
║ (SQLite)               ║
╚═════════╦══════════════╝
          │
   (Manual or Scheduled)
   ├─→ ghostclaw sync --project-id={id}
   ├─→ Push scans, sessions, suggestions
   └─→ Merge with cloud, resolve conflicts
          │
          ▼
╔════════════════════════╗
║ Backend Service        ║
║ PostgreSQL (Supabase)  ║
║ Multi-user, Teams      ║
╚════════════════════════╝
```

**Sync Commands**:
```bash
# Manual upload specific project
ghostclaw sync --project my-api

# Scheduled sync (daemon mode, optional)
ghostclaw daemon --sync-interval 3600

# Pull latest scans into local DB
ghostclaw pull --project my-api

# Share session to team
ghostclaw share --session {session_id} --team {team_id}
```

---

## 5. Interactive Chat Capabilities (3-Tier)

### Tier 1: Suggest (Phase 1)
**Capability**: Analyze + suggest plans/edits in chat

```
User: > How can I reduce complexity in auth.py?

Agent: 
  📊 Analysis of auth.py:
  - Lines: 850
  - CC: 28 (🔴 HIGH)
  - Nesting: 6 (normal)
  
  🎯 Suggestions:
  1. Extract login_handler() → separate module
  2. Replace nested if-chains with guard clauses
  3. Extract token validation → service class
  
  💾 These are saved as suggestions (not applied yet).
     Use `accept suggestion-1` to apply.
```

**Store in DB**:
- suggestions table (type='architectural' | 'code_fix')
- Message references original analysis

### Tier 2: Apply (Phase 2)
**Capability**: Apply suggested edits to codebase

```
User: > accept suggestion-1

Agent:
  📝 Applying: Extract login_handler() to separate module
  
  Changes:
  ├── auth.py (850 lines → 650 lines)
  ├── auth_handlers.py (NEW, 200 lines)
  └── imports.py (updated)
  
  ✅ Applied 3 files. Review changes? (y)

User: y

Agent: 
  Diff preview shown...
  Apply to disk? (y)
```

**Store in DB**:
- edits table (file_path, before, after, applied_at)
- Direct filesystem modification
- Create git backup branch (`ghostclaw/suggestions-{session_id}`)

### Tier 3: Multi-File + Git Commit (Phase 2-3, Flexible)
**Capability**: Complex refactors, multiple files, git integration

```
User: > Can you refactor the entire auth layer?

Agent:
  🏗️ Multi-file refactor plan:
  - Extract interfaces from auth.py
  - Move email logic to email_service.py
  - Update imports in 12 files
  - Add unit tests
  
  Estimated impact: Current test suite may need > 10 changes
  
  Proceed? (y/n)

User: y

Agent:
  Applying changes to 14 files...
  Running tests...
  ✓ All tests pass
  
  Create commit? (y)
  
User: y

Agent: 
  ✓ Committed: "Refactor: Extract auth layer into services"
  ✓ Branch: origin/ghostclaw-suggestions-{session_id}
```

**Store in DB**:
- edits table (multiple files, one per row)
- git_commit field with commit hash
- Full audit trail of all changes

---

## 6. Session Persistence & Context

### 6.1. Session State in Chat

```python
class AgentSession:
    id: UUID                                # Session ID
    project_id: UUID                        # Which project
    scan_id: UUID                           # Reference scan
    messages: List[AgentMessage]            # Chat history
    suggestions: List[Suggestion]           # Pending/applied
    
    @property
    def context_window(self) -> str:
        """Build LLM context from scan + recent messages"""
        return f"""
        Project: {project.name}
        
        Recent Scan Results:
        {scan.report.summary()}
        
        Recent Edits Made:
        {self.recent_edits()}
        
        Conversation History (last 10 messages):
        {self.messages[-10:]}
        """
    
    def save_to_db(self):
        """Persist to SQLite or PostgreSQL"""
        pass
    
    def export_json(self) -> str:
        """Export session as JSON for sharing"""
        pass
```

### 6.2. Context Building for Chat Turn

```python
async def chat_turn(
    query: str, 
    session: AgentSession,
    use_web_search: bool = False
) -> str:
    """
    Given user query and session context, generate response
    """
    context = session.context_window
    
    # Build messages for LLM (includes scan + history)
    messages = [
        {"role": "system", "content": f"You are Ghostclaw Agent...", },
        {"role": "system", "content": context},
        *session.messages[-5:],  # Last 5 exchanges
        {"role": "user", "content": query}
    ]
    
    # Stream response (FastAPI streaming or CLI streaming)
    response = await llm_client.stream_response(messages)
    
    # Parse response for suggestions (regex/structured)
    suggestions = parse_suggestions(response)
    
    # Save everything
    session.messages.append({"role": "user", "content": query})
    session.messages.append({"role": "assistant", "content": response})
    session.suggestions.extend(suggestions)
    session.save_to_db()
    
    return response
```

---

## 7. Implementation Roadmap

### Phase 1: Local Knowledge DB (Weeks 1-2)
- [x] Define SQLite schema
- [ ] Implement `src/ghostclaw/lib/local_storage.py`
  - `LocalDB` class (SQLite operations)
  - Project management (create, load, list)
  - Scan storage (save ArchitectureReport)
- [ ] Extend `GhostAgent` with `.chat_turn()` method
- [ ] Create `AgentSession` class (session state management)
- [ ] CLI command: `ghostclaw agent spawn`
  - Initialize session
  - Interactive loop
  - Save on exit

### Phase 2: Apply Edits + Git Integration (Weeks 3-4)
- [ ] `Suggestion` model with code comparison
- [ ] `EditsManager` class (file operations, git)
- [ ] Chat commands: `accept suggestion-{id}`
- [ ] Diff preview before applying
- [ ] Git branch creation (`ghostclaw/suggestions-*`)

### Phase 3: Backend + Cloud Sync (Weeks 5-6)
- [ ] PostgreSQL schema definition
- [ ] Backend service endpoints
- [ ] Sync engine (local ↔ cloud)
- [ ] Team collaboration features
- [ ] WebSocket interactive agent

### Phase 4: Analytics & Observability (Weeks 7-8)
- [ ] Session analytics (tokens, queries, edits)
- [ ] Logfire integration
- [ ] Performance metrics
- [ ] Audit logging

---

## 8. Database Isolation & Security

### 8.1. CLI Local Database
- **Location**: `~/.ghostclaw/ghostclaw.db` (user home only)
- **Permissions**: `0600` (user read-write only)
- **Encryption**: Optional (SQLCipher for sensitive repos)
- **Backup**: Automatic to `~/.ghostclaw/backups/` (daily)

### 8.2. Backend Service Database
- **Authentication**: JWT tokens
- **Authorization**: RBAC (user, team, project)
- **Row-level Security**: Supabase RLS policies
- **Encryption**: TLS in transit, encryption at rest
- **Audit**: Full audit trail (user, timestamp, action)

---

## 9. Query Patterns & Performance

### Most Common Queries

```python
# Get most recent scan for project
db.scans.filter(project_id=id).order_by('-created_at').first()

# Load session with full conversation
db.sessions.get(id)
db.messages.filter(session_id=id).order_by('created_at')

# Get all suggestions in session
db.suggestions.filter(session_id=id)

# Compare before/after of edits
db.edits.filter(session_id=id).order_by('applied_at')
```

**Indexes to Create**:
```sql
CREATE INDEX idx_scans_project_id ON scans(project_id);
CREATE INDEX idx_sessions_project_id ON agent_sessions(project_id);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_suggestions_session_id ON suggestions(session_id);
CREATE INDEX idx_edits_session_id ON edits(session_id);
```

---

## 10. Example: Complete Session Flow

```bash
$ ghostclaw agent spawn ~/projects/my-api

✓ Scanning ~/projects/my-api...
  ├── 45 files scanned
  ├── Avg CC: 8.2
  ├── Max nesting: 7
  └── Total LoC: 12,450

✓ Session created: session-abc123
✓ Database ready: ~/.ghostclaw/ghostclaw.db
✓ Ready for chat!

[Session: my-api] >_ How can I reduce complexity?

🤔 Analyzing your project...

Top issues found:
1. api/auth.py (CC=28, Lines=850)
2. utils/validators.py (CC=24, Lines=620)
3. models/user.py (CC=18, Lines=450)

💡 Suggestion-1: Extract login handler from auth.py
💡 Suggestion-2: Simplify validator logic with guard clauses
💡 Suggestion-3: Split user model into entity + service

Would you like me to explain any of these in more detail?

[Session: my-api] >_ Yes, explain suggestion-1

🎯 Suggestion-1 Details:

Current state:
  auth.py has 850 lines with 28 CC
  - login_handler: 200 lines, handles OAuth + JWT + 2FA
  - validate_token: 150 lines, nested conditions
  - ensure_permission: 100 lines, complex ACL logic

Suggested refactor:
  ├── auth.py → 300 lines (core logic)
  ├── oauth_handler.py → 150 lines (OAuth delegation)
  ├── token_service.py → 150 lines (JWT handling)
  └── permission_engine.py → 250 lines (ACL logic)

Benefit:
  ✓ Reduce CC from 28 → 8 (per module)
  ✓ Improve testability
  ✓ Easier to maintain

Ready to apply? (y/accept/skip)

[Session: my-api] >_ accept

✓ Changes applied to 4 files
✓ Tests still passing
✓ Suggestion marked as applied

DB saved:
  - edits table: 4 records (one per file)
  - Session history: 5 messages + 1 accepted suggestion

[Session: my-api] >_ exit

✓ Session saved: ~/.ghostclaw/projects/my-api/sessions/abc123.json
✓ You can resume this session later with: ghostclaw agent resume abc123
```

---

## 11. API Reference For Developers

### LocalStorage API (CLI)

```python
from ghostclaw.lib.local_storage import LocalDB

db = LocalDB()

# Project management
project = db.projects.create(path="/path/to/repo", name="my-app")
project = db.projects.get_by_path("/path/to/repo")
projects = db.projects.list()

# Scans
scan = db.scans.create(
    project_id=project.id,
    report=architecture_report,
    metrics=metrics_dict
)
scan = db.scans.get_latest(project_id)

# Sessions
session = db.sessions.create(project_id=project.id, scan_id=scan.id)
session = db.sessions.get(session_id)

# Messages
db.messages.create(session_id=session.id, role="user", content="...")
messages = db.messages.list_by_session(session_id)

# Suggestions
db.suggestions.create(session_id=session.id, type="code_fix", ...)
```

### Backend API (Service)

```python
from ghostclaw_mcp.client import GhostclawClient

client = GhostclawClient(url="http://localhost:8000", token="...")

# Create analysis job
job_id = await client.analyze(repo_path="/path")
status = await client.get_job_status(job_id)
report = await client.get_report(job_id)

# Interactive agent
async with client.agent_session(project_id="...") as session:
    response = await session.chat("How to reduce complexity?")
    suggestions = await session.get_suggestions()
    await session.apply_suggestion(suggestion_id)
```

---

## 12. Next Steps

1. **Approval**: Confirm this Knowledge DB architecture aligns with vision
2. **Refinement**: Any adjustments to schema or capabilities?
3. **Phase 1 Code Scaffolds**: Ready to create:
   - `src/ghostclaw/lib/local_storage.py` (LocalDB + schema)
   - `src/ghostclaw/core/agent_session.py` (session management)
   - `src/ghostclaw/core/agent.py` extended with `.chat_turn()` 
   - `src/ghostclaw/cli/commands/agent.py` (interactive CLI)

4. **Testing Strategy**: Unit tests for storage, integration tests for chat flow

---

**Architecture Status**: ✅ Ready for Phase 1 Implementation
