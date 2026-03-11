# Ghostclaw

> "I see the flow between functions. I sense the weight of dependencies. I know when a module is uneasy."

Ghostclaw is an OpenClaw skill that provides an **architectural code review assistant** focused on system-level flow, cohesion, and tech stack best practices.

## Prerequisites

Before installing Ghostclaw, you must have [OpenClaw](https://openclaw.ai/) and [ClawHub](https://clawhub.ai/) installed on your system.

## Quick Start (Installation)

### Method 1: NPM (Recommended)

Install Ghostclaw globally from the npm registry:

```bash
npm install -g ghostclaw
```

### Method 2: NPX

To run it without explicitly installing globally:

```bash
npx ghostclaw /path/to/repo
```

You can also add it via OpenClaw skills:

```bash
npx skills add Ev3lynx727/ghostclaw
```

### Method 3: ClawHub

Install skills only via ClawHub by running:

```bash
clawhub install skill ghostclaw
```

### Method 4: Build from source

```bash
git clone https://github.com/Ev3lynx727/ghostclaw.git
cd ghostclaw
pip install .
```

For a detailed integration guide, see **[GUIDE.md](docs/GUIDE.md)**.

## Usage

### Run a review on a codebase

```bash
# If installed globally via NPM or Python
ghostclaw /path/to/your/repo

# If running from source
python3 src/ghostclaw/cli/ghostclaw.py /path/to/your/repo
```

### Background Monitoring (Cron)

Set up your repositories in a `repos.txt` file and add the native watcher binary to your cron jobs:

```bash
0 9 * * * ghostclaw-watcher /path/to/repos.txt
```

## What Ghostclaw Does

- **Vibe Score**: Assigns a 0-100 score representing architectural health.
- **Architectural Ghosts**: Detects code smells like "AuthGhost" or "ControllerGhost".
- **Refactor Blueprints**: Suggests high-level plans before code changes.
- **Sub-agent Mode**: Can be spawned via `openclaw sessions_spawn --agentId ghostclaw`.
- **Watcher Mode**: Monitors repositories and opens PRs with improvements.

## Files

```text
ghostclaw/
├── package.json — Package metadata for NPM and Skills CLI
├── SKILL.md — OpenClaw skill definition
├── docs/ — Documentation for Ghostclaw
├── scripts/ — Systemd service setup configuration
└── src/ghostclaw/ — Main Python package source
    ├── core/ — Core analysis orchestration
    ├── ghostclaw_mcp/ — Model Context Protocol (MCP) server
    ├── lib/ — Utilities (GitHub, Cache, Notify)
    ├── stacks/ — Stack-specific analysis strategies
    ├── cli/ — CLI implementation
    └── references/ — Architectural patterns
```

## Integrations

### Advanced Integrations (Phase 2)

Ghostclaw now supports several advanced extensions and optional dependencies.

#### MCP Server

Ghostclaw can now be used as an MCP server for Claude, Cursor, and other AI tools.

To install with MCP support:

```bash
pip install ghostclaw[mcp]
```

To run the MCP server:

```bash
ghostclaw-mcp
```

**Exposed Tools:**

- `ghostclaw_analyze`: Full vibe analysis.
- `ghostclaw_get_ghosts`: Architectural smells only.
- `ghostclaw_refactor_plan`: Automated blueprint generation.

#### Advanced Context & AST Indexing

By utilizing the `ai-codeindex` engine, Ghostclaw can extract full structural syntax trees and build extensive call graphs.

To install:

```bash
pip install ghostclaw[ai-codeindex]
```

#### Dead Code & Clone Detection

Ghostclaw can offload syntax-level checks for dead code and near-identical code blocks to `pyscn`.

To install:

```bash
pip install ghostclaw[pyscn]
```

#### Plugin Management CLI (v0.1.6)

Ghostclaw features a native plugin ecosystem. You can manage built-in and external adapters via the CLI:

```bash
# List all active adapters
ghostclaw plugins list

# Install an external adapter from a local folder
ghostclaw plugins add ./path/to/custom_adapter

# Scaffold a new developer template
ghostclaw plugins scaffold my-new-adapter
```

### Systemd Service (Phase 3)

For a persistent local MCP service, you can use the provided setup script which installs a `systemd` unit on Linux:

```bash
# Run from the source repository directory
npm run install-service
```

## Supported Stacks

- Node.js / React / TypeScript
- Python (Django, FastAPI)
- Go (Basic)

## Performance & Best Practices

Ghostclaw is designed to be fast out of the box, but for large repositories or specific use cases, consider these tips:

### Parallel Processing (Default)
- Parallel file scanning is **enabled by default** and highly recommended.
- The `--no-parallel` flag exists only for debugging; it causes a ~300× slowdown.
- If you accidentally use `--no-parallel` on a large repo (>5000 files), Ghostclaw will automatically re-enable parallel mode to prevent timeouts.

### Caching
- Ghostclaw caches analysis results to speed up repeated runs.
- Default cache TTL is 7 days. Use `--cache-ttl` to adjust.
- To disable caching (e.g., for CI), use `--no-cache`.
- Cache statistics can be shown with `--cache-stats`.

### Benchmarking
- Use `--benchmark` to see timing breakdown per analysis phase.
- This helps identify bottlenecks (e.g., file scanning, AI synthesis).

### Large Repositories
- For repos with >10k files, expect analysis to take several seconds even with parallelism (disk I/O bound).
- Consider increasing `--concurrency-limit` if you have a fast SSD and abundant CPU cores (default is 32).
- Use `--no-write-report` if you only need console output and want to reduce disk I/O.

### AI Synthesis
- AI synthesis (`--use-ai`) adds network latency (5-30s depending on provider and model).
- Use `--dry-run` to estimate token count without making API calls.
- Cache hits skip AI synthesis entirely if the code hasn't changed significantly.

### Troubleshooting Timeouts
- Ensure `parallel_enabled: true` in `~/.ghostclaw/ghostclaw.json`.
- Avoid `--no-parallel` on any non-trivial repository.
- For extremely large repos, consider analyzing a specific subdirectory instead of the entire codebase.

## License

MIT
