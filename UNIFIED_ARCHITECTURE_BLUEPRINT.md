# GHOSTCLAW UNIFIED ARCHITECTURE & IMPLEMENTATION BLUEPRINT

**Status**: Complete Platform Design (CLI + Interactive Agent + Backend Service)  
**Date**: March 30, 2026  
**Version**: 1.0.0-unified  
**Integration**: REVIEW.md + BACKEND_ARCHITECTURE_BLUEPRINT.md + INTERACTIVE_AGENT_ARCHITECTURE.md

---

## EXECUTIVE OVERVIEW

Ghostclaw adalah **single platform** dengan **3 operating modes** yang berbagi **satu core logic**:

```
┌────────────────────────────────────────────────────────────────┐
│                    GHOSTCLAW UNIFIED PLATFORM                 │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  MODE 1: BATCH CLI         MODE 2: INTERACTIVE AGENT          │
│  (Synchronous)             (Multi-turn conversation)          │
│  $ ghostclaw /path         $ ghostclaw agent spawn /path      │
│  └─ One-pass analysis      └─ Interactive terminal chat       │
│  └─ File output            └─ Real-time refactoring          │
│  └─ Use: Scripting, CI/CD  └─ Use: Development, review       │
│                                                                │
│  MODE 3: BACKEND SERVICE                                      │
│  (Asynchronous, Multi-user)                                  │
│  docker-compose up                                            │
│  POST /api/v1/analyses (batch job queue)                     │
│  WebSocket /ws/agent (interactive streaming)                  │
│  └─ Scalable, team-ready                                     │
│  └─ Use: Production, collaboration                           │
│                                                                │
│  ═══════════════════════════════════════════════════════════ │
│  SHARED CORE (No duplication, single source of truth)        │
│  ═══════════════════════════════════════════════════════════ │
│                                                                │
│  src/ghostclaw/core/                                          │
│  ├─ agent.py          (GhostAgent: .analyze() + .chat_turn())│
│  ├─ analyzer.py       (CodebaseAnalyzer)                     │
│  ├─ llm_client.py     (LLM integration + streaming)          │
│  ├─ models.py         (ArchitectureReport, GhostIssue)       │
│  └─ ... (all analysis logic)                                 │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## PART 1: THREE-MODE ARCHITECTURE

### 1.1 Mode Comparison Matrix

| Aspect | Batch CLI | Interactive Agent | Backend Service |
|--------|-----------|-------------------|-----------------|
| **Invocation** | `ghostclaw /path --json` | `ghostclaw agent spawn /path` | `POST /api/v1/analyses` |
| **Execution** | Synchronous, blocking | Synchronous, interactive | Async, job queue |
| **Latency** | Immediate | Immediate | Deferred (+ polling) |
| **Output** | File/stdout | Terminal (streaming) | JSON + DB |
| **State** | None | Session file | PostgreSQL |
| **Auth** | None | None | JWT required |
| **Multi-user** | No | No | Yes |
| **Scaling** | Single machine | Single machine | Multi-worker |
| **Ideal Use** | Scripting, CI/CD | Dev & learning | Production |

### 1.2 Unified Core Logic Flow

```
┌──────────────────────────────────────────────────────────────┐
│ UNIVERSAL ANALYSIS PIPELINE (src/ghostclaw/core/)           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Input (repo_path, config)                                 │
│         ↓                                                   │
│  Stack Detection (Python, Node, Go, TypeScript, etc)      │
│         ↓                                                   │
│  File Discovery & Scanning                                │
│         ↓                                                   │
│  Base Metrics (LoC, nesting, CCN)                         │
│         ↓                                                   │
│  Plugin Adapters (Lizard, PySCN, AI-CodeIndex)           │
│         ↓                                                   │
│  Vibe Score Computation (0-100)                           │
│         ↓                                                   │
│  Coupling & Dependency Analysis                            │
│         ↓                                                   │
│  ArchitectureReport Generation                            │
│         ↓                                                   │
│  [Optional] LLM Synthesis (refactoring suggestions)       │
│         ↓                                                   │
│  Output → File/API/WebSocket                              │
│                                                              │
└──────────────────────────────────────────────────────────────┘

