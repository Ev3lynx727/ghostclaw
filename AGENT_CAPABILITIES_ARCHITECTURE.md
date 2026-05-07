# Agent Capabilities & Memory System Architecture

**Status**: Design Phase | **For**: Ghostclaw v1.0.0 Agent Identity System  
**Updated**: 2026-03-30

---

## Executive Summary

Ghostclaw agents are **persistent entities with identity, memory, and learning**.

When a user runs `ghostclaw agent spawn /path/to/repo`:
1. ✅ Agent autolok-registers with unique ID (UUID)
2. ✅ Agent creates **isolated workspace** (local git branch, NO repo changes)
3. ✅ Agent maintains **persistent memory** (IDENTITY.md, HOOK.md, USER.md, etc.)
4. ✅ Agent learns over time (LEARNINGS.md, AGENT.md)
5. ✅ User can read & edit agent's memory (collaborative)
6. ✅ If repo has GitHub remote → create PR branches & propose commits

```
Agent Identity Lifecycle:

<should this path be cwd or absolute? Absolute is more flexible for multi-agent discovery>

┌─────────────────────────────────────────┐
│  $ ghostclaw agent spawn /path/repo     │ 
└──────────────────┬──────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
    Register Agent       Create Workspace
    UUID: abc-123        
    Status: active       ~/.ghostclaw/agents/
                         └── abc-123/ (Agent workspace namespace)
                             ├── memory/
                             │   ├── IDENTITY.md
                             │   ├── HOOK.md
                             │   ├── USER.md
                             │   ├── AGENT.md
                             │   ├── RULES.md
                             │   ├── CONTEXT.md
                             │   └── LEARNINGS.md
                             └── sessions/
                                 └── session-xyz/
```

---

## 1. Agent Architecture Overview

### 1.1 Agent as Persistent Entity

```python
class Agent:
    """
    Persistent agent with identity, memory, and learning capability
    """
    id: UUID                        # Unique agent ID
    name: str                       # User-friendly name (auto or custom)
    created_at: datetime
    
    # Current active session
    current_session_id: UUID        # None if idle
    current_project_path: str       # None if not spawned
    
    # Memory & Learning
    memory: AgentMemory             # Persistent memory system
    hooks: Dict[str, Hook]          # Behavioral rules
    identity: AgentIdentity         # Personality & goals
    rules: AgentRules               # Constraints & boundaries
    
    def spawn(self, project_path: str):
        """
        When user runs: ghostclaw agent spawn /path
        1. Load or create agent memory
        2. Create workspace (git branch)
        3. Start session
        """
        self.workspace = self.create_workspace(project_path)
        self.current_session = self.start_session()
        self.memory.update_context(project_path)
    
    async def chat_turn(self, user_query: str):
        """
        Process user message
        1. Read current context
        2. Consult memory & rules
        3. Generate response
        4. Update memory & CONTEXT.md
        """
        context = self.build_context()  # From memory + session
        response = await self.think(user_query, context)
        self.memory.update_after_turn(response)
        return response
    
    def save_memory(self):
        """
        Persist all memory files to disk
        Called on periodic trigger or session exit
        """
        self.memory.save_all()
```

---

## 2. Agent Workspace (Isolated Editing)

### 2.1 Workspace Structure

```
Original Repo: ~/projects/my-api/
├── src/
├── tests/
├── package.json
└── .git/

Agent isolates edits into local branch:
└─ agent/workspaces/abc-123/  (local only)
   ├── Edits to auth.py
   ├── Edits to models.py
   └── No changes to main repo!

All agent commits stay in branch until user approves.
```

### 2.2 Git Strategy

**For Local Repos (no GitHub)**:
```bash
# Agent creates local branch
git branch agent/workspaces/abc-123
git checkout agent/workspaces/abc-123

# Agent makes commits (only in this branch)
git add .
git commit -m "[Agent] Extract OAuth handler"

# User reviews via git status
git log --oneline  # see agent's commits
git diff main..agent/workspaces/abc-123  # view changes

# User integrates when ready
git checkout main
git merge agent/workspaces/abc-123
```

