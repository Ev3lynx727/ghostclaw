# Contributing to Ghostclaw

Thank you for your interest in contributing to Ghostclaw!

## Development Environment

### Option 1: Dev Container (Recommended for Local Development)

Ghostclaw includes a Dev Container configuration for VS Code. This provides a consistent development environment with all dependencies pre-installed.

1. Install [Docker](https://docs.docker.com/get-docker/) and [VS Code](https://code.visualstudio.com/)
2. Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
3. Open the repository in VS Code
4. Click "Reopen in Container" when prompted (or use the Command Palette: "Dev Containers: Reopen in Container")

The container will:
- Build from Python 3.12 slim image
- Install all dependencies: `pip install -e ".[full]"`
- Pre-warm the embedding model for QMD features
- Configure Ruff linting and formatting

### Option 2: codesandbox.io (Quick Online Testing)

For quick experiments without local setup:

1. Go to [codesandbox.io](https://codesandbox.io)
2. Choose "Python" template
3. Push this repository (or fork it to your GitHub and import)
4. The `.codesandbox/` config will auto-install dependencies
5. Use the left sidebar "Tasks" panel to run:
   - **Analyze Sample** — test QMD analysis on `sample_repo/`
   - **Run Tests** — execute pytest suite
   - **Memory Stats** — check QMD metrics

No PostgreSQL or external services needed — everything runs in the sandbox.

### Option 3: Local Setup (Manual)

If you prefer to set up manually:

\`\`\`bash
# Clone and enter repository
git clone https://github.com/your-username/ghostclaw.git
cd ghostclaw

# Install all optional dependencies (QMD, semantic, complexity, etc.)
pip install -e ".[full]"

# Optional: pre-warm embedding model
python -c "from ghostclaw.qmd.embedding import EmbeddingManager; EmbeddingManager()"

# Run tests
pytest -xvs
\`\`\`

## Repository Structure

- \`src/ghostclaw/\` — core package
- \`src/ghostclaw/cli/commands/\` — CLI command implementations
- \`src/ghostclaw/cli/services/\` — business logic services
- \`tests/\` — unit and integration tests
- \`.codesandbox/\` — codesandbox.io configuration
- \`.devcontainer/\` — VS Code Dev Container configuration
- \`sample_repo/\` — minimal Python project for quick testing

For more details on architecture, see [PROJECT_SYMBOLS.md](PROJECT_SYMBOLS.md).