Used by:
├─ GhostAgent.analyze() (Batch mode)
├─ GhostAgent.chat_turn() (Interactive mode) 
└─ Celery task in service layer
```

---

## PART 2: ENTRY POINTS (Different Interfaces)

### 2.1 CLI Layer (src/ghostclaw/cli/)

```
┌─────────────────────────────────────────────────────────────┐
│ CLI ENTRY POINTS (Single pip package)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ pip install ghostclaw                                      │
│                                                             │
│ COMMAND 1: ghostclaw /path [OPTIONS]  [BATCH MODE]        │
│ ─────────────────────────────────────                     │
│ Usage:                                                     │
│   $ ghostclaw /path/to/repo                              │
│   $ ghostclaw /path/to/repo --use-ai --json              │
│   $ ghostclaw /path/to/repo --delta --base origin/main    │
│                                                             │
│ File: src/ghostclaw/cli/commands/analyze.py              │
│ Flow:                                                      │
│   1. Parse args (AnalyzeCommand)                         │
│   2. Load config (GhostclawConfig)                       │
│   3. Create GhostAgent                                    │
│   4. Call agent.analyze()  ← Core logic                 │
│   5. Format output (JSON, Markdown)                      │
│   6. Write to file or stdout                             │
│                                                             │
│                                                             │
│ COMMAND 2: ghostclaw agent spawn /path [OPTIONS]  [NEW] │
│ ──────────────────────────────────────────────────────   │
│ Usage:                                                     │
│   $ ghostclaw agent spawn /path/to/repo                  │
│   $ ghostclaw agent spawn /path/to/repo --use-ai        │
│   $ ghostclaw agent spawn /path/to/repo --save-session   │
│                                                             │
│ File: src/ghostclaw/cli/commands/agent.py               │
│ Flow:                                                      │
│   1. Parse args (AgentCommand)                           │
│   2. Run initial analysis (CodebaseAnalyzer)            │
│   3. Create AgentSession (state tracker)                 │
│   4. Create GhostAgent                                    │
│   5. Interactive loop:                                    │
│      - Read user input                                   │
│      - Call agent.chat_turn()  ← Core logic            │
│      - Stream response to terminal                       │
│      - Save to session                                   │
│   6. Save session file on exit                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Service Layer (app/ directory)

```
┌─────────────────────────────────────────────────────────────┐
│ BACKEND SERVICE (FastAPI + Celery)                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ docker-compose up                                          │
│                                                             │
│ ENDPOINT 1: POST /api/v1/analyses  [BATCH MODE]          │
│ ────────────────────────────────                         │
│ Request:                                                   │
│   {                                                       │
│     "repo_url": "https://github.com/user/repo",        │
│     "branch": "main",                                    │
│     "use_ai": true                                       │
│   }                                                       │
│                                                             │
│ File: app/api/v1/analyses.py                             │
│ Flow:                                                      │
│   1. Authenticate user (JWT)                             │
│   2. Check quota                                          │
│   3. Clone repository                                     │
│   4. Create Analysis record in DB                         │
│   5. Queue Celery task                                    │
│      └─ run_ghostclaw_analysis(repo_path)               │
│         └─ Create GhostAgent                             │
│         └─ Call agent.analyze()  ← Core logic           │
│         └─ Save report to DB                             │
│   6. Return 202 Accepted + job_id                        │
│                                                             │
│ GET /api/v1/analyses/{id}/status  [POLLING]             │
│ ────────────────────────────────                        │
│   Returns: {status, progress, eta}                        │
│                                                             │
│ GET /api/v1/analyses/{id}  [RESULT]                      │
│ ──────────────────────────────────                       │
│   Returns: Full ArchitectureReport + vibe_score          │
│                                                             │
│                                                             │
│ ENDPOINT 2: WebSocket /ws/agent/{session_id} [INTERACTIVE] │
│ ────────────────────────────────────────────────────────  │
│ Connection:                                                │
│   ws = new WebSocket('ws://localhost:8000/ws/agent/...')│
│                                                             │
│ Send:                                                      │
│   {                                                       │
│     "action": "chat",                                     │
│     "message": "What's the biggest issue?"              │
│   }                                                       │
│                                                             │
│ File: app/api/v1/agent.py                                │
│ Flow:                                                      │
│   1. Authenticate user (JWT from token)                   │
│   2. Load AgentSession from DB                            │
│   3. Create GhostAgent                                    │
│   4. For each message:                                    │
│      - Call agent.chat_turn(message, session)           │
│      - Stream response chunks over WebSocket             │
│      - Save updated session to DB                        │
│   5. Keep connection alive for multi-turn chat           │
│                                                             │
│ Receive (streaming):                                       │
│   {type: "stream", chunk: "Agent response..."}          │
│   {type: "complete", full_response: "..."}              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## PART 3: CORE AGENT (UNIFIED BUSINESS LOGIC)

### 3.1 GhostAgent Class Structure

```python
# src/ghostclaw/core/agent.py

