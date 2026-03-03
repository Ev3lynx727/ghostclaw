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

This is the heart of the sentinel. It orchestrates the scanning sequence:

* **`analyzer.py`**: The primary coordinator. Scans files, initializes the correct `stacks` analyzer, processes optional engine plugins, and calculates the final vibe score.
* **`detector.py`**: Heuristic analysis. Detects the tech stack of the repository based on file extensions and critical files like `Cargo.toml` or `package.json`.
* **`validator.py`**: The rules engine. Reads YAML pattern references and validates the codebase against architectural best practices.
* **`cache.py`**: In-memory and disk caching subsystem to avoid re-parsing unchanged Git commits between runs based on git fingerprints.
* **External Engine Wrappers**: Contains `pyscn_wrapper.py` and `ai_codeindex_wrapper.py` to seamlessly integrate external CLI AST tools into Ghostclaw's internal issue lists when explicitly requested by users.

### `src/ghostclaw/cli/`

Contains the argument parsers and formatted outputs.

* **`ghostclaw.py`**: Provides the main ad-hoc terminal command. Prints formatted Markdown or JSON.
* **`compare.py`**: Retrieves cache history to compare trends across multiple repositories.

### `src/ghostclaw/stacks/`

Strategy pattern implementations for parsing language-specific complexities.
Every language parser must conform to a unified interface (`BaseAnalyzer`) to yield consistent metric scales (0-100 scores, issues, circular dependencies) back to the core analyzer. Support currently includes Python and NodeJS heuristics.

### `src/ghostclaw/lib/`

Houses agnostic utilities used by the system but not specifically related to AST code analysis.

* **`github.py`**: Standardized class for interacting with GitHub's REST API, handling token auth and PR generation.
* **`cache.py`**: Manages the persistent disk store (`~/.cache/ghostclaw/`) for longitudinal watcher trends.
* **`notify.py`**: External webhook dispatches (e.g., Telegram bots) when thresholds decay.

### `src/ghostclaw_mcp/`

Provides the `server.py` implementation of the Model Context Protocol (MCP). It wraps `core.analyzer` into distinct JSON endpoints that LLMs like Claude can interface with autonomously.

---

## Execution Flow

1. **Invocation**: Initiated via CLI (`ghostclaw`), MCP server tool call, or cron script (`watcher`).
2. **Detection**: `core.detector` scans path files to understand stack and scope.
3. **Graphing**: `core.analyzer` builds base metrics and optionally delegates to PySCN or AI-CodeIndex if higher AST fidelity is requested.
4. **Validation**: Evaluated AST representations are piped into `core.validator` which diffs against parsed `references/*.yaml` patterns.
5. **Reporting**: A final `vibe_score`, `issues` array, and structural `ghosts` array are returned up the stack.
6. **Action**: If triggered by a `watcher`, `lib.github` opens a remediation PR, updates local `lib.cache`, and optionally pings `lib.notify`.
