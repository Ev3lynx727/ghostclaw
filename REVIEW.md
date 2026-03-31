# GHOSTCLAW PROJECT REVIEW
**Status**: Comprehensive Overview for Backend Service Conversion  
**Date**: March 30, 2026  
**Version**: 0.2.5a1 (Beta)

---

## 1. PROJECT OVERVIEW

### Purpose
Ghostclaw is an **architectural code review assistant** that analyzes codebases to detect architectural issues, code smells, dependency coupling, and provides a "vibe score" (architectural health metric). It's designed for system-level flow analysis, cohesion assessment, and tech-stack best practices validation.

### Core Value Proposition
- **Perceives Code Vibes**: Detects architectural debt and anti-patterns through composite metrics (nesting depth, cyclomatic complexity, LoC)
- **Pluggable Analysis**: Extensible adapter system for custom metrics, storage backends, and output targets
- **Multi-Stack Support**: Detects and analyzes Python, Node.js, Go, TypeScript, and generic shell projects
- **AI-Enhanced Reports**: Optional LLM synthesis for actionable insights and refactoring suggestions
- **CI/CD Ready**: Delta-context mode for PR reviews, batch processing, and automated reporting

### Current Distribution
- **NPM Package** (for OpenClaw skill ecosystem)
- **PyPI Package** (full CLI + library)
- **MCP Server** (Model Context Protocol for IDE integration)
- **Installed via ClawHub** (skill-only distribution)

---

## 2. BUSINESS LOGIC & KEY WORKFLOWS

### 2.1 Primary Workflow: Code Analysis Pipeline
```
User Input (repo path, flags)
  ↓
GhostAgent (Orchestrator)
  ├─ Detect Stack (Python, Node, Go, TypeScript, Shell)
  ├─ Initialize CodebaseAnalyzer
  ├─ Scan & Parse Files
  ├─ Compute Base Metrics
  ├─ Run Metric Adapters (Lizard, PySCN, AI-CodeIndex, etc.)
  ├─ Aggregate Results → ArchitectureReport
  ├─ [Optional] LLM Synthesis (OpenRouter, OpenAI, Anthropic)
  ├─ Cache Results (TTL + Compression)
  └─ Output (JSON, Markdown, JSON-RPC, Storage)
```

### 2.2 Vibe Score Computation (Core Metric)
The **vibe score** (0-100) combines three weighted dimensions:

| Dimension | Weight | Focus | Penalty |
|-----------|--------|-------|---------|
| **Nesting Depth (ND)** | 50% | Cognitive load | -10 if depth > 8 |
| **Cyclomatic Complexity (CCN)** | 30% | Logic branching | -10 if CCN > 25 |
| **Lines of Code (LoC)** | 20% | File size | N/A |

**Hotspot Trigger**: Files with extreme nesting or CCN get a -10 penalty (architectural red flag).

### 2.3 Delta-Context Analysis (PR Mode)
Analyzes only git diff instead of full codebase:
- Compare against `HEAD~1` (default) or any commit/branch/tag
- Used for **CI/CD integration** (fast, token-efficient)
- Report saved as `ARCHITECTURE-DELTA-<timestamp>.md` in `.ghostclaw/`
- Enables **drift detection** (compare against baseline)

### 2.4 Coupling & Dependency Analysis
- **Coupling Metrics**: Track inter-module dependencies
- **Supported**: Python (via `detector.py`), Node.js (package.json), Go (imports), TypeScript
- **Outputs**: Coupling graph, metrics per file, architectural ghosts (tight coupling patterns)

### 2.5 Configuration Resolution (Precedence)
```
1. CLI Flags (highest priority)
   └─ --use-ai, --no-ai, --delta, --base, etc.
2. Environment Variables
   └─ GHOSTCLAW_*, OPENAI_API_KEY, etc.
3. Local Config
   └─ <repo>/.ghostclaw/ghostclaw.json
4. Global Config (lowest priority)
   └─ ~/.ghostclaw/ghostclaw.json
```

---

## 3. ARCHITECTURE

### 3.1 High-Level Component Model

