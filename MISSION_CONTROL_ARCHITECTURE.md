# Mission Control Architecture

**Status**: Design Phase | **For**: Ghostclaw v1.0.0 Unified Multi-Agent System  
**Updated**: 2026-03-30

---

## Executive Summary

Ghostclaw evolves into a **multi-agent ecosystem** with two interfaces:

1. **CLI Interactive Agent** (primary, local) - `ghostclaw agent spawn /path`
2. **Mission Control** (frontend web app) - Central oversight + agent management

**Shared Knowledge Database** - Both CLI and web app access same data (SQLite local + PostgreSQL cloud).

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Ghostclaw v1.0.0 Ecosystem                  │
└─────────────────────────────────────────────────────────────────┘

┌────────────────────┐          ┌──────────────────────┐
│   CLI Agents       │          │  Mission Control     │
│ (Local Interactive)│◄────────►│   (Web Dashboard)    │
│                    │          │                      │
│ $ ghostclaw agent  │          │ [React/Next.js app]  │
│   spawn /path      │          │                      │
└────────────────────┘          └──────────────────────┘
         │                               │
         │                               │
         └──────────────┬────────────────┘
                        │
         ┌──────────────┴──────────────┐
         │                             │
    ┌────▼─────────┐         ┌────────▼─────┐
    │  Local DB    │         │  Cloud DB    │
    │  (SQLite)    │◄───────►│ (PostgreSQL) │
    │              │   Sync  │              │
    │ ~/.ghostclaw/│         │ Supabase     │
    └──────────────┘         └──────────────┘
         │
    ┌────▼──────────────────────────┐
    │   Shared Knowledge Database    │
    │                                │
    │ • Project Scans                │
    │ • Agent Sessions               │
    │ • Chat History                 │
    │ • Suggestions & Edits          │
    │ • Agent Registry               │
    └────────────────────────────────┘
```

---

## 2. Two Interface Pattern

### 2.1 CLI Interface (Interactive Agent)

```bash
$ ghostclaw agent spawn ~/projects/my-api

✓ Loaded project: my-api
✓ Scan completed (45 files, 12.5K LoC)
✓ Agent ready for chat

[my-api] >_ How can I reduce complexity in auth?

🤖 Agent Response:
  Found 3 high-complexity files...
  Suggestion-1: Extract OAuth handler
  ...

[my-api] >_ accept suggestion-1
✓ Applied to auth.py
```

**Characteristics**:
- Interactive terminal chat
- Full bidirectional context (scan results + chat history)
- Session persists to local DB
- Can sync to cloud later
- Single agent per terminal window

### 2.2 Mission Control Interface (Web Dashboard)

```
https://ghostclaw.app/dashboard

┌──────────────────────────────────────────┐
│ Mission Control - Agent Headquarters      │
├──────────────────────────────────────────┤
│                                          │
│  📊 Active Agents: 12                    │
│  📈 Total Sessions: 247                  │
│  🎯 Pending Reviews: 5                   │
│                                          │
├──────────────────────────────────────────┤
│                                          │
│ Agent Registry                           │
│ ┌────────────────────────────────────┐   │
│ │ agent-001  [my-api]      [Active]  │   │
│ │ agent-002  [web-client]  [Idle]    │   │
│ │ agent-003  [data-layer]  [Active]  │   │
│ │ ...                                │   │
│ └────────────────────────────────────┘   │
│                                          │
│ Recent Sessions                          │
│ ┌────────────────────────────────────┐   │
│ │ [my-api] session-abc123            │   │
│ │   3 suggestions applied            │   │
│ │   Edited: auth.py, oauth.py        │   │
│ │                                    │   │
│ │ [web-client] session-def456        │   │
│ │   5 messages in conversation       │   │
│ │                                    │   │
│ └────────────────────────────────────┘   │
│                                          │
│ Shared Sessions (Teams)                  │
│ ┌────────────────────────────────────┐   │
│ │ [platform-refactor] by @alice      │   │
│ │   Contributors: 3                  │   │
│ │   Active: Yes                      │   │
│ └────────────────────────────────────┘   │
│                                          │
└──────────────────────────────────────────┘
```

**Characteristics**:
- Central oversight of all agents
- Agent registry (status, last activity)
- View/manage multiple sessions
- Team collaboration & session sharing
- Historical analytics
- Real-time agent status (if service running)
- Agent coordination (pause, resume, cancel)

---

## 3. Agent Registry & Multi-Agent Coordination

### 3.1 Agent Identity & Registration

```python
class Agent:
    """
    Represents an agent instance (CLI or service-based)
    - Can be standalone (CLI) or registered in system
    - Has unique identity for tracking
    """
    id: UUID                     # Unique agent ID
    name: str                    # user-friendly name (auto or custom)
    type: str                    # 'cli' | 'service'
    status: str                  # 'active' | 'idle' | 'offline'
    
    # CLI-specific
    hostname: str                # machine where agent runs
    project_path: str            # GitHub/local path
    
    # Service-specific
    service_id: UUID             # which backend service instance
    
    # Lifecycle
    created_at: datetime
    last_heartbeat: datetime
    current_session_id: UUID