class GhostAgent:
    """
    Single agent class supporting both batch and interactive modes.
    
    Attributes:
        repo_path: str
        use_ai: bool
        ai_provider: str (openrouter, openai, anthropic)
        ai_model: Optional[str]
    """
    
    async def analyze(
        self,
        use_cache: bool = True,
        benchmark: bool = False
    ) -> ArchitectureReport:
        """
        BATCH MODE: Single-pass full analysis.
        
        Returns ArchitectureReport with:
        - vibe_score (0-100)
        - issues, ghosts, red_flags
        - metrics, coupling analysis
        - [optional] ai_synthesis
        
        Used by:
        - CLI batch: ghostclaw /path
        - Service: Celery task
        """
        # Run analysis pipeline
        analyzer = CodebaseAnalyzer()
        report = await analyzer.analyze(self.repo_path)
        
        # [Optional] LLM synthesis
        if self.use_ai:
            report.ai_synthesis = await self._synthesize_report(report)
        
        return report
    
    async def chat_turn(
        self,
        user_query: str,
        session: 'AgentSession',
        stream: bool = True
    ) -> AsyncIterator[str]:
        """
        INTERACTIVE MODE: Single turn in conversation.
        
        Yields response chunks for streaming display.
        
        Flow:
        1. Build context from session.initial_report
        2. Format conversation history (last 5 turns)
        3. Create LLM prompt with query
        4. Stream response via LLMClient
        5. Save exchange to session
        
        Used by:
        - CLI interactive: ghostclaw agent spawn
        - Service: WebSocket /ws/agent
        """
        # Build rich context
        context = self._build_chat_context(session)
        
        prompt = f"""
        You are GhostClaw, architectural code review agent.
        
        Repository: {self.repo_path}
        Initial Analysis Report:
        {session.initial_report}
        
        Conversation History:
        {session.get_conversation_history(last_n=5)}
        
        User: {user_query}
        
        Provide actionable analysis...
        """
        
        # Stream response
        response = ""
        async for chunk in self.llm_client.stream_completion(prompt):
            response += chunk
            if stream:
                yield chunk
        
        # Save to session
        session.add_message("user", user_query)
        session.add_message("agent", response)
        
        return response
    
    async def suggest_refactoring(
        self,
        file_path: str,
        session: 'AgentSession'
    ) -> Dict[str, Any]:
        """Suggest concrete refactoring for file."""
        # ... implementation ...
        pass
    
    async def explain_pattern(
        self,
        pattern_name: str,
        session: 'AgentSession'
    ) -> str:
        """Explain architectural pattern in context of repo."""
        # ... implementation ...
        pass
```

### 3.2 AgentSession Class (NEW)

```python
# src/ghostclaw/core/agent_session.py

class AgentSession:
    """
    Manages interactive session state.
    
    Persists to:
    - File (.ghostclaw/sessions/{session_id}.json) for CLI
    - PostgreSQL for backend service
    """
    
    def __init__(
        self,
        repo_path: str,
        initial_report: Optional[ArchitectureReport] = None
    ):
        self.repo_path = repo_path
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.utcnow()
        self.messages: List[AgentMessage] = []
        self.initial_report = initial_report
    
    def add_message(
        self,
        role: str,  # "user" or "agent"
        content: str,
        context: Optional[Dict] = None
    ):
        """Track single conversation turn."""
        msg = AgentMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            analysis_context=context
        )
        self.messages.append(msg)
    
    def get_conversation_history(self, last_n: int = 10) -> str:
        """Format recent messages for LLM context."""
        recent = self.messages[-last_n:]
        return "\n".join([
            f"{msg.role.upper()}: {msg.content}"
            for msg in recent
        ])
    
    def save_to_file(self, file_path: str):
        """CLI: Persist session to file."""
        # ... implementation ...
        pass
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'AgentSession':
        """CLI: Resume previous session from file."""
        # ... implementation ...
        pass
    
    def to_dict(self) -> Dict:
        """Convert to dict for DB storage."""
        # ... implementation ...
        pass