```
┌─────────────────────────────────────────────────────────────┐
│                          CLI / API Layer                     │
│  (src/ghostclaw/cli/ghostclaw.py | src/ghostclaw_mcp/)     │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ↓                           ↓
┌─────────────────────────┐  ┌──────────────────────────┐
│   GhostAgent            │  │   JSON-RPC Bridge        │
│ (core/agent.py)         │  │ (core/bridge.py)         │
│ - Orchestrates pipeline │  │ - Method: analyze        │
│ - Manages LLM calls     │  │ - Method: plugins        │
│ - Handles caching       │  │ - Method: status         │
└────────────┬────────────┘  └──────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────────────────┐
│            CodebaseAnalyzer (core/analyzer.py)              │
│  - Finds files (find_files, find_files_parallel)            │
│  - Computes base metrics (compute_metrics)                  │
│  - Dispatches to adapters (PluginRegistry)                  │
│  - Aggregates → ArchitectureReport                          │
└────────┬─────────────────────────────────┬──────────────────┘
         │                                 │
         ↓                                 ↓
┌────────────────────────┐      ┌─────────────────────────┐
│  Stack Detectors       │      │   PluginRegistry        │
│ (stacks/*.py)          │      │ (core/adapters/)        │
│ - Python               │      │ - MetricAdapter         │
│ - Node.js              │      │ - StorageAdapter        │
│ - Go                   │      │ - TargetAdapter         │
│ - TypeScript           │      │ - Version checks        │
│ - Shell                │      │ - Concurrency mgmt      │
└────────────────────────┘      └─────────────────────────┘
                                        │
         ┌──────────────────┬───────────┼────────────┬──────────────┐
         ↓                  ↓           ↓            ↓              ↓
    ┌─────────┐       ┌──────────┐ ┌─────────┐  ┌──────────┐  ┌──────────┐
    │ Lizard  │       │ PySCN    │ │AI-Code  │  │ QMD      │  │ Custom   │
    │ Scoring │       │ Coupling │ │Index    │  │ Vector   │  │ Adapters │
    │ Adapter │       │ Analyzer │ │Embedding│  │ Store    │  │ (plugins)│
    └─────────┘       └──────────┘ └─────────┘  └──────────┘  └──────────┘

         └────────────────── Metric Results ─────────────────────┘
                                  │
                                  ↓
                    ┌──────────────────────────┐
                    │  LLMClient               │
                    │ (core/llm_client.py)     │
                    │ - OpenRouter/OpenAI      │
                    │ - Anthropic              │
                    │ - Streaming & Batch      │
                    │ - Retry with backoff     │
                    └──────────────────────────┘
                                  │
                                  ↓
                    ┌──────────────────────────┐
                    │  Report Generation &     │
                    │  Output Routing          │
                    │ (JSON, Markdown, Storage)│
                    └──────────────────────────┘
```

### 3.2 Core Components

#### **GhostAgent** (`src/ghostclaw/core/agent.py`)
- **Responsibility**: Main orchestrator of the analysis workflow
- **Key Methods**:
  - `analyze()` — Detect stack, run CodebaseAnalyzer, optionally invoke LLM
  - Manages caching with TTL
  - Tracks timing (benchmarking)
- **Decision Points**:
  - Whether to use LLM synthesis (`use_ai` flag)
  - Cache hit/miss handling
  - Error recovery & reporting

#### **CodebaseAnalyzer** (`src/ghostclaw/core/analyzer.py`)
- **Responsibility**: Scan files, compute metrics, dispatch to adapters
- **Key Methods**:
  - `find_files()` / `find_files_parallel()` — Discover source files
  - `compute_metrics()` — Run base analysis (LoC, file counts)
  - `analyze()` — Main pipeline coordination
  - `save_report()` — Persist results via storage adapters
- **Dependencies**: PluginRegistry, Stack detectors, Metric adapters

#### **PluginRegistry** (`src/ghostclaw/core/adapters/registry.py`)
- **Responsibility**: Discover, load, and manage all adapters
- **Functions**:
  - Scans `src/ghostclaw/core/adapters/` for internal plugins
  - Loads external plugins from `<repo>/.ghostclaw/plugins/`
  - Validates version compatibility (min/max Ghostclaw version)
  - Runs adapters concurrently
  - Collects and reports errors without blocking
- **Adapter Categories**:
  - **MetricAdapter**: Analysis tools (Lizard, PySCN, AI-CodeIndex)
  - **StorageAdapter**: Vibe history backend (SQLite, Supabase, QMD)
  - **TargetAdapter**: Output routing (JSON files, webhooks, APIs)

#### **LLMClient** (`src/ghostclaw/core/llm_client.py`)
- **Responsibility**: Unified LLM interface for synthesis reports
- **Providers**:
  - OpenRouter (default)
  - OpenAI
  - Anthropic