```

### 3.2 Agent Registry (Shared DB Table)

```sql
CREATE TABLE agent_registry (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,                   -- 'cli' | 'service'
    status TEXT DEFAULT 'idle',  -- 'active' | 'idle' | 'offline'
    hostname TEXT,               -- machine name
    project_path TEXT,           -- /path/to/repo
    user_id UUID,                -- who owns this agent
    team_id UUID,                -- which team can see it
    created_at TIMESTAMP,
    last_heartbeat TIMESTAMP,
    metadata JSONB,              -- agent config, version, etc
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(team_id) REFERENCES teams(id)
);

CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,      -- who is running this session
    project_id UUID NOT NULL,
    scan_id UUID NOT NULL,
    created_at TIMESTAMP,
    closed_at TIMESTAMP,
    FOREIGN KEY(agent_id) REFERENCES agent_registry(id),
    FOREIGN KEY(project_id) REFERENCES projects(id),
    FOREIGN KEY(scan_id) REFERENCES scans(id)
);

-- Track all messages from all agents
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    agent_id UUID NOT NULL,      -- which agent produced this
    role TEXT,                   -- 'user' | 'assistant' | 'system'
    content TEXT NOT NULL,
    created_at TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES agent_sessions(id),
    FOREIGN KEY(agent_id) REFERENCES agent_registry(id)
);
```

### 3.3 Agent Lifecycle

```
┌─────────────────────────────────────────┐
│  Agent Phases                           │
└─────────────────────────────────────────┘

1. REGISTRATION (on startup)
   ├─→ CLI: Auto-register on `ghostclaw agent spawn`
   │  └─→ Get UUID, register to local DB
   │
   └─→ Service: Registered via API on deployment
      └─→ API assigns UUID

2. ACTIVE (during session)
   ├─→ Heartbeat sent every 30s
   ├─→ Session status tracked (messages, suggestions)
   └─→ Can be monitored via Mission Control

3. IDLE (between sessions)
   ├─→ Session closed, session_data saved
   ├─→ Agent marked 'idle' in registry
   └─→ Can be resumed

4. SYNC (periodic)
   ├─→ CLI: Manual or periodic sync to cloud
   ├─→ Push: local sessions → PostgreSQL
   └─→ Bidirectional for team sharing

5. OFFLINE / DEREGISTERED
   ├─→ No heartbeat for 24 hours
   ├─→ Marked 'offline', can be reactivated
   └─→ Or explicitly deregistered
```

---

## 4. Shared Knowledge Database

### 4.1 Data Models Shared Between CLI & Mission Control

```
Local CLI (SQLite)          ←────────────────→  Cloud Service (PostgreSQL)
~/.ghostclaw/ghostclaw.db   ←─ Bi-directional ─→  Supabase / PostgreSQL

┌─────────────────┐                             ┌──────────────────────┐
│ projects        │                             │ users                │
│ scans           │                             │ teams                │
│ agent_sessions  │◄───────────────────────────►│ projects             │
│ messages        │       (Sync Engine)         │ scans                │
│ suggestions     │                             │ agent_registry       │
│ edits           │                             │ agent_sessions       │
│ agent_registry  │                             │ messages             │
└─────────────────┘                             │ suggestions          │
                                                │ edits                │
                                                │ audit_logs           │
                                                └──────────────────────┘