**For GitHub Repos (with remote)**:
```bash
# Agent creates local branch (same as above)
git branch agent/workspaces/abc-123

# Agent also creates remote PR branch
# Assuming origin = GitHub
git push origin agent/workspaces/abc-123 -u

# Auto-create PR on GitHub
POST /repos/{owner}/{repo}/pulls
  base: main
  head: agent/workspaces/abc-123
  title: "[Agent] Reduce auth complexity"
  body: "Automated refactoring suggestions..."

# User reviews PR on GitHub
# OR merges locally (git merge)
```

### 2.3 Workspace Isolation Details

```python
class AgentWorkspace:
    """
    Isolated editing environment for agent
    - No direct file modifications
    - All changes via git commits
    - Full audit trail
    """
    
    agent_id: UUID
    project_path: str
    workspace_branch: str           # agent/workspaces/{id}
    
    def apply_suggestion(self, file_path: str, new_code: str):
        """
        Apply code suggestion (NOT in-place edit)
        
        1. Checkout workspace branch
        2. Modify file
        3. Run tests
        4. Commit to git
        5. Mark suggestion as applied
        
        Main repo unchanged until merge
        """
        with self.checkout_branch():
            # Make edits
            with open(file_path, 'w') as f:
                f.write(new_code)
            
            # Commit
            self.git.stage(file_path)
            self.git.commit(
                message=f"[Agent] {suggestion.title}",
                details=f"Suggestion ID: {suggestion.id}"
            )
            
            # Tests
            test_result = self.run_tests()
            
            return {
                "applied": True,
                "commit_hash": self.git.head,
                "tests_passing": test_result.passed,
                "diff_url": self.get_diff_url()
            }
    
    def create_pr_if_remote(self):
        """
        If GitHub exists, create PR automatically
        """
        if self.has_github_remote():
            pr = self.github_api.create_pull_request(
                base="main",
                head=self.workspace_branch,
                title=self.get_pr_title(),
                body=self.get_pr_description()
            )
            self.pr_url = pr.url
            return pr
        return None
```

---

## 3. Agent Memory System

### 3.1 Memory Location & Discovery

**Global Agent Registry** (for discovery):
```
~/.ghostclaw/
├── agents/
│   ├── abc-123/              (Agent workspace namespace)
│   │   ├── memory/           (ALL agent memory files)
│   │   │   ├── IDENTITY.md
│   │   │   ├── HOOK.md
│   │   │   ├── USER.md
│   │   │   ├── AGENT.md
│   │   │   ├── RULES.md
│   │   │   ├── CONTEXT.md
│   │   │   └── LEARNINGS.md
│   │   ├── sessions/         (Session history)
│   │   │   └── session-xyz/
│   │   └── metadata.json     (Agent registry entry)
│   │
│   ├── def-456/
│   │   ├── memory/
│   │   ├── sessions/
│   │   └── metadata.json
│   │
│   └── AGENTS_INDEX.json     (Global index for discovery)
│
├── ghostclaw.db              (Knowledge DB)
└── config.json
```

**AGENTS_INDEX.json** - for quick discovery:
```json
{
  "agents": [
    {
      "id": "abc-123",
      "name": "my-api-agent",
      "type": "cli",
      "status": "active",
      "last_active": "2026-03-30T15:23:45Z",
      "current_project": "/Users/alice/projects/my-api",
      "memory_path": "~/.ghostclaw/agents/abc-123/memory",
      "hooks_version": "1.0",
      "identity_version": "1.2"
    },
    ...
  ]
}
```

### 3.2 Memory Files (7 Core)

#### A. IDENTITY.md - Agent Personality & Goals

```markdown
# Agent Identity

## Personality
- Name: api-refactor-agent
- Style: Direct, technical, action-oriented
- Communication: Clear explanations, code-first
- Decision-making: Analyze metrics, suggest bold changes

## Goals
- Reduce code complexity (target: CC < 10 per function)
- Improve testability
- Enforce consistent patterns
- Learn from codebase styles

## Constraints
- Never delete production code without tests
- Always preserve backward compatibility
- Preserve original intent/logic
- Respect existing architecture decisions

## Strengths
- Complexity analysis (trained on 500+ codebases)
- OAuth/auth patterns (specialized knowledge)
- Python/TypeScript (primary languages)

## Weaknesses
- Limited knowledge of DevOps/infrastructure
- May miss business context in legacy code
```