- **Features**:
  - One-shot and streaming modes
  - Exponential backoff retry for failures
  - Token budget enforcement
  - Dry-run mode (preview prompt without API call)

#### **Cache** (`src/ghostclaw/core/cache.py`)
- **Responsibility**: Disk-based caching with TTL
- **Features**:
  - Custom TTL per cache entry
  - Gzip compression (to reduce disk footprint)
  - Fingerprinting for cache invalidation
  - Optional disabling via config

#### **GhostclawConfig** (`src/ghostclaw/core/config.py`)
- **Responsibility**: Centralized configuration management
- **Features**:
  - Pydantic-based validation
  - Multi-source loading (CLI, env, JSON files)
  - Schema validation with custom validators
  - Deep merge for partial overrides
  - Optional dependencies (QMD, Supabase, MCP)

### 3.3 Stack Detection (`src/ghostclaw/stacks/`)
Each stack module detects language/framework and customizes analysis:

| Stack | File | Detects | Customizes |
|-------|------|---------|-----------|
| **Python** | `python.py` | `pyproject.toml`, `setup.py`, `*.py` | Import coupling, decorators |
| **Node.js** | `node.py` | `package.json`, `*.js`, `*.ts` | NPM deps, module structure |
| **Go** | `go.py` | `go.mod`, `*.go` | Go imports, package structure |
| **TypeScript** | `typescript.py` | `tsconfig.json`, `*.ts` | Type analysis |
| **Docker** | `docker.py` | `Dockerfile` | Container analysis |
| **Shell** | `shell.py` | `*.sh`, `Makefile` | Generic fallback |

---

## 4. DATA MODELS

### 4.1 Core Models (`src/ghostclaw/core/models.py`)

#### **ArchitectureReport**
The main output object:
```python
ArchitectureReport(
    repo_path: str,
    vibe_score: int,                          # 0-100
    vibe_detailed: Dict,                      # Breakdown by dimension
    stack: str,                               # Detected tech stack
    files_analyzed: int,
    total_lines: int,
    issues: List[GhostIssue],                 # From adapters
    architectural_ghosts: List[str],          # Coupling, tight coupling
    red_flags: List[str],                     # Critical issues
    coupling_metrics: Dict,                   # Module dependencies
    errors: List[str],                        # Adapter/engine errors
    ai_prompt: Optional[str],                 # Used LLM prompt
    ai_synthesis: Optional[str],              # LLM response (synthesis, reasoning, patches)
    metadata: Dict                            # Fingerprint, timestamp, config hash
)
```

#### **GhostIssue**
Standardized issue format:
```python
GhostIssue(
    type: str,                                # 'issue', 'ghost', 'flag'
    id: str,                                  # Tool identifier
    message: str,
    file: Optional[str],
    line: Optional[int],
    severity: str,                            # 'low', 'medium', 'high', 'critical'
    metadata: Dict                            # Tool-specific details
)
```

#### **MetricSummary**
Quick summary of file-level metrics:
```python
MetricSummary(
    total_files: int,
    total_lines: int,
    large_file_count: int,
    average_lines: float,
    vibe_score: int,
    coupling_metrics: Dict
)
```

### 4.2 Adapter Interfaces
All adapters inherit from `BaseAdapter`:
```python
class BaseAdapter(ABC):
    async def is_available() -> bool          # Check if tool installed
    def get_metadata() -> AdapterMetadata     # Name, version, description
    async def analyze(root, files) -> Dict    # Run analysis
```

**Three Adapter Categories**:
1. **MetricAdapter** — Analysis engines (return issues, ghosts, flags)
2. **StorageAdapter** — Persistence backends (save/load reports)
3. **TargetAdapter** — Output routing (emit reports to external systems)

---

## 5. TECHNOLOGY STACK

### 5.1 Core Dependencies
| Dependency | Purpose | Version |
|-----------|---------|---------|
| **Python** | Runtime | ≥ 3.10 |
| **Pydantic** | Data validation, settings | ≥ 2.13.1 |
| **httpx** | Async HTTP client | ≥ 0.28.1 |
| **requests** | HTTP client (fallback) | ≥ 2.32.5 |
| **tenacity** | Retry logic | ≥ 9.0.0 |
| **rich** | Terminal UI (colors, tables) | ≥ 14.3.0 |
| **tiktoken** | Token counting (OpenAI) | ≥ 0.7.0 |
| **openai** | OpenAI API | ≥ 1.50.0 |
| **anthropic** | Anthropic API | ≥ 0.40.0 |
| **pluggy** | Plugin system | ≥ 1.0.0 |
| **aiosqlite** | Async SQLite | ≥ 0.20.0 |
| **lizard** | Code complexity scanning | ≥ 1.21.2 |
| **logfire** | Observability/telemetry | ≥ 4.30.0 |
| **pydantic-ai-slim** | LLM integration | ≥ 1.73.0 |