```

---

## PART 4: SYSTEM ARCHITECTURE (5-TIER)

```
┌──────────────────────────────────────────────────────────┐
│ TIER 1: ENTRY POINTS (User interfaces)                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  CLI (pip install ghostclaw)                            │
│  ├── AnalyzeCommand (batch)                             │
│  └── AgentCommand (interactive)                         │
│                                                          │
│  FastAPI (docker-compose up)                            │
│  ├── /api/v1/analyses (batch endpoints)                │
│  └── /ws/agent (websocket for interactive)              │
│                                                          │
│  Web UI (Next.js frontend)                              │
│  ├── Batch analysis form                                │
│  └── Interactive agent chat panel                       │
│                                                          │
└──────────┬───────────────────────────────────────────────┘
           │
┌──────────┴───────────────────────────────────────────────┐
│ TIER 2: REQUEST HANDLERS (Business orchestration)       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  CLI Commands (src/ghostclaw/cli/commands/)             │
│  ├── analyze.py → GhostAgent.analyze()                 │
│  └── agent.py   → GhostAgent.chat_turn()               │
│                                                          │
│  Services (app/services/)                               │
│  ├── analysis_service.py  (schedule, poll)             │
│  ├── user_service.py      (auth, quotas)               │
│  └── repo_service.py      (clone, validate)            │
│                                                          │
│  Celery Tasks (app/tasks/)                              │
│  └── analyze_task.py → GhostAgent.analyze()            │
│                                                          │
└──────────┬───────────────────────────────────────────────┘
           │
┌──────────┴───────────────────────────────────────────────┐
│ TIER 3: CORE ANALYSIS (Reused, no duplication)         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  GhostAgent (src/ghostclaw/core/agent.py)              │
│  ├── .analyze() → ArchitectureReport                   │
│  ├── .chat_turn() → Stream response                    │
│  └── ... other methods                                 │
│                                                          │
│  CodebaseAnalyzer (src/ghostclaw/core/analyzer.py)     │
│  ├── Find files                                         │
│  ├── Compute metrics                                    │
│  ├── Run adapters                                       │
│  └── Aggregate results                                 │
│                                                          │
│  PluginRegistry (src/ghostclaw/core/adapters/)         │
│  ├── Discover plugins                                  │
│  ├── Validate versions                                 │
│  └── Run concurrently                                  │
│                                                          │
│  LLMClient (src/ghostclaw/core/llm_client.py)          │
│  ├── Stream responses                                  │
│  ├── Retry logic                                       │
│  └── Token budgets                                     │
│                                                          │
│  AgentSession (src/ghostclaw/core/agent_session.py)    │
│  ├── Track conversation                                │
│  ├── Persist state                                     │
│  └── Manage context                                    │
│                                                          │
│  Models & Validators (src/ghostclaw/core/models.py)    │
│  ├── ArchitectureReport                                │
│  ├── GhostIssue                                        │
│  └── ... other models                                  │
│                                                          │
└──────────┬───────────────────────────────────────────────┘
           │
┌──────────┴───────────────────────────────────────────────┐
│ TIER 4: DATA ACCESS (Persistence)                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Database (app/db/)                                     │
│  ├── SQLAlchemy models                                 │
│  ├── User, Team, Analysis, AuditLog                    │
│  └── Alembic migrations                                │
│                                                          │
│  Cache (app/cache/)                                     │
│  ├── Redis for sessions, job status                    │
│  └── Local file cache for CLI                          │
│                                                          │
│  File System                                            │
│  ├── Session files (.ghostclaw/sessions/)              │
│  └── Cloned repos (.ghostclaw/repos/)                  │
│                                                          │
└──────────┬───────────────────────────────────────────────┘
           │