Schema Parity:
✓ Same column names
✓ Same data types
✓ Same relationships
✓ Cloud has additional: users, teams, permissions
```

### 4.2 Sync Engine

```python
class SyncEngine:
    """
    Bidirectional sync: Local SQLite ↔ Cloud PostgreSQL
    """
    
    async def push_session(
        self, 
        session_id: UUID,
        local_db: LocalDB,
        cloud_db: CloudDB
    ):
        """
        CLI → Cloud: Push local session data
        1. Get session from local_db
        2. Resolve conflicts (timestamp-based merge)
        3. Insert/update in cloud_db
        4. Mark as synced
        """
        pass
    
    async def pull_session(
        self,
        session_id: UUID,
        cloud_db: CloudDB,
        local_db: LocalDB
    ):
        """
        Cloud → CLI: Pull shared session (from teammate)
        1. Fetch from cloud
        2. Check conflicts
        3. Save to local_db
        4. Notify user
        """
        pass
    
    async def sync_agent_registry(self):
        """
        Keep agent_registry in sync across all agents
        Ensures all agents know who else is online
        """
        pass
```

---

## 5. Frontend Architecture: Mission Control

### 5.1 Stack & Structure

```
mission-control/
├── public/
│   └── favicon.ico
├── src/
│   ├── app/
│   │   ├── layout.tsx          # App shell
│   │   ├── dashboard/
│   │   │   ├── page.tsx        # Main dashboard
│   │   │   ├── agents/
│   │   │   │   ├── [id]/       # Agent detail view
│   │   │   │   └── registry/   # All agents
│   │   │   ├── sessions/
│   │   │   │   ├── page.tsx    # All sessions
│   │   │   │   └── [id]/       # Session detail + chat replay
│   │   │   └── teams/
│   │   │       └── [id]/       # Team sessions
│   │   └── api/
│   │       ├── agents/
│   │       ├── sessions/
│   │       └── sync/
│   ├── components/
│   │   ├── AgentCard.tsx
│   │   ├── AgentRegistry.tsx
│   │   ├── SessionViewer.tsx
│   │   ├── ChatReplay.tsx
│   │   └── TeamCollaboration.tsx
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   ├── realtime.ts         # WebSocket for live updates
│   │   └── sync.ts             # Sync logic
│   └── hooks/
│       ├── useAgents.ts
│       ├── useSessions.ts
│       └── useRealtime.ts
├── package.json
└── next.config.js