### 5.2 Optional Dependencies (Extras)

| Extra | Packages | Purpose |
|-------|----------|---------|
| **full** | MCP, AI-CodeIndex, PySCN | Complete feature set |
| **mcp** | mcp | IDE/protocol integration |
| **qmd** | lancedb, fastembed, numpy, pandas | Vector search backend |
| **supabase** | supabase | Cloud PostgreSQL storage |
| **orchestrator** | ghost-orchestrator | Plugin selection AI |
| **pyscn** | pyscn | Python coupling analysis |
| **ai-codeindex** | ai-codeindex | Semantic code indexing |
| **config** | json5 | Comments in config files |
| **telemetry** | logfire, opentelemetry-* | Observability |

### 5.3 Development Stack
- **Testing**: pytest (unit + integration)
- **Linting**: ruff
- **Formatting**: black
- **CI/CD**: GitHub Actions
- **Package Distribution**: setuptools, wheel, PyPI, NPM

---

## 6. PLUGIN SYSTEM (EXTENSIBILITY)

### 6.1 Three Plugin Types

#### **1. MetricAdapter** (Analysis Engines)
Add custom scanning capabilities:
```python
class CustomSecurityScanner(MetricAdapter):
    async def is_available(self) -> bool:
        return shutil.which("semgrep") is not None
    
    async def analyze(self, root: str, files: List[str]) -> Dict[str, Any]:
        return {
            "issues": [...],
            "architectural_ghosts": [...],
            "red_flags": [...]
        }
```

#### **2. StorageAdapter** (Persistence)
Custom vibe history backends:
```python
class PostgresStorage(StorageAdapter):
    async def save_report(self, report: ArchitectureReport) -> str:
        # Save to PostgreSQL, return report_id
        pass
    
    async def load_report(self, report_id: str) -> ArchitectureReport:
        # Load from PostgreSQL
        pass
```

#### **3. TargetAdapter** (Output Routing)
Emit reports to external systems:
```python
class SlackAlert(TargetAdapter):
    async def emit(self, report: ArchitectureReport) -> bool:
        # Post to Slack channel
        return True
```

### 6.2 Plugin Discovery & Lifecycle
- **Discovery**: Scans `<repo>/.ghostclaw/plugins/` for adapter subclasses
- **Version Checks**: Validates `min_version` and `max_version` compatibility
- **Concurrent Execution**: All adapters run in parallel with error isolation
- **Event Hooks**: `ghost_analyze`, `ghost_compute_vibe`, `ghost_emit` (pluggy-based)

### 6.3 Built-in Adapters
| Adapter | Type | Purpose |
|---------|------|---------|
| **Lizard** | MetricAdapter | Complexity & nesting scoring |
| **PySCN** | MetricAdapter | Python coupling analysis |
| **AI-CodeIndex** | MetricAdapter | Vector-based semantic analysis |
| **QMD** | StorageAdapter | Vector DB backend (LanceDB) |
| **SQLite** | StorageAdapter | Local database storage |
| **Supabase** | StorageAdapter | Cloud PostgreSQL backend |
| **JSON** | TargetAdapter | File-based output |
| **Orchestrator** | MetricAdapter | Plugin selection (LLM-driven) |

---

## 7. CURRENT FEATURES & STATUS

### 7.1 Major Features (v0.2.5)
✅ **Core Analysis**
- Multi-language code scanning
- Vibe score computation
- Coupling metrics
- Architectural pattern detection

✅ **AI Integration**
- OpenRouter, OpenAI, Anthropic support
- Streaming & batch synthesis
- Dry-run mode (preview without API call)

✅ **Reporting**
- JSON output (machine-readable)
- Markdown reports (human-readable)
- Delta-context analysis (PR mode)
- Custom formatters

✅ **Plugins & Extensibility**
- MetricAdapter, StorageAdapter, TargetAdapter system
- Version-aware plugin loading
- External plugin scanning (`.ghostclaw/plugins/`)
- Concurrent adapter execution