┌──────────┴───────────────────────────────────────────────┐
│ TIER 5: INFRASTRUCTURE (Deployment & Config)           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Configuration (app/config/)                            │
│  ├── settings.py (Pydantic BaseSettings)               │
│  ├── database.py (SQLAlchemy setup)                    │
│  └── cache.py (Redis setup)                            │
│                                                          │
│  Docker & Orchestration                                │
│  ├── Dockerfile (API + workers)                        │
│  ├── docker-compose.yml (local dev)                    │
│  └── k8s/ (optional Kubernetes)                        │
│                                                          │
│  Environment                                            │
│  ├── .env.example                                      │
│  └── logging.yaml                                      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## PART 5: DIRECTORY STRUCTURE (COMPLETE)

```
ghostclaw/
│
├── src/ghostclaw/
│   ├── __init__.py
│   ├── version.py
│   │
│   ├── core/                          ← SHARED BY ALL 3 MODES
│   │   ├── __init__.py
│   │   ├── agent.py                   # GhostAgent (analyze + chat_turn)
│   │   ├── agent_session.py           # AgentSession (state management)
│   │   ├── analyzer.py                # CodebaseAnalyzer
│   │   ├── analyzer/                  # Sub-components
│   │   ├── llm_client.py              # LLM integration (streaming)
│   │   ├── llm_client/                # Provider implementations
│   │   ├── models.py                  # ArchitectureReport, GhostIssue
│   │   ├── adapters/                  # MetricAdapter, StorageAdapter
│   │   ├── cache.py                   # Disk + Redis caching
│   │   ├── config.py                  # Configuration
│   │   ├── coupling.py                # Dependency analysis
│   │   ├── detector.py                # File discovery
│   │   ├── git_utils.py               # Git operations
│   │   ├── metrics.py                 # Vibe score formulas
│   │   ├── migration.py               # Data migration
│   │   ├── memory.py                  # Report history
│   │   ├── qmd/                       # Vector DB backend
│   │   ├── search_cache.py            # Query caching
│   │   ├── vector_store/              # Vector search
│   │   └── __init__.py
│   │
│   ├── cli/                           ← CLI INTERFACE (MODE 1 & 2)
│   │   ├── __init__.py
│   │   ├── ghostclaw.py               # Entry point
│   │   ├── commander.py               # Command discovery
│   │   ├── commands/
│   │   │   ├── __init__.py
│   │   │   ├── analyze.py             # Batch mode
│   │   │   └── agent.py               # Interactive mode (NEW)
│   │   ├── formatters/
│   │   │   ├── json_formatter.py
│   │   │   ├── markdown_formatter.py
│   │   │   └── terminal_formatter.py  # Interactive UI
│   │   ├── services/
│   │   │   ├── analysis_cli_service.py
│   │   │   └── agent_cli_service.py   # Terminal UI helpers
│   │   └── __init__.py
│   │
│   ├── lib/
│   │   ├── cache.py
│   │   ├── github.py
│   │   ├── notify.py
│   │   ├── complexity.py
│   │   └── __init__.py
│   │
│   ├── stacks/
│   │   ├── base.py
│   │   ├── python.py
│   │   ├── node.py
│   │   ├── go.py
│   │   ├── typescript.py
│   │   ├── docker.py
│   │   ├── shell.py
│   │   └── __init__.py
│   │
│   └── references/
│
├── app/                               ← BACKEND SERVICE (MODE 3)
│   ├── __init__.py
│   ├── main.py                        # FastAPI app initialization
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── analyses.py            # POST /v1/analyses, GET /status
│   │   │   ├── auth.py                # Login, register, refresh
│   │   │   ├── reports.py             # List, get, export reports
│   │   │   ├── health.py              # Health check
│   │   │   ├── agent.py               # WebSocket /ws/agent (NEW)
│   │   │   ├── plugins.py             # Plugin management
│   │   │   ├── admin.py               # Admin endpoints
│   │   │   └── deps.py                # Dependencies (auth, DB)
│   │   └── middleware.py              # CORS, logging, etc
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt_handler.py             # Token generation/validation
│   │   ├── permissions.py             # RBAC enforcement
│   │   ├── models.py                  # User, Team, Role
│   │   └── security.py                # Password hashing
│   │
│   ├── services/                      # Business orchestration
│   │   ├── __init__.py
│   │   ├── analysis_service.py        # Schedule, poll, get results
│   │   ├── user_service.py            # User management
│   │   ├── repo_service.py            # Clone, validate repos
│   │   ├── quota_service.py           # Rate limiting
│   │   ├── storage_service.py         # Report persistence
│   │   └── agent_service.py           # Interactive agent (NEW)
│   │
│   ├── tasks/                         # Celery task definitions
│   │   ├── __init__.py
│   │   ├── analyze_task.py            # @task run_ghostclaw_analysis
│   │   ├── cleanup_task.py            # Scheduled cleanup
│   │   └── celery_app.py              # Celery config
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py                  # SQLAlchemy ORM
│   │   ├── schemas.py                 # Pydantic for API
│   │   ├── session.py                 # AsyncSession manager
│   │   └── migrations/                # Alembic migrations
│   │
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── redis_client.py            # Redis connection
│   │   ├── job_cache.py               # Job status cache
│   │   ├── session_cache.py           # Session cache
│   │   └── memory_cache.py            # In-memory cache
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py                # Pydantic BaseSettings
│   │   ├── database.py                # DB connection
│   │   └── logging.py                 # Logging setup
│   │
│   └── websocket/                     # WebSocket utilities (NEW)
│       ├── __init__.py
│       ├── manager.py                 # Connection management
│       └── handlers.py                # WebSocket message handlers
│
├── docker/
│   ├── Dockerfile                     # Multi-stage for API
│   ├── Dockerfile.worker              # Celery worker
│   ├── Dockerfile.beat                # Celery beat
│   └── entrypoint.sh
│
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   └── ingress.yaml
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures
│   │
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_agent.py              # GhostAgent tests
│   │   ├── test_agent_session.py      # Session tests (NEW)
│   │   ├── test_chat_turn.py          # Interactive tests (NEW)
│   │   ├── test_analyzer.py
│   │   ├── test_adapters.py
│   │   ├── test_llm_client.py
│   │   ├── test_auth.py
│   │   ├── test_api_endpoints.py
│   │   ├── test_services.py
│   │   └── ...
│   │
│   └── integration/
│       ├── __init__.py
│       ├── test_batch_cli_flow.py    # CLI batch e2e
│       ├── test_interactive_cli_flow.py # CLI interactive e2e (NEW)
│       ├── test_batch_api_flow.py    # API batch e2e
│       ├── test_interactive_api_flow.py # WebSocket e2e (NEW)
│       ├── test_full_workflow.py     # End-to-end
│       └── ...
│
├── migrations/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│
├── scripts/
│   ├── init_db.py
│   ├── seed_data.py
│   ├── health_check.sh
│   └── load_test.py                  # Locust load testing
│
├── config/
│   ├── .env.example
│   └── logging.yaml
│
├── docs/
│   ├── UNIFIED_ARCHITECTURE.md        # This file
│   ├── QUICKSTART.md                  # Get started guide
│   ├── CLI_GUIDE.md                   # CLI usage
│   ├── API_GUIDE.md                   # Service API docs
│   ├── AGENT_GUIDE.md                 # Interactive agent guide
│   ├── DEPLOYMENT.md                  # Deploy to production
│   └── TROUBLESHOOTING.md             # Common issues
│
├── pyproject.toml                     # Package config
├── requirements.txt
├── Dockerfile                         # For service
├── docker-compose.yml                 # Local dev
│
├── README.md                          # Main readme
├── UNIFIED_ARCHITECTURE.md            # This file
│
└── .github/
    └── workflows/
        ├── test.yml                   # Run tests
        ├── lint.yml                   # Lint & format
        └── release.yml                # Auto-release
```