#### B. HOOK.md - Behavioral Rules & Triggers

```markdown
# Agent Hooks & Behaviors

## Event Triggers

### On Session Start
- Load latest IDENTITY.md
- Load USER preferences
- Read CONTEXT.md from last session
- Initialize memory cache

### On Each Turn (User Query)
- Parse query for intent (ask, suggest, apply, learn)
- Check RULES.md for constraints
- Consult LEARNINGS.md for similar past cases
- Build LLM context from memory + session

### On Suggestion Generated
- Log to AGENT.md (reasoning)
- Estimate impact (files affected, tests needed)
- Check RULES.md for violations
- Add to suggestions table

### On Suggestion Applied
- Update CONTEXT.md (current state)
- Log outcome to LEARNINGS.md
- Update AGENT.md (what worked)

### On Periodic Trigger (every 10 messages / 30 min)
- Save all memory files
- Update CONTEXT.md
- Compress old session data
- Sync to cloud if configured

## Decision Rules

### When Suggesting Code Changes:
1. Check RULES.md for constraints
2. Consult LEARNINGS.md for similar patterns
3. Verify against USER preferences
4. Estimate testability impact
5. Add rationale to AGENT.md

### When User Disagrees:
1. Log disagreement to AGENT.md
2. Update RULES.md if new constraint
3. Note in LEARNINGS.md (what to avoid)
4. Adjust future suggestions
```

#### C. USER.md - User Preferences & History

```markdown
# User Profile & Preferences

## User Info
- Name: Alice
- Email: alice@company.com
- Timezone: UTC+8
- GitHub: @alice-dev
- Preferred Language: Python 3.10+

## Preferences
- Code Style: Google Python Style Guide
- Testing: pytest with > 80% coverage
- Git: Conventional commits (feat:, fix:, refactor:)
- Documentation: Docstring every public function
- Architecture: Domain-driven design

## Work Patterns
- Usually codes 14:00-18:00 UTC+8
- Prefers working with "auth" & "API" modules
- Dislikes: Magic numbers, complex nested logic
- Likes: Clear separation of concerns, type hints

## Past Projects
- my-api (Flask, 2K LoC)
- web-client (React, 5K LoC)  
- data-pipeline (Python, 8K LoC)

## Agent Notes (from collaboration history)
- Responsive to auto-suggest (high accept rate)
- Prefers conservative refactoring (small commits)
- Values test coverage highly
- Will manually edit files for custom logic
```

#### D. AGENT.md - Agent's Self-Analysis

```markdown
# Agent Self-Analysis & Learnings

## Current Session Analysis
**Project**: my-api (Flask)
**Scan Date**: 2026-03-30T10:00:00Z
**Complexity**: Avg CC 12.5 (high)

### Findings
1. auth.py: CC=28, 850 lines
   - Suggestion: Extract OAuth, token, permissions
   - Status: Generated, awaiting user feedback

2. validators.py: CC=24, 620 lines
   - Suggestion: Use guard clauses instead of nested ifs
   - Status: Generated

3. models.py: CC=18, 450 lines
   - Suggestion: Split entity + service layer
   - Status: Monitoring

### Decision Log
- [10:15] Generated suggestion-1 (OAuth extraction)
  - Reasoning: CC reduction 28 → 8
  - Confidence: 85%
  - User response: Pending
  
- [10:30] Generated suggestion-2 (validators refactor)
  - Reasoning: Common pattern simplification
  - Confidence: 75%
  - User response: Pending

## Pattern Recognition
- This codebase similar to web-client project
- Common pattern: Monolithic handlers (like API layer)
- Recommendation: Extract service layer (60% confidence)

## Performance Notes
- Scan time: 2.3s (normal)
- Suggestion generation: 1.8s (normal)
- Model used: claude-opus (better complex analysis)
```

#### E. RULES.md - Constraints & Guardrails