✅ **Storage & History**
- Disk cache with TTL & gzip
- SQLite persistence
- Vector DB backend (QMD with LanceDB)
- Supabase (PostgreSQL) cloud backend
- Report fingerprinting

✅ **MCP Server**
- FastMCP integration
- Tools: `ghostclaw_analyze`, `ghostclaw_memory_search`, `ghostclaw_refactor_plan`, `ghostclaw_knowledge_graph`
- IDE/agent integration

✅ **Telemetry & Observability**
- Logfire integration (native instrumentation)
- OpenTelemetry hooks (botocore, FastAPI, Redis, SQLite, etc.)
- Observability dashboard support

✅ **CI/CD Ready**
- GitHub Actions workflows
- Automated testing & linting
- TestPyPI + PyPI release automation

### 7.2 Recent Improvements (v0.2.4-v0.2.5)
- **Orchestrator CLI Flags**: `--orchestrate-verbose`, `--orchestrate-cache-dir`, `--orchestrate-history-len`
- **Config Deep-Merge**: Partial overrides preserve defaults (nested config safety)
- **Fingerprint Stability**: Orchestrator params included in cache fingerprint
- **Test Expansion**: 100+ new unit tests (core, CLI, QMD, vector store)
- **CI/CD Pipeline**: Lint, test, buildverification, automated releases
- **Python 3.12 Standardization**: `.python-version` file added
- **Supabase Integration**: Cloud-based report persistence

### 7.3 Known Limitations
- ⚠️ **Beta Status**: API may change before v1.0
- ⚠️ **Python-First**: NodeIndex, Go support maturing
- ⚠️ **Optional Dependencies**: Some features require extras (`--pre ghostclaw[full]`)
- ⚠️ **Single-Machine Cache**: Not distributed; per-repo local storage
- ⚠️ **LLM Cost**: AI synthesis adds API costs (OpenRouter, OpenAI, Anthropic)
- ⚠️ **Plugin Isolation**: No sandboxing; plugins run with full access

---

## 8. KEY WORKFLOWS & INTEGRATION POINTS

### 8.1 CLI Workflow (`src/ghostclaw/cli/`)
```
User Command
  ↓
Commander (Auto-discovery of Command subclasses from commands/)
  ↓
AnalyzeCommand (primary command)
  ├─ Parse arguments (flags, repo path)
  ├─ Load GhostclawConfig (resolution cascade)
  ├─ Initialize GhostAgent
  ├─ Call agent.analyze()
  ├─ Format output (JSON, Markdown, or raw)
  └─ Exit with status code
```

### 8.2 MCP (Model Context Protocol) Server
Enables IDE/LLM-agent integration:
- **Endpoint**: `src/ghostclaw_mcp/server.py`
- **Tools**:
  - `ghostclaw_analyze` — Run analysis on a directory
  - `ghostclaw_memory_search` — Query report history
  - `ghostclaw_refactor_plan` — Get refactoring suggestions
  - `ghostclaw_knowledge_graph` — Visualize dependencies

### 8.3 JSON-RPC Bridge
For direct API consumption (non-CLI):
```python
GhostBridge (src/ghostclaw/core/bridge.py)
  Methods:
    - analyze(repo_path, config)
    - status()
    - plugins()
    - ping()
```

### 8.4 Report Persistence & Storage
```
CodebaseAnalyzer.save_report()
  ↓
PluginRegistry finds StorageAdapters
  ├─ SQLiteStorageAdapter (local)
  ├─ QMDStorageAdapter (vector DB)
  ├─ SupabaseStorageAdapter (cloud PostgreSQL)
  └─ [Custom adapters]
  ↓
Report saved with fingerprint + metadata
```

---

## 9. BACKEND SERVICE CONSIDERATIONS

### 9.1 Current State for Service Conversion
**Strengths**:
- ✅ Modular architecture (GhostAgent, CodebaseAnalyzer, PluginRegistry)
- ✅ Async/await throughout (ready for concurrent requests)
- ✅ Configuration management (environment-aware)
- ✅ Multiple storage backends (SQLite, Supabase, Vector DB)
- ✅ Error handling & reporting (ArchitectureReport)
- ✅ MCP server scaffolding exists
- ✅ Comprehensive test suite (298+ tests)