---

## PART 6: IMPLEMENTATION PHASES

### Phase 1: Core Extensions (Week 1)
**Goal**: Enhance core with interactive capabilities

**Tasks**:
- [ ] Update `GhostAgent.chat_turn()` method (streaming)
- [ ] Create `AgentSession` class (state management)
- [ ] Enhance `LLMClient` for streaming & multi-turn
- [ ] Add terminal streaming to formatters
- [ ] Tests: `test_chat_turn.py`, `test_agent_session.py`

**Deliverables**:
- GhostAgent supports both `.analyze()` and `.chat_turn()`
- Session persistence (file + dict format)
- Streaming response support

### Phase 2: CLI Interactive Command (Week 1-2)
**Goal**: Add interactive agent mode to CLI

**Tasks**:
- [ ] Create `AgentCommand` in `cli/commands/agent.py`
- [ ] Terminal UI with streaming display
- [ ] Interactive loop (read input → chat_turn → display)
- [ ] Session save/load from file
- [ ] Helper functions (explain, refactor, compare)
- [ ] Tests: `test_interactive_cli_flow.py`

**Deliverables**:
```bash
$ ghostclaw agent spawn /path/to/repo
agent> what's wrong?
[Agent responds with streaming]
agent> explain nesting depth
[Agent explains concept]
agent> save my-session
```

