# System Architecture

Ghostclaw analyzes complex codebases, evaluates architectural health ("vibes"), tracks metrics, and generates refactoring PRs. To achieve modularity and prevent naming collisions, the codebase is structured using the standard Python **src layout**.

---

## Directory Layout overview

```text
ghostclaw/
├── src/
│   ├── ghostclaw/           # Main Package Namespace
│   │   ├── cli/             # CLI entry points
│   │   ├── core/            # Core analysis, parsing, and ML logic
│   │   ├── lib/             # Utility modules (GitHub API, cache, notifications)
│   │   ├── stacks/          # Stack-specific (Python, Node, Go) analyzers
│   │   └── references/      # YAML configuration for best practices
│   │
│   └── ghostclaw_mcp/       # Optional MCP Server Package
│
├── scripts/                 # Utility shell wrappers and crons
├── docs/                    # Architectural guidelines and guides
├── tests/                   # Pytest suite
└── pyproject.toml           # Build system and dependency config
```

---

## Deep Dive into Submodules

### `src/ghostclaw/core/`

This is the heart of the system, now refactored for **asynchronous concurrency** and **modular extensibility**:

* **`agent.py`**: The high-level orchestrator (`GhostAgent`). Manages the analysis lifecycle, handles event hooks, and broadcasts results to storage and target adapters.
* **`analyzer.py`**: The technical coordinator (`CodebaseAnalyzer`). Orchestrates stack detection and delegates tool-specific metrics to the `PluginRegistry`.
* **`adapters/`**: contains the **Ghost Adapter Ecosystem**:
  * **`registry.py`**: A `pluggy`-powered manager (`PluginRegistry`) that dynamically loads built-in and external adapters.
  * **`base.py`**: Defines abstract base classes for `MetricAdapter`, `StorageAdapter`, and `TargetAdapter`.
* **`detector.py`**: Heuristic analysis for tech stack detection.
* **`validator.py`**: Validates codebases against architectural patterns defined in `references/*.yaml`.
* **`cache.py`**: Manages the local result cache to accelerate repeated runs.

### `src/ghostclaw/cli/`

Handles user interaction and formatted output.

* **`ghostclaw.py`**: The unified CLI entry point. Supports `analyze`, `plugins`, `test`, and `init` commands.
* **`compare.py`**: Compares architectural trends over time.

---

## Ghost Adapter Ecosystem

In v0.1.6, Ghostclaw adopted a modular adapter pattern to decouple core logic from external tools:

1. **Metric Adapters**: Encapsulate tools like `PySCN` or `AI-CodeIndex`. They provide structured issue and ghost data.
2. **Storage Adapters**: Handle persistence (e.g., `SQLiteStorageAdapter`).
3. **Target Adapters**: Handle final output delivery (e.g., `JsonTargetAdapter`).

External adapters can be added to `.ghostclaw/plugins/` and are automatically discovered via the `PluginRegistry`.

---

## Execution Flow (Async)

1. **Invocation**: Triggered via `ghostclaw analyze` or the MCP server.
2. **Discovery**: `PluginRegistry` loads all built-in and local external adapters.
3. **Detection**: `CodebaseAnalyzer` identifies the tech stack.
4. **Parallel Analysis**: `PluginRegistry` executes all active `MetricAdapters` concurrently using `asyncio`.
5. **Synthesis**: `GhostAgent` pipes metadata and metrics to the AI Engine (via `LLMClient`) for high-level architectural vibes.
6. **Broadcast**: `GhostAgent` emits completion events. `StorageAdapters` persist the report, and `TargetAdapters` deliver the final results.