**Gaps for Full Backend Service**:
- ⚠️ **No Job Queue**: Single-machine execution; no Celery/RQ integration
- ⚠️ **No Auth/RBAC**: No user/team isolation
- ⚠️ **No Rate Limiting**: No built-in throttling for API abuse
- ⚠️ **No API Framework**: Currently CLI-centric; needs FastAPI/Flask wrapper
- ⚠️ **Single-Machine Cache**: No distributed cache (Redis) integration
- ⚠️ **Limited Observability**: Logfire logs locally; no metrics aggregation
- ⚠️ **No Database Migrations**: Schema evolution not automated
- ⚠️ **No Request Tracking**: No correlation IDs for debugging

### 9.2 Recommended Architecture for Backend Service
```
┌─────────────────────────────────────────────────┐
│           FastAPI / REST API Layer              │
│  (routes for /analyze, /status, /reports/)      │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────┐
│            Auth & RBAC Layer                     │
│  (JWT, user context, team isolation)            │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────┐
│         Job Queue Integration                   │
│  (Celery/RQ for async analysis)                 │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────┐
│    GhostAgent + CodebaseAnalyzer                │
│    (existing business logic - NO CHANGES)       │
└──────────────────┬──────────────────────────────┘
                   │
   ┌───────────────┼───────────────┐
   ↓               ↓               ↓
PostgreSQL    Redis Cache    Blob Storage
(reports)     (hot data)      (cloned repos)
```

### 9.3 Service Endpoints (Proposed)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/analyze` | POST | Trigger analysis (async) |
| `/api/v1/analysis/{id}` | GET | Get analysis result |
| `/api/v1/analysis/{id}/status` | GET | Poll analysis status |
| `/api/v1/reports` | GET | List reports with filters |
| `/api/v1/reports/{id}` | GET | Get full report |
| `/api/v1/plugins` | GET | List available plugins |
| `/api/v1/health` | GET | Service health check |
| `/api/v1/queue/stats` | GET | Job queue statistics |

### 9.4 Implementation Strategy
1. **Phase 1**: Wrap existing GhostAgent in FastAPI (minimal changes)
2. **Phase 2**: Add async job queue (Celery/RQ) for long-running analyses
3. **Phase 3**: Implement auth (JWT + user context)
4. **Phase 4**: Add distributed cache (Redis) layer
5. **Phase 5**: Resource limits, rate limiting, observability

---

## 10. DIRECTORY STRUCTURE & KEY FILES

### 10.1 Source Organization
```
src/ghostclaw/
├── __init__.py
├── version.py                          # Version string
├── core/                               # Business logic
│   ├── agent.py                        # GhostAgent orchestrator
│   ├── analyzer.py                     # CodebaseAnalyzer
│   ├── analyzer/                       # Analyzer sub-components
│   ├── adapter*.py                     # Adapter base classes
│   ├── adapters/                       # Metric/Storage/Target adapters
│   │   ├── registry.py                 # Plugin discovery & loading
│   │   ├── lizard_adapter.py           # Complexity scoring
│   │   ├── pyscn_adapter.py            # Python coupling
│   │   └── storage/                    # Storage backends
│   ├── bridge.py                       # JSON-RPC 2.0 interface
│   ├── cache.py                        # Disk caching
│   ├── config.py                       # Configuration management
│   ├── coupling.py                     # Dependency coupling logic
│   ├── detector.py                     # File discovery
│   ├── git_utils.py                    # Git operations
│   ├── graph.py                        # Dependency graph
│   ├── llm_client.py                   # LLM integration
│   ├── memory.py                       # Report history store
│   ├── metrics.py                      # Vibe score formulas
│   ├── migration.py                    # Data migration utilities
│   ├── models.py                       # Pydantic models
│   ├── qmd/                            # Vector DB backend
│   ├── search_cache.py                 # Query caching
│   └── vector_store/                   # Vector search
├── cli/                                # Command-line interface
│   ├── ghostclaw.py                    # Entry point
│   ├── commander.py                    # Command discovery
│   ├── commands/                       # Command subclasses
│   ├── formatters/                     # Output formatters
│   ├── services/                       # Business logic services
│   └── ...
├── lib/                                # Shared utilities
│   ├── cache.py                        # Cache helpers
│   ├── github.py                       # GitHub API integration
│   ├── notify.py                       # Notifications
│   ├── complexity.py                   # Complexity calculations
│   └── __init__.py
├── references/                         # Reference data
├── stacks/                             # Language-specific logic
│   ├── base.py                         # Stack base class
│   ├── python.py                       # Python stack
│   ├── node.py                         # Node.js stack
│   ├── go.py                           # Go stack
│   ├── typescript.py                   # TypeScript stack
│   ├── docker.py                       # Docker analysis
│   └── shell.py                        # Generic/shell fallback
└── version.py

src/ghostclaw_mcp/
├── server.py                           # MCP server implementation
└── __init__.py

tests/
├── unit/                               # Unit tests (298+)
│   ├── test_*.py                       # Component tests
│   └── cli/commands/                   # CLI command tests
└── integration/                        # End-to-end tests
    └── test_*.py

docs/
├── ARCHITECTURE.md                     # Architecture deep-dive
├── CLI_ARCHITECTURE.md                 # CLI design
├── GUIDE.md                            # User guide
├── PLUGINS_GUIDE.md                    # Plugin development
├── HOWTOUSE.md                         # Quick start
├── TROUBLESHOOT.md                     # Troubleshooting
├── INTEGRATION.md                      # Integration patterns
├── ORCHESTRATOR.md                     # Plugin orchestrator
├── FAQ.md                              # FAQs
└── references.md                       # References
```