```markdown
# Agent Rules & Constraints

## Hard Rules (Never Violate)
- [ ] Never suggest breaking changes without NEW_FEATURE flag
- [ ] Never delete code without unit tests covering it
- [ ] Never modify production config files
- [ ] Never suggest changes affecting backward compatibility
- [ ] Preserve error messages and logging

## Soft Rules (Prefer, but can override)
- [ ] Suggest tests before suggesting code changes
- [ ] Keep functions under 50 lines
- [ ] Keep cyclomatic complexity under 10
- [ ] Use existing code patterns (consistency > novelty)
- [ ] Add docstrings to new/modified functions

## This Repository Rules
- Must use pytest for tests
- Must follow Google Python style guide
- Must maintain > 80% code coverage
- Type hints required for all functions
- Conventional commits required

## User-Specific Rules (from USER.md)
- Alice prefers small, incremental commits (not giant refactors)
- Alice wants conservative suggestions (higher confidence threshold)
- Alice manually reviews all file edits before applying

## LLM Constraints
- Max tokens: 2000 per suggestion
- Temperature: 0.3 (low randomness, more deterministic)
- Model: claude-opus (for complex analysis)
```

#### F. CONTEXT.md - Current Session Context

```markdown
# Current Session Context

## Session Info
- Session ID: session-abc123
- Started: 2026-03-30T15:00:00Z
- Duration: 23 minutes
- Messages: 5 user queries

## Current State
- Project: /Users/alice/projects/my-api
- Branch: agent/workspaces/abc-123
- Files analyzed: 45
- Suggestions generated: 2 (pending review)
- Suggestions applied: 0

## Recent Decisions
1. User asked: "How to reduce complexity in auth?"
   - Response: Generated 3 suggestions (OAuth, validators, models)
   
2. User asked: "Can you explain suggestion-1?"
   - Response: Detailed explanation + impact analysis
   
3. Pending: User review of suggestions

## LLM Context Window
```
Recent messages (for context when continuing):
User: How can I reduce complexity in auth.py?
Agent: Found 3 issues...
User: Explain suggestion-1
Agent: OAuth extraction would...
User: [waiting for feedback]
```

## Next Steps
- Wait for user feedback on suggestions
- If approved: Apply suggestion-1 to auth.py
- If rejected: Adjust approach based on feedback
```

#### G. LEARNINGS.md - Long-Term Patterns & Optimizations

```markdown
# Agent Learnings & Patterns

## Successful Patterns
- **OAuth extraction**: Used 3 times, 100% user satisfaction
  - Key: Clear interface + existing tests
  - Pattern: Extract handler → service layer → DI
  
- **Guard clause refactoring**: Used 2 times, 80% satisfaction
  - Key: Start with simple cases
  - Pitfall: Over-aggressive with nested structures
  
- **Type hints addition**: Used 5 times, 95% satisfaction
  - Key: Generate, don't require user to write
  - Pattern: Start with public APIs

## Unsuccessful Patterns
- **Aggressive multi-method extraction**: 1 attempt, rejected
  - Issue: Too many files changed at once
  - Learning: User prefers small, incremental commits
  
- **AI-suggested variable names**: 2 attempts, 60% satisfaction
  - Issue: Misses business context
  - Learning: Ask user for naming preferences

## User Collaboration Insights
- Alice responds well to **metric-driven suggestions**
- Alice prefers **historical context** (why this pattern exists)
- Alice values **confidence scores** (which suggestions are safe)
- Alice rejects suggestions that **change code intent** (even slightly)

## Code Pattern Library (from Alice's projects)
```
my-api patterns:
- Flask Blueprint per domain
- Service layer for complex logic
- Repository pattern for data access
- Middleware for cross-cutting concerns

Styles:
- Snake_case for variables
- PascalCase for classes
- UPPERCASE for constants
- Docstring format: Google style
```

## Optimization Notes
- When analyzing Flask projects: Load Flask patterns first (+30% efficiency)
- When working with Alice: Increase confidence threshold (she's thorough reviewer)
- OAuth/auth modules: Use specialized model (better results)
- When suggesting: Include git diff URL (increases acceptance rate)

## Areas to Improve
- [ ] Better understanding of business logic in legacy code
- [ ] More context about why certain code decisions were made
- [ ] Handling technical debt vs feature development trade-offs
```

### 3.3 Memory Update Lifecycle

