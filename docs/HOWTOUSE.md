# How to Use Ghostclaw

Ghostclaw is an architectural sentinel designed to analyze your codebase's health, dependencies, and "vibes". Because of its solid `src/` layout, it can be executed in several robust ways depending on your environment.

This document covers all the practical ways you can use Ghostclaw.

---

## 1. Using the Command Line Interface (CLI)

Since v0.1.6, Ghostclaw uses a **sub-command architecture**. To see all available commands:

```bash
ghostclaw --help
```

### Analyzing a Repository

To perform a full architectural review:

```bash
ghostclaw analyze /path/to/your/project
```

**Common Flags:**

- `--patch`: Generate AI-driven refactor blueprints and code diffs.
- `--no-cache`: Force a fresh analysis (ignore local history).
- `--json`: Output report in raw JSON format.

### Plugin Management

Ghostclaw 0.1.6 introduced the **Ghost Adapters** ecosystem. You can manage built-in and external plugins directly:

```bash
# List all active adapters and their status
ghostclaw plugins list

# Add an external adapter from a local directory
ghostclaw plugins add /path/to/external-adapter

# Remove a previously added external adapter
ghostclaw plugins remove adapter-name

# Generate a boilerplate adapter for development
ghostclaw plugins scaffold my-custom-adapter
```

---

## 2. Using the Shell Scripts (`scripts/`)

The wrapper scripts in `scripts/` are legacy-compatible but now delegate to the main `ghostclaw` entry point.

### Repository Comparison

To compare the architectural trends of multiple repositories and generate a formatted report:

```bash
./scripts/compare.sh --repos-file scripts/repos.txt
```

---

## 3. Using the Python API

For advanced integration, use the asynchronous `GhostAgent` or `CodebaseAnalyzer`.

```python
import asyncio
from ghostclaw.core.analyzer import CodebaseAnalyzer
from ghostclaw.core.agent import GhostAgent
from ghostclaw.core.config import GhostclawConfig

async def run_review():
    config = GhostclawConfig.load("/path/to/repo")
    analyzer = CodebaseAnalyzer()
    agent = GhostAgent(config, "/path/to/repo", analyzer=analyzer)
    
    # Run the full agent lifecycle
    report = await agent.run()
    
    print(f"Vibe Score: {report['vibe_score']}/100")

if __name__ == "__main__":
    asyncio.run(run_review())
```

---

## 4. Agentic Integrations (OpenClaw & MCP)

If you are using LLMs or autonomous agents, Ghostclaw serves as a powerful architectural context provider.

### OpenClaw

If installed via `npx clawhub-cli install ghostclaw`, your OpenClaw agents can autonomously trigger Ghostclaw using natural language:
> *"Ghostclaw, check the architectural integrity of this repository before we open the Pull Request."*

### Model Context Protocol (MCP)

If you are using Claude Desktop or another MCP-compatible client, Ghostclaw exposes MCP tools (`ghostclaw_analyze`, `ghostclaw_get_ghosts`, `ghostclaw_refactor_plan`).
Please see [docs/INTEGRATION.md](./INTEGRATION.md) for detailed MCP server configuration instructions.

---

## 5. Manual Installation as an OpenClaw Skill

If you prefer not to use `npx` or want a local copy of the skill, you can manually install Ghostclaw into your OpenClaw skills directory.

### The `skills` Branch: Ready-to-Copy Artifact

The repository maintains a `skills` branch that contains a self-contained package layout suitable for dropping directly into `~/.openclaw/skills/`. Do **not** use the `develop` branch for manual installation; it requires a full install via `pip` or the wrapper scripts.

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/Ev3lynx727/ghostclaw.git
cd ghostclaw

# Ensure you have the latest skills branch
git checkout skills
git pull origin skills
```

### Correct Directory Structure

After copying, your OpenClaw skills directory should look like:

```text
~/.openclaw/skills/ghostclaw/
├── SKILL.md
└── ghostclaw/
    ├── __init__.py
    ├── cli/
    ├── core/
    ├── lib/
    ├── stacks/
    └── references/
```

**Important:** The top-level `ghostclaw/` package directory is required. A common mistake is to copy only the contents of `src/ghostclaw/` directly into `~/.openclaw/skills/ghostclaw/` without the package wrapper, which results in import errors like:

```text
ModuleNotFoundError: No module named 'ghostclaw'
```

The `skills` branch already has the correct layout: the `ghostclaw/` package resides at the skill root alongside `SKILL.md`.

### Copy vs Symlink

You can either copy the files or create symlinks for live updates:

```bash
# Option A: Copy (static)
cp -r /path/to/ghostclaw/skills/* ~/.openclaw/skills/ghostclaw/

# Option B: Symlink (recommended for development)
rm -rf ~/.openclaw/skills/ghostclaw
ln -s /path/to/ghostclaw/ghostclaw ~/.openclaw/skills/ghostclaw/ghostclaw
ln -s /path/to/ghostclaw/SKILL.md ~/.openclaw/skills/ghostclaw/SKILL.md
```

### Verification

Test that the skill is importable by OpenClaw:

```bash
python3 -c "import sys; sys.path.insert(0, str(Path.home() / '.openclaw/skills/ghostclaw')); from ghostclaw.core.analyzer import CodebaseAnalyzer; print('Ghostclaw skill loaded OK')"
```

If you see no errors, the skill is ready. OpenClaw agents will now be able to invoke Ghostclaw.