### 10.2 Configuration Files
| File | Purpose |
|------|---------|
| `pyproject.toml` | Package metadata, dependencies, build config |
| `.env.example` | Environment variables template |
| `.ghostclaw/ghostclaw.json` | Local repo config |
| `~/.ghostclaw/ghostclaw.json` | Global user config |
| `.python-version` | Python version (3.12) |

### 10.3 Important Modules Map

| Module | Exports | Responsibility |
|--------|---------|-----------------|
| `core/agent.py` | `GhostAgent` | Main orchestrator |
| `core/analyzer.py` | `CodebaseAnalyzer` | File scanning & metrics |
| `core/adapters/registry.py` | `PluginRegistry` | Plugin management |
| `core/llm_client.py` | `LLMClient` | LLM API abstraction |
| `core/cache.py` | `Cache` | Disk-based caching |
| `core/config.py` | `GhostclawConfig` | Config resolution |
| `core/models.py` | `ArchitectureReport`, `GhostIssue` | Data structures |
| `core/bridge.py` | `GhostBridge` | JSON-RPC interface |
| `cli/commander.py` | `Command`, `Commander` | CLI framework |
| `stacks/base.py` | `StackDetector` | Stack detection base |

---

## 11. DEVELOPMENT & TESTING

### 11.1 Test Coverage
- **Unit Tests**: 298+ tests covering core, CLI, adapters, config, etc.
- **Integration Tests**: PR review, telemetry, Supabase, orchestrator
- **Focus Areas**:
  - Config merging & resolution
  - Cache fingerprinting
  - Orchestrator plugin selection
  - Storage adapter lifecycle
  - CLI command discovery
  - LLM client retry logic

### 11.2 Running Tests
```bash
# All tests
python3 -m pytest

# Specific test
python3 -m pytest tests/unit/test_adapters.py -v

# With coverage
python3 -m pytest --cov=src/ghostclaw tests/

# Integration only
python3 -m pytest tests/integration/ -v
```

### 11.3 Development Setup
```bash
cd ghostclaw
pip install -e .[full,mcp]    # Install in dev mode with all extras
black .                         # Format code
ruff check --fix .             # Lint & fix
python3 -m pytest               # Run tests
```

---

## 12. METRICS & PERFORMANCE

### 12.1 Vibe Score Formula
```
ND_norm = min(nesting_depth / 5, 1.0)
CCN_norm = min(cyclomatic_complexity / 10, 1.0)
LoC_norm = min(lines_of_code / 1000, 1.0)

BASE_SCORE = 100 * (1 - 0.5*ND_norm - 0.3*CCN_norm - 0.2*LoC_norm)

if nesting_depth > 8 OR cyclomatic_complexity > 25:
    VIBE_SCORE = BASE_SCORE - 10
else:
    VIBE_SCORE = BASE_SCORE
```

### 12.2 Performance Benchmarks (v0.2.5)
- **1000-loop Analysis**: ~300ms baseline (profiling_1000runs.txt)
- **Parallel File Discovery**: N workers on N cores
- **Cache Hit**: <50ms (disk read + decompression)
- **LLM Synthesis**: 5-30s (depends on model & token count)

---

## 13. KNOWN ISSUES & ROADMAP