Tech Stack:
• Next.js 14+ (React, SSR)
• Tailwind CSS (UI)
• TanStack Query (data fetching)
• WebSocket (real-time updates)
• Recharts or similar (analytics)
```

### 5.2 Key Views & Features

#### Dashboard Overview
```
┌─ MISSION CONTROL ─────────────────────────────────┐
│                                                   │
│  📊 System Status                                 │
│  ├─ Active Agents: 12                             │
│  ├─ Total Sessions: 247                           │
│  ├─ Pending Reviews: 5                            │
│  └─ Last 24h Activity: ↑ 23%                      │
│                                                   │
│  🤖 Agent Registry (Real-time)                    │
│  ├─ agent-001 [my-api]       [🟢 ACTIVE]          │
│  │   Project: github.com/user/my-api              │
│  │   Session: 3 messages, 2 suggestions applied   │
│  │   Last active: 2 min ago                       │
│  │                                                │
│  ├─ agent-002 [web-client]   [🟡 IDLE]            │
│  │   Last session: 1 hour ago                     │
│  │   Suggestions pending review: 1                │
│  │                                                │
│  └─ agent-003 [data-layer]   [🟢 ACTIVE]          │
│      Chat with agent online ➜                     │
│                                                   │
│  📋 Recent Sessions                               │
│  ├─ [my-api] Reducing auth complexity             │
│  │   3 files modified, all tests pass             │
│  │   Ready to merge ✓                             │
│  │                                                │
│  └─ [web-client] Refactoring components           │
│                                                   │
│  👥 Team Collaboration                            │
│  ├─ @alice shared: platform-refactor session      │
│  │   Contributors: 3, Active: Yes                 │
│  │   View session ➜                               │
│  └─ @bob wants feedback on auth refactor          │
│      Request review ➜                             │
│                                                   │
└───────────────────────────────────────────────────┘
```

#### Agent Registry View
```
┌─ AGENT REGISTRY ──────────────────────────────┐
│                                               │
│ Filter: [All] [Active] [Idle] [Offline]       │
│ Sort: [Last Active] [Name] [Project]          │
│                                               │
│ ┌────────────────────────────────────────┐    │
│ │ Agent ID      │ Name      │ Project    │    │
│ ├────────────────────────────────────────┤    │
│ │ abc-001       │ my-api    │ github/... │ 🟢 │
│ │ def-002       │ web-uiGCP │ github/... │ 🟡 │
│ │ ghi-003       │ platform  │ gitlab/... │ 🟢 │
│ │ jkl-004       │ desktop   │ local/...  │ ⚫ │
│ │ ...           │ ...       │ ...        │    │
│ └────────────────────────────────────────┘    │
│                                               │
│ Selected: ghi-003 (platform)                   │
│ ┌────────────────────────────────────────┐    │
│ │ Details:                               │    │
│ │ • Type: cli                            │    │
│ │ • Status: active                       │    │
│ │ • Hostname: macbook-pro.local          │    │
│ │ • Project: /Users/alice/projects/...   │    │
│ │ • Created: 2 days ago                  │    │
│ │ • Current Session: session-xyz789      │    │
│ │   └─ 5 messages, 2 pending review      │    │
│ │                                        │    │
│ │ Actions:                               │    │
│ │ [View Session] [Join Chat] [Share]     │    │
│ └────────────────────────────────────────┘    │
│                                               │
└───────────────────────────────────────────────┘
```

#### Session Viewer & Chat Replay
```
┌─ SESSION: Fix Auth Complexity ────────────┐
│ Agent: my-api (alice@company.com)         │
│ Project: /Users/alice/my-api              │
│ Created: 2 hours ago | Closed: 1 hour ago │
├───────────────────────────────────────────┤
│                                           │
│ Chat Replay:                              │
│                                           │
│ [Alice] How can I reduce complexity?      │
│                                           │
│ [Agent] Found 3 high-complexity files:    │
│ • auth.py (CC=28)                         │
│ • validators.py (CC=24)                   │
│ • user.py (CC=18)                         │
│                                           │
│ Suggestions:                              │
│ ☑️ Suggestion-1: Extract OAuth handler   │
│    ✅ APPLIED (2 files changed)            │
│    [View Diff] [Revert]                   │
│                                           │
│ ☑️ Suggestion-2: Simplify validators      │
│    ❌ PENDING (auto-generated)             │
│    [View Code] [Accept] [Reject]          │
│                                           │
│ [Alice] Great! Let's refactor the models │
│                                           │
│ [Agent] Refactoring models...             │
│ ...                                       │
│                                           │
│ Summary:                                  │
│ • Files modified: 4                       │
│ • Tests passing: Yes                      │
│ • Ready to merge: Yes                     │
│ • Branch: ghostclaw/suggestions-xyz789    │
│                                           │
│ Collaboration:                            │
│ [Share with Team] [Export] [Resume in CLI]│
│                                           │
└───────────────────────────────────────────┘
```

---

## 6. CLI ↔ Mission Control Integration

### 6.1 Bi-directional Commands

**From CLI**:
```bash
# Publish session to cloud (share with team)
$ ghostclaw session share session-abc123 --team platform-team

# Resume colleague's shared session
$ ghostclaw session resume shared:platform-refactor

# Get dashboard URL for this agent
$ ghostclaw agent info
Agent ID: abc-123
Name: my-api
Mission Control: https://ghostclaw.app/agents/abc-123

# List all active agents in team (needs cloud sync)
$ ghostclaw agents list --team platform-team --status active
```

**From Mission Control**:
```html
<!-- Agent Detail Card -->
<AgentDetail agentId="abc-123">
  <AgentInfo />
  <CurrentSession />
  
  <!-- If agent CLI is online, show option to join chat -->
  <button onClick={joinLiveChat}>
    💬 Chat with Agent (Live)
  </button>
  
  <!-- Resume session in CLI -->
  <button onClick={resumeInCLI}>
    🖥️ Open in CLI
  </button>
</AgentDetail>
```

### 6.2 Live Chat Bridge (Optional Enhancement)

If agent is online, Mission Control can open WebSocket to join the CLI session:

```
User at Mission Control                User at CLI Terminal
         │                                    │
         │────────── WebSocket ──────────────│
         │     (join live session)           │
         │                                    │
         └──► Live Chat ◄───────────────────┘
         │    (both see same messages)       │
         │    (can type together)            │
         └──────────────────────────────────┘
