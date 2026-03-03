# Ghostclaw

> "I see the flow between functions. I sense the weight of dependencies. I know when a module is uneasy."

Ghostclaw is an OpenClaw skill that provides an **architectural code review assistant** focused on system-level flow, cohesion, and tech stack best practices.

## Quick Start (Installation)

### Method 1: ClawHub (Recommended)

Install Ghostclaw via ClawHub:

```bash
npx clawdhub@latest install ghostclaw
```

### Method 2: NPX

```bash
npx skills add Ev3lynx727/ghostclaw
```

### Method 3: Build from source

```bash
git clone https://github.com/Ev3lynx727/ghostclaw.git
cd ghostclaw
pip install .
```

For a detailed integration guide, see **[GUIDE.md](docs/GUIDE.md)**.

## Usage

### Run a review on a codebase

```bash
# Via script
./scripts/ghostclaw.sh review /path/to/your/repo

# Via alias (if installed globally)
ghostclaw /path/to/your/repo
```

### Background Monitoring (Cron)

Set up your repositories in `scripts/repos.txt` and add to cron:

```bash
0 9 * * * /path/to/ghostclaw/scripts/watcher.sh
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
├── package.json — Package metadata for Skills CLI
├── SKILL.md — OpenClaw skill definition
├── docs/ — Documentation for Ghostclaw
├── core/ — Core analysis orchestration
├── ghostclaw_mcp/ — Model Context Protocol (MCP) server
├── lib/ — Utilities (GitHub, Cache, Notify)
├── stacks/ — Stack-specific analysis strategies
├── cli/ — CLI implementation
├── scripts/ — Entry points and deployment
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

### Systemd Service (Phase 3)

For persistent local service, use the provided `systemd` unit:

```bash
cp scripts/ghostclaw.service /etc/systemd/system/
systemctl enable ghostclaw
systemctl start ghostclaw
```

## Supported Stacks

- Node.js / React / TypeScript
- Python (Django, FastAPI)
- Go (Basic)

## License

MIT