```
Agent Session Flow with Memory Updates:

┌─────────────────────────────────┐
│ $ ghostclaw agent spawn /path   │
└────────────┬────────────────────┘
             │
             ▼
    ┌────────────────────┐
    │ Load Memories      │
    │ (IDENTITY, RULES,  │
    │  USER, LEARNINGS)  │
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────┐
    │ Start Session      │
    │ Init CONTEXT.md    │
    └────────┬───────────┘
             │
             ├─────────────────┐
             │                 │
             ▼                 ▼
    ┌──────────────┐   wait
    │ User Query   │
    └────┬─────────┘
         │
         ▼
    ┌─────────────────────────────┐
    │ Process Query               │
    │ 1. Read IDENTITY, RULES     │
    │ 2. Consult LEARNINGS        │
    │ 3. Build LLM context        │
    │ 4. Generate response        │
    └────┬────────────────────────┘
         │
         ▼
    ┌─────────────────────────────┐
    │ Update Memories (on trigger)│
    │ • AGENT.md: log decision    │
    │ • CONTEXT.md: current state │
    │ • Frequency: periodic/       │
    │   on-request (not real-time) │
    └────┬────────────────────────┘
         │
    ┌────▼──────────────────┐
    │ Applied suggestion?   │
    │ YES ──► Update        │
    │ NO  ──► Continue      │ LEARNINGS.md
    └────┬──────────────────┘ (track outcomes)
         │
         ├─────────────── is_running?
         │       YES ◄─────┘
         │
         └─── NO
              ▼
    ┌─────────────────────────────┐
    │ On Exit/Save                │
    │ 1. Update CONTEXT.md        │
    │ 2. Save all memories        │
    │ 3. Compress session data    │
    │ 4. Sync to cloud (if config)│
    │ 5. Update AGENTS_INDEX      │
    └─────────────────────────────┘
```

### 3.4 Memory File Update Strategy

```python
class AgentMemoryManager:
    """
    Manages all agent memory files with smart persistence
    """
    
    def __init__(self, agent_id: UUID):
        self.agent_id = agent_id
        self.memory_dir = Path(f"~/.ghostclaw/agents/{agent_id}/memory")
        self.dirty_files = set()  # Track changed files
        self.last_save = None
    
    def on_turn_complete(self, turn_result: TurnResult):
        """
        Called after each chat turn
        Updates relevant memory files (not all, only changed)
        """
        # Update CONTEXT.md (current state)
        self.update_context(turn_result)
        self.dirty_files.add("CONTEXT.md")
        
        # Update AGENT.md (decision log)
        self.log_decision(turn_result)
        self.dirty_files.add("AGENT.md")
        
        # Check if periodic save needed
        if self.should_save_periodic():
            self.save_all()
    
    def should_save_periodic(self) -> bool:
        """
        Determine if it's time to save memory to disk
        Strategy: Update immediately on important changes,
        batch save on periodic triggers
        """
        # Trigger 1: Every 10 messages
        if len(self.dirty_files) >= 10:
            return True
        
        # Trigger 2: Every 30 minutes
        if (datetime.now() - self.last_save).seconds > 1800:
            return True
        
        # Trigger 3: Suggestion applied (important change)
        if "suggestion_applied" in self.dirty_files:
            return True
        
        return False
    
    def save_all(self):
        """
        Persist all dirty memory files to disk
        """
        for filename in self.dirty_files:
            self.save_file(filename)
        
        self.dirty_files.clear()
        self.last_save = datetime.now()
        
        # Update global AGENTS_INDEX
        self.update_agents_index()
    
    def load_memories(self) -> AgentMemories:
        """
        Load all memory files from disk
        Called on agent spawn
        """
        return AgentMemories(
            identity=self.load_file("IDENTITY.md"),
            hooks=self.load_file("HOOK.md"),
            user=self.load_file("USER.md"),
            agent=self.load_file("AGENT.md"),
            rules=self.load_file("RULES.md"),
            context=self.load_file("CONTEXT.md"),
            learnings=self.load_file("LEARNINGS.md"),
        )
```

---

## 4. User-Agent Memory Collaboration

### 4.1 User Edits Memory Files

