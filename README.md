# Ghostclaw

> "I see the flow between functions. I sense the weight of dependencies. I know when a module is uneasy."

Ghostclaw is an OpenClaw skill that provides an **architectural code review assistant** focused on system-level flow, cohesion, coupling metrics, and tech stack best practices.

## Quick Start

```bash
# Install the skill (if not already installed)
./scripts/install.sh

# Run a review on a codebase
./scripts/ghostclaw /path/to/your/repo
# or legacy: ./scripts/ghostclaw review /path/to/your/repo

# Set up background monitoring (cron)
# Edit scripts/repos.txt first, then:
0 9 * * * /path/to/ghostclaw/scripts/watcher.sh --notify
```

## What Ghostclaw Does

- Analyzes codebase structure (file sizes, module boundaries, import coupling)
- Detects "architectural ghosts" and circular dependencies
- Assigns a "vibe score" (0-100) representing architectural health
- Applies rule-based validation specific to your tech stack
- Suggests refactoring directions aligned with framework idioms
- Can run as a sub-agent via `openclaw sessions_spawn --agentId ghostclaw`
- Watcher mode can create draft PRs with improvements and send notifications

## Modes

- **Review mode**: `./scripts/ghostclaw <repo_path>` — one-shot analysis
- **Watcher mode**: `./scripts/watcher.sh [--dry-run] [--create-pr] [--notify]` — monitors multiple repos (configured via `scripts/repos.txt`)
- **Sub-agent**: Spawned by OpenClaw when `ghostclaw` codename is invoked

## Configuration

- `scripts/repos.txt` — List of repositories for watcher (one URL per line)
- `GH_TOKEN` — GitHub token for PR automation (optional)
- `NOTIFY_CHANNEL` — Telegram chat ID for alerts (optional)
- `references/stack-patterns.yaml` — Validation rules (customizable)

## Dependencies

- Python 3.8+
- Python packages: `pyyaml`, `python-dotenv` (install via `pip install -r requirements-dev.txt` or `pip install -e .`)
- Optional: `gh` (GitHub CLI) for PR creation
- Bash (for wrappers)

## Project Structure

See `SKILL.md` for the full breakdown of the refactored codebase organization.

## Currently Supported Stacks

- Node.js / React / TypeScript (with import coupling analysis)
- Python (Django, FastAPI)
- Go (basic detection)

## License

MIT