### 13.1 Current Issues (Tracked)
- None critical; beta version stable
- Plugin discovery error handling logged at DEBUG (avoid noise)
- Single-machine cache; no distributed support

### 13.2 Future Roadmap (Post v1.0)
1. **v0.3.0**: Job queue integration (Celery/RQ)
2. **v0.4.0**: User auth + RBAC
3. **v0.5.0**: Distributed cache (Redis)
4. **v1.0.0**: Stable API, full backend service
5. **v1.1.0**: WebUI dashboard

---

## 14. SECURITY CONSIDERATIONS

### 14.1 Current Security Posture
- ✅ UTF-8 encoding (no injection vulnerabilities from bytes)
- ✅ Pydantic validation (input sanitization)
- ✅ SHA256 fingerprinting (no weak hashing)
- ✅ Environment variable isolation (secrets not in logs)
- ⚠️ **Plugin Sandbox**: No isolation; plugins run with full access
- ⚠️ **API Keys**: Stored in env vars; no vault integration
- ⚠️ **Git Clone**: No size limits; could be abused

### 14.2 Recommended Additions
- API rate limiting (per user/IP)
- Request size limits
- Git clone size caps
- Plugin security manifest (permissions)
- Audit logging
- HTTPS enforcement (if service)

---

## 15. SUMMARY & NEXT STEPS

### 15.1 Strengths
1. **Solid Architecture**: Modular, async, testable
2. **Rich Plugin System**: Extensible metric/storage/target adapters
3. **Multi-Language**: Python, Node, Go, TypeScript support
4. **Production-Ready Features**: Caching, error handling, telemetry
5. **Well-Tested**: 298+ unit + integration tests
6. **AI-Enhanced**: LLM synthesis for actionable insights

### 15.2 Gaps for Backend Service
1. No async job queue (Celery/RQ)
2. No user authentication or RBAC
3. No API framework (FastAPI/Flask wrapper)
4. No distributed caching (Redis)
5. No rate limiting or resource quotas
6. No API versioning strategy

### 15.3 Recommended Conversion Path
```
Phase 1 (Week 1):
  └─ Wrap GhostAgent in FastAPI
     Add POST /analyze, GET /status, GET /report endpoints
     
Phase 2 (Week 2):
  └─ Integrate async job queue (Celery)
     Decouple analysis from request handling
     
Phase 3 (Week 3):
  └─ Add JWT auth layer
     Implement team/user isolation in storage
     
Phase 4 (Week 4):
  └─ Deploy & test in staging
     Add monitoring, rate limiting, error tracking
```

### 15.4 Files to Study Before Service Build
1. **`src/ghostclaw/core/agent.py`** — Main orchestrator (read first)
2. **`src/ghostclaw/core/analyzer.py`** — Analysis logic
3. **`src/ghostclaw/core/config.py`** — Configuration
4. **`src/ghostclaw/core/models.py`** — Data structures
5. **`docs/ARCHITECTURE.md`** — Deep architecture docs

---

## APPENDIX: QUICK REFERENCE

### Configuration Precedence
```
CLI flags > ENV vars > Local config (.ghostclaw/ghostclaw.json) > Global config (~/.ghostclaw/ghostclaw.json)
```

### Key Environment Variables
```
GHOSTCLAW_USE_AI=1
GHOSTCLAW_AI_PROVIDER=openrouter
GHOSTCLAW_AI_MODEL=anthropic/claude-3-sonnet
OPENROUTER_API_KEY=sk-...
GHOSTCLAW_USE_QMD=1
GHOSTCLAW_TELEMETRY=1
```

### Core Dependencies (Minimal)
```
pydantic, httpx, requests, tenacity, rich, pluggy, aiosqlite, lizard, logfire
```

### Optional Extras
```
[full] → MCP + AI models
[qmd] → Vector DB
[supabase] → Cloud storage
[orchestrator] → Plugin selection AI
```

### CLI Quick Commands
```bash
ghostclaw /path/to/repo                              # Basic analysis
ghostclaw /path/to/repo --use-ai                     # With LLM synthesis
ghostclaw /path/to/repo --delta --base origin/main   # PR review mode
ghostclaw /path/to/repo --json > report.json         # Machine-readable output
ghostclaw /path/to/repo --benchmark                  # Show timing
```

---

**END OF REVIEW**

Generated: March 30, 2026  
Ghostclaw Version: 0.2.5a1 (Beta)  
Review Scope: All components, architecture, business logic, extensibility, backend conversion readiness