### Phase 3: Backend Service Base (Week 2)
**Goal**: FastAPI wrapper around core logic

**Tasks**:
- [ ] Create FastAPI app (`app/main.py`)
- [ ] Database models (User, Analysis, Team)
- [ ] `/api/v1/analyses` POST endpoint (sync first)
- [ ] `/api/v1/analyses/{id}` GET endpoint
- [ ] Error handling & validation
- [ ] Docker setup (single container)
- [ ] Tests: `test_batch_api_flow.py`

**Deliverables**:
- Synchronous API working
- Database persistence
- Docker image

### Phase 4: Async Job Queue (Week 2-3)
**Goal**: Decouple analysis from HTTP request

**Tasks**:
- [ ] Setup Redis (docker-compose)
- [ ] Setup Celery (`app/tasks/celery_app.py`)
- [ ] Create `analyze_task.py` (calls `GhostAgent.analyze()`)
- [ ] Refactor `/api/v1/analyses` to queue task
- [ ] Implement `/api/v1/analyses/{id}/status`
- [ ] Docker: separate API, worker, beat
- [ ] Tests: Queue, polling, workers

**Deliverables**:
- Async job queue
- Non-blocking API
- Multiple worker support

### Phase 5: Authentication & RBAC (Week 3)
**Goal**: User isolation & security

**Tasks**:
- [ ] JWT auth system (`auth/jwt_handler.py`)
- [ ] User registration & login endpoints
- [ ] Protect all endpoints with `@Depends(get_current_user)`
- [ ] Quota tracking & enforcement
- [ ] Team model & team endpoints
- [ ] Audit logging
- [ ] Tests: Auth flows, permissions

**Deliverables**:
- User management
- JWT tokens
- Quotas
- Team support

### Phase 6: Interactive Agent via WebSocket (Week 3-4)
**Goal**: Interactive chat over backend service

**Tasks**:
- [ ] WebSocket endpoint `/ws/agent/{session_id}`
- [ ] Load `AgentSession` from DB
- [ ] Integrate with `GhostAgent.chat_turn()`
- [ ] Streaming over WebSocket
- [ ] Connection management & error handling
- [ ] Session persistence (DB)
- [ ] Tests: `test_interactive_api_flow.py`

**Deliverables**:
```javascript
ws = new WebSocket('ws://localhost:8000/ws/agent/...')
ws.send({action: "chat", message: "what's wrong?"})
// Real-time streaming response
```

### Phase 7: Observability & Scaling (Week 4)
**Goal**: Production-ready

**Tasks**:
- [ ] Distributed tracing (Logfire + OTLP)
- [ ] Metrics collection (Prometheus)
- [ ] Structured logging (JSON)
- [ ] Rate limiting middleware
- [ ] Health checks
- [ ] Docker Compose with monitoring
- [ ] K8s manifests (optional)
- [ ] Load testing

**Deliverables**:
- Full observability
- Rate limiting
- Production readiness

### Phase 8: Frontend Integration (Week 4-5)
**Goal**: Connect Next.js to backend

**Tasks**:
- [ ] Update Next.js to call API (batch)
- [ ] Add WebSocket client (interactive)
- [ ] Chat component for agent
- [ ] Real-time streaming UI
- [ ] Session management
- [ ] Authentication flow

**Deliverables**:
- Next.js + backend integration
- Web UI for both batch & interactive

---

## PART 7: COMPARISON TABLE

The three modes share the SAME CORE:

| Feature | Batch CLI | Interactive CLI | Backend Service |
|---------|-----------|-----------------|-----------------|
| **Entry Point** | `ghostclaw /path` | `ghostclaw agent spawn /path` | `POST /api/v1/analyses` |
| **Core Used** | `GhostAgent.analyze()` | `GhostAgent.chat_turn()` + session | `Celery task` → `GhostAgent.analyze()` + WebSocket |
| **Database** | Optional (file cache) | File-based session | PostgreSQL (required) |
| **Auth** | None | None | JWT |
| **Scalability** | Single machine | Single machine | Multi-worker |
| **Latency** | Immediate | Immediate | Async (polling/WebSocket) |
| **State** | None | Session file | DB + Redis |
| **Multi-user** | No | No | Yes |
| **Live Updates** | No | Terminal | WebSocket streaming |

---

## PART 8: SUMMARY TABLE: WHAT'S NEW, WHAT'S UNCHANGED

### ✅ UNCHANGED (From existing CLI)
```
src/ghostclaw/core/
├── analyzer.py          (CodebaseAnalyzer)
├── adapters/            (Plugin system)
├── llm_client.py        (LLM integration)
├── models.py            (ArchitectureReport, etc)
├── stacks/              (Language detection)
├── metrics.py           (Vibe score formulas)
└── ... everything else
```

### 🆕 NEW/ENHANCED
```
src/ghostclaw/core/
├── agent.py             (UPDATED: added .chat_turn() method)
└── agent_session.py     (NEW: interactive state management)

src/ghostclaw/cli/
├── commands/agent.py    (NEW: interactive command)
└── formatters/          (UPDATED: streaming support)

app/                     (NEW: Backend service)
├── api/v1/agent.py      (NEW: WebSocket endpoint)
├── services/
│   └── agent_service.py (NEW: service orchestration)
├── tasks/
│   └── analyze_task.py  (NEW: Celery integration)
└── ...
```

---

## PART 9: MIGRATION PATH (IF UPGRADING EXISTING CLI)

For users with existing v0.2.5 CLI:

```
v0.2.5 (Current CLI)
    ↓
v1.0.0 (Unified Platform)
    ├── CLI batch mode: ghostclaw /path (unchanged)
    ├── CLI interactive (NEW): ghostclaw agent spawn /path
    ├── Backend service (NEW): docker-compose up
    └── Web UI (NEW): Next.js frontend
```

**No breaking changes** for existing CLI users:
- `ghostclaw /path --json` still works identically
- All core logic unchanged
- New `agent` command is opt-in

---

## PART 10: QUICK START

### Quick Start: Batch CLI (Existing)
```bash
pip install ghostclaw
ghostclaw /path/to/repo --use-ai --json
```

### Quick Start: Interactive CLI (NEW)
```bash
pip install ghostclaw
ghostclaw agent spawn /path/to/repo
agent> what's the biggest issue?
agent> explain nesting depth
agent> exit
```

### Quick Start: Backend Service (NEW)
```bash
cd ghostclaw-backend
docker-compose up
# API available at http://localhost:8000
# Web UI available at http://localhost:3000
```

### Quick Start: Interactive Agent (Service)
```javascript
// JavaScript client
const ws = new WebSocket('ws://localhost:8000/ws/agent/session-123?token=JWT');

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: "chat",
    message: "What's the biggest code smell?"
  }));
};

ws.onmessage = (event) => {
  const {type, chunk} = JSON.parse(event.data);
  if (type === "stream") {
    console.log("Agent:", chunk);  // Real-time
  }
};
```

---

## SUMMARY

**Ghostclaw v1.0** adalah **unified platform** dengan **single core logic** yang dapat diakses melalui:

1. **Batch CLI** (`ghostclaw /path`) — Existing, unchanged
2. **Interactive CLI** (`ghostclaw agent spawn`) — New, local development
3. **Backend Service** (`docker-compose up`) — New, production-grade

**No code duplication**. **Shared core**. **Multiple interfaces**.

---

**END OF UNIFIED ARCHITECTURE BLUEPRINT**

Generated: March 30, 2026  
Integration: REVIEW.md + BACKEND_ARCHITECTURE_BLUEPRINT.md + INTERACTIVE_AGENT_ARCHITECTURE.md  
Status: Ready for implementation