```

---

## 7. Backend Service API (Supports Both Interfaces)

### 7.1 Core Endpoints

```
POST   /api/v1/agents/register
       Register new agent (CLI or service-based)

GET    /api/v1/agents
       List all agents (with filters)

GET    /api/v1/agents/{id}
       Get agent details + current session

POST   /api/v1/agents/{id}/heartbeat
       Keep-alive signal (every 30s from CLI)

---

POST   /api/v1/sessions
       Create new session

GET    /api/v1/sessions/{id}
       Get session details + full chat history

POST   /api/v1/sessions/{id}/messages
       Add message (user or assistant)

POST   /api/v1/sessions/{id}/suggestions
       Save suggestion

POST   /api/v1/sessions/{id}/apply
       Apply suggestion to codebase

---

POST   /api/v1/sync
       Sync local CLI data to cloud

GET    /api/v1/sync/status
       Check last sync time + conflicts

POST   /api/v1/sessions/{id}/share
       Share session with team

WS     /api/v1/ws/sessions/{id}
       WebSocket for real-time chat
```

### 7.2 CLI → Backend Sync Flow

```python
class CLISyncManager:
    """
    Handles bidirectional sync between local DB and cloud
    """
    
    async def push_to_cloud(self, session_id: UUID):
        """
        When user types: ghostclaw session share session-123
        
        1. Collect all data from local DB
           - Session metadata
           - All messages
           - All suggestions + edits
        2. POST /api/v1/sync with full payload
        3. Cloud stores and makes available to team
        """
        session = local_db.get_session(session_id)
        messages = local_db.get_messages(session_id)
        suggestions = local_db.get_suggestions(session_id)
        
        await api_client.post("/api/v1/sync", {
            "session": session,
            "messages": messages,
            "suggestions": suggestions
        })
        
        print("✓ Session shared to cloud")
    
    async def pull_from_cloud(self, shared_session_id: str):
        """
        When user types: ghostclaw session resume shared:name
        
        1. Query cloud for shared session
        2. Download full session data
        3. Merge into local DB
        4. Present to user as if local
        """
        response = await api_client.get(
            f"/api/v1/sessions/{shared_session_id}"
        )
        
        # Merge into local DB
        local_db.import_session(response)
        
        print("✓ Session loaded into local DB")
```

---

## 8. Multi-Agent Coordination

### 8.1 Preventing Conflicts

**Scenario**: Two teammates modify same file in their separate agent sessions.

**How to handle**:

```
Agent-1 (alice): Modifying auth.py
Agent-2 (bob): Also modifying auth.py (same file!)

When Bob tries to apply suggestion:
├─→ Check git: Is auth.py already modified?
├─→ If yes: Show conflict warning
│   └─→ "Alice modified auth.py 10 minutes ago"
│   └─→ "Merge strategy: [Auto] [Manual] [Abort]"
└─→ Auto-merge if possible, else request manual

When syncing to cloud:
├─→ Compare timestamps
├─→ If both changed same file:
│   └─→ Create conflict marker
│   └─→ Both agents notified
│   └─→ Require manual resolution
```

### 8.2 Session Sharing & Collaboration

```
┌─────────────────────────────────────────────┐
│ Shared Session: platform-refactor           │
│                                             │
│ Contributors: alice, bob, charlie           │
│ Status: Active (3 agents editing)           │
│                                             │
│ Activity Timeline:                          │
│ ├─ alice: Create session, analyze project   │
│ ├─ bob: Join session, add comment           │
│ ├─ alice: Apply suggestion-1                │
│ ├─ charlie: Join session                    │
│ ├─ bob: Apply suggestion-2                  │
│ └─ alice: Ready to merge                    │
│                                             │
│ Files Modified:                             │
│ • auth.py: alice + bob (collaborative)      │
│ • models.py: charlie                        │
│ • services/: alice                          │
│                                             │
│ Merge Status: 3 files ready to merge        │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [x] Knowledge DB Architecture (done)
- [ ] Local Storage: `src/ghostclaw/lib/local_storage.py`
- [ ] Agent Registry: tables + models
- [ ] GhostAgent.chat_turn() method
- [ ] CLI command: `ghostclaw agent spawn`

