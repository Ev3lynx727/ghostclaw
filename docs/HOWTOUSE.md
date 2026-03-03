# How to Use Ghostclaw

Ghostclaw is an architectural sentinel designed to analyze your codebase's health, dependencies, and "vibes". Because of its solid `src/` layout, it can be executed in several robust ways depending on your environment.

This document covers all the practical ways you can use Ghostclaw.

---

## 1. Using the Command Line Interface (CLI)

The most common way to run Ghostclaw is via the CLI. If you have installed Ghostclaw globally or within a virtual environment using `pip install .` or `pipx install .`, the `ghostclaw` command will be available on your path.

### Basic Usage

To analyze a local repository:

```bash
ghostclaw /path/to/your/project
```

### Advanced Engine Toggles

Ghostclaw supports switching its internal analysis engines for deeper or faster insights.

* **PySCN (Fast Dead Code & Clones)**: Assumes you have PySCN installed.

    ```bash
    ghostclaw /path/to/your/project --pyscn
    ```

* **AI-CodeIndex (Deep AST Graphing)**: Utilizes `tree-sitter` for advanced semantic coupling detection. Requires `ai-codeindex` to be installed (e.g., `pip install ai-codeindex[all]`).

    ```bash
    ghostclaw /path/to/your/project --ai-codeindex
    ```

* **JSON Output**: Useful for piping results into `jq` or other CI/CD tools.

    ```bash
    ghostclaw /path/to/your/project --json > report.json
    ```

---

## 2. Using the Shell Scripts (`scripts/`)

If you want to run Ghostclaw directly from the cloned repository **without** installing it via `pip`, you can use the provided wrapper scripts in the `scripts/` directory. These scripts automatically handle `PYTHONPATH` resolution for the `src/` layout.

### Single Repository Review

```bash
./scripts/ghostclaw.sh /path/to/your/project
```

### Multi-Repository Watcher

To run Ghostclaw against multiple repositories automatically (useful for cron jobs):

1. Add your repositories to `scripts/repos.txt` (one path/URL per line).
2. Run the watcher:

    ```bash
    ./scripts/watcher --repos-file scripts/repos.txt
    ```

### Repository Comparison

To compare the architectural trends of multiple repositories and generate a formatted report:

```bash
./scripts/compare.sh --repos-file scripts/repos.txt
```

---

## 3. Using the Python API

You can import Ghostclaw directly into your own Python scripts or automated testing pipelines.

```python
from ghostclaw.core.analyzer import CodebaseAnalyzer

# Initialize the analyzer
analyzer = CodebaseAnalyzer()

# Perform the analysis
report = analyzer.analyze("/path/to/your/project")

print(f"Overall Architectural Vibe Score: {report['vibe_score']}/100")
print("Top Issues:")
for issue in report['issues'][:3]:
    print(f"- {issue}")
```

### Enabling Optional Engines in Python

You can specifically request the external analysis wrappers:

```python
report = analyzer.analyze(
    "/path/to/your/project",
    use_pyscn=True,
    use_ai_codeindex=True
)
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