```
User workflow:
1. Open agent memory files in editor
2. Edit RULES.md to add new constraints
3. Edit USER.md to update preferences
4. Edit LEARNINGS.md to correct pattern
5. Agent picks up changes on next turn
6. Agent integrates feedback

Example: User adds rule
File: ~/.ghostclaw/agents/abc-123/memory/RULES.md

Add:
"""
## New Rule (2026-03-30)
- Never suggest changes to database migrations
  (Reason: Too risky in production)
"""

Agent behavior:
- On next turn, agent reads updated RULES.md
- Checks: "DB migrations?" → NO (new rule)
- Skips suggesting migration changes
- Logs: "Respected user rule: no DB migration changes"
```

### 4.2 Agent Learns from User Feedback

```
Session flow:

Agent: "I suggest extracting OAuth handler"
User: "No, we have plans to refactor OAuth next sprint"

Agent action:
1. Log to AGENT.md: "User rejected OAuth suggestion
   Reason: Planned refactor next sprint"
2. Update LEARNINGS.md: "Note: Check sprint plan before
   suggesting OAuth changes"
3. Ask: "Should I add this as a rule?"
   User: "Yes, add to RULES.md"
4. Update RULES.md automatically
```

---

## 5. Agent Capabilities (Complete List)

### 5.1 Interactive Chat
- ✅ Natural language queries
- ✅ Multi-turn conversation
- ✅ Context awareness (from scan + memory)
- ✅ Streaming responses

### 5.2 Code Analysis & Suggestions
- ✅ Identify high-complexity functions
- ✅ Suggest refactoring patterns
- ✅ Generate new code (tests, types, docs)
- ✅ Propose complete reformatting

### 5.3 Code Modification
- ✅ Apply suggestions to codebase
- ✅ Run tests to verify changes
- ✅ Create commits with proper messages
- ✅ Create PRs (if GitHub remote exists)

### 5.4 Learning & Memory
- ✅ Persist identity & personality
- ✅ Maintain conversation history
- ✅ Learn from user feedback
- ✅ Improve suggestions over time
- ✅ Respect user preferences & rules

### 5.5 Workspace Isolation
- ✅ Create isolated git branches (agent/workspaces/{id})
- ✅ No changes to main repo until approved
- ✅ Full git audit trail
- ✅ Easy rollback (just delete branch)

### 5.6 GitHub Integration (If Remote Exists)
- ✅ Auto-create remote PR branches
- ✅ Push commits to GitHub
- ✅ Create pull requests automatically
- ✅ Link suggestions to GitHub issues (optional)
- ✅ Track PR status in agent memory

### 5.7 Mission Control Integration
- ✅ Register with agent registry
- ✅ Appear in Mission Control dashboard
- ✅ Stream live updates during session
- ✅ Share sessions with teammates
- ✅ Sync to cloud database

---

## 6. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Local Storage: Agent workspace structure
- [ ] Memory System: IDENTITY.md, HOOK.md, USER.md templates
- [ ] Agent Spawn: Initialize agent with memory
- [ ] Chat Loop: Load memory, process turns

### Phase 2: Memory Integration (Weeks 3-4)
- [ ] Memory Update Logic: Periodic saves (not real-time)
- [ ] User Collaboration: Read/edit memory files
- [ ] Context Building: Leverage memory in chat
- [ ] Learning: Track outcomes in LEARNINGS.md

### Phase 3: Workspace & Git (Weeks 3-4)
- [ ] Create isolated workspace branches
- [ ] Apply suggestions to workspace
- [ ] Commit with proper messages
- [ ] Test integration

### Phase 4: GitHub Integration (Weeks 5-6)
- [ ] Detect GitHub remote
- [ ] Create PR branches
- [ ] Auto-create PRs
- [ ] Link suggestions to PRs

### Phase 5: Agent Registry & Sync (Weeks 5-6)
- [ ] Register agents globally
- [ ] AGENTS_INDEX.json management
- [ ] Cloud sync of agent metadata
- [ ] Multi-agent discovery

---

## 7. Example: Complete Agent Session with Memory