### Phase 2: CLI Full Features (Weeks 3-4)
- [ ] Session persistence (save/resume)
- [ ] Apply suggestions to files
- [ ] Git integration (create branches)
- [ ] Manual sync: `ghostclaw session sync`
- [ ] CLI agent registration

### Phase 3: Mission Control Frontend (Weeks 5-6)
- [ ] Next.js app setup
- [ ] Dashboard + agent registry view
- [ ] Session viewer + chat replay
- [ ] Real-time WebSocket updates
- [ ] Team collaboration UI

### Phase 4: Backend Service API (Weeks 5-6, parallel)
- [ ] FastAPI setup
- [ ] Agent registry endpoints
- [ ] Session sync endpoints
- [ ] Cloud DB (PostgreSQL)
- [ ] Authentication (JWT + RBAC)

### Phase 5: Sync Engine (Weeks 7-8)
- [ ] Bidirectional sync logic
- [ ] Conflict resolution
- [ ] Shared session management
- [ ] Team permissions

### Phase 6: Live Collaboration (Weeks 7-8)
- [ ] WebSocket for live chat
- [ ] Multi-user session editing
- [ ] Real-time conflict detection
- [ ] Audit logging

---

## 10. Shared Database Schema Summary

Both CLI (SQLite) and Mission Control (PostgreSQL) use same table structure:

```sql
-- Core Knowledge
projects
scans (ArchitectureReport + metrics)
agent_sessions
messages
suggestions
edits (file changes)

-- Agent Management
agent_registry (all agents in ecosystem)
agent_heartbeat (keep-alive tracking)

-- Team Collaboration
users
teams
project_access
session_sharing

-- Audit & Analytics
audit_logs
activity_timeline
sync_log
```

**Key Principle**: Same schema, different backends
- CLI reads/writes SQLite (~/.ghostclaw/ghostclaw.db)
- Mission Control reads/writes PostgreSQL (cloud)
- Sync engine keeps them in sync

---

## 11. Quick Start Example

### For CLI User:
```bash
# 1. Spawn interactive agent
$ ghostclaw agent spawn ~/projects/my-api

# Agent auto-registers to local DB and cloud (if configured)
# Session starts with full scan context

# 2. Chat with agent
[my-api] >_ How to reduce complexity?
[Agent] Analyzing... Found 3 issues
         - Suggestion-1: Extract OAuth ...
         - Suggestion-2: Simplify validators ...

# 3. Apply suggestion
[my-api] >_ accept suggestion-1
[Agent] Applied to 2 files, tests passing

# 4. Share with team
[my-api] >_ share with @platform-team
[Agent] ✓ Shared to Mission Control
         Team members can view: https://ghostclaw.app/sessions/abc123
```

### For Mission Control User:
```
1. Open https://ghostclaw.app/dashboard
2. See agent-001 (my-api) is ACTIVE
3. Click "View Session" to see chat replay
4. Click "Share" to collaborate with team
5. See @alice made 3 edits, all tests pass
6. Click "Ready to Merge" button
```

---

## 12. Architecture Comparison

| Aspect | CLI | Mission Control | Shared |
|--------|-----|-----------------|--------|
| **Interface** | Terminal | Web Dashboard | - |
| **Use Case** | Interactive coding | Oversight & Management | - |
| **User** | Individual developer | Team/Manager | - |
| **Real-time** | Live agent | Live updates via WS | - |
| **Database** | SQLite (local) | PostgreSQL (cloud) | Same schema |
| **Sync** | Manual/periodic | Automatic | Bidirectional |
| **Permission** | Single user | RBAC + teams | - |

---

## 13. Next Steps

1. ✅ **Knowledge DB Architecture** (done)
2. ⏳ **Mission Control Design** (this document)
3. **Code Scaffolds Phase 1** (ready to start)
   - Local storage layer
   - Agent session management
   - CLI interactive command
   - Agent registry tables

4. **Frontend Scaffolds** (Phase 3)
   - Next.js app structure
   - Dashboard components
   - Agent registry view

5. **Backend API** (Phase 4)
   - FastAPI + PostgreSQL setup
   - Sync engine

**Status**: Architecture COMPLETE, ready for Phase 1 implementation

---

This is the **Ghostclaw Ecosystem v1.0.0**: CLI as primary interface, Mission Control as central oversight, shared knowledge database enabling seamless collaboration between individual developers and teams.