```bash
$ ghostclaw agent spawn ~/projects/my-api

✓ Agent ID: agent-alice-001 (remembered)
✓ Loading memory from ~/.ghostclaw/agents/agent-alice-001/memory/
  ├─ IDENTITY.md loaded (api-refactor specialized)
  ├─ USER.md loaded (Alice's preferences)
  ├─ RULES.md loaded (5 rules, including new "no DB migrations")
  ├─ LEARNINGS.md loaded (past patterns)
  └─ CONTEXT.md loaded (can resume from last session)

✓ Creating workspace branch: agent/workspaces/agent-alice-001
✓ Scanning project...

[my-api] >_ How to improve auth.py?

🤖 Agent response (consulting memory):
  • Checking IDENTITY.md: I specialize in auth patterns
  • Checking RULES.md: Hard rules apply here
  • Checking LEARNINGS.md: Similar project last month...
  
  Found:
  1. OAuth handler (250 lines, should extract)
     Status: In learnings, successful pattern
     Confidence: 95%
  
  2. Token validation (nested conditions)
     Status: Pattern used before
     Confidence: 85%
  
  3. Permission engine (complex ACL)
     Status: User said "no DB migrations" - this is related!
     Skipping this one (following new rule)

[my-api] >_ I like suggestion-1. Can you implement it?

✓ Agent applies suggestion to workspace branch
✓ Runs tests: all passing
✓ Commits to agent/workspaces/agent-alice-001
  Message: "[Agent] Refactor: Extract OAuth handler from auth.py"
  
✓ Creates PR on GitHub:
  Title: "[Agent] Refactor: Extract OAuth handler"
  Body: "Extracted by Ghostclaw agent...
         Suggestion ID: sugg-001
         Tests: ✓ All passing
         Review in Mission Control: ..."
  PR URL: https://github.com/alice/my-api/pull/147

✓ Updates memory:
  • CONTEXT.md: suggestion-1 was applied
  • AGENT.md: logged decision + commitment
  • LEARNINGS.md: note success (OAuth extraction)
  • Saves all memory files to disk

[my-api] >_ Looks great! Let's merge it

✓ Agent suggests:
  "You can merge via GitHub PR or locally:
   git checkout main
   git merge agent/workspaces/agent-alice-001"

[my-api] >_ exit

✓ Session saved
✓ All memory files updated and synced
✓ Next time you spawn: agent remembers this session
```

---

## 8. Agent Diversity

Because agents persist with unique memories, each agent develops unique characteristics:

```
Agent A (alice-001):
- Specializes in Flask auth
- Conservative (high confidence threshold)
- Prefers small commits
- 85% suggestion acceptance rate

vs

Agent B (bob-002):
- Specializes in React components
- Bold (lower confidence threshold)
- Prefers large refactors
- 60% suggestion acceptance rate

Mission Control shows:
"Agent A: Best for auth work"
"Agent B: Best for UI refactoring"

Users can choose which agent to spawn based on:
- Project type
- Agent specialization
- User style preferences
- Past success rates
```

---

## 9. Architecture Summary

```
Agent = Persistent Entity with:
├─ Identity (IDENTITY.md)
├─ Personality (HOOK.md)
├─ Knowledge (LEARNINGS.md)
├─ Constraints (RULES.md)
├─ Context (CONTEXT.md)
├─ User Profile (USER.md)
└─ Analysis Notes (AGENT.md)

When spawned:
├─ Create isolated workspace (local git branch)
├─ Load all memories from ~/.ghostclaw/agents/{id}/
├─ Respect user preferences + rules
├─ Run analysis in context-aware manner
├─ Make suggestions based on capabilities + learnings
├─ Apply edits in isolation (no main repo changes)
└─ Update memory files (periodic, not real-time)

Connection to Mission Control:
├─ Register in global AGENTS_INDEX
├─ Sync memory metadata to cloud
├─ Share sessions across team
└─ Multi-agent oversight & coordination
```

---

## 10. Next Steps

1. ✅ Review this agent capabilities design
2. ⏳ Clarify: Should agent memory be Git-tracked in the repo itself? Or only local?
3. ⏳ Design: How agents discover & learn from each other?
4. ⏳ Start Phase 1 code scaffolds:
   - `src/ghostclaw/core/agent_identity.py` - Agent personality/identity
   - `src/ghostclaw/lib/agent_memory.py` - Memory file management
   - `src/ghostclaw/core/agent_workspace.py` - Workspace isolation
   - Update `src/ghostclaw/cli/commands/agent.py` with memory integration

---

**Status**: Architecture COMPLETE, ready for Phase 1 implementation 🚀
