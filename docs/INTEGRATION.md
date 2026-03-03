# Ghostclaw Integration Guide

Ghostclaw is designed to operate not just as a standalone CLI tool, but as an embedded architectural sentinel within larger AI agent ecosystems and CI/CD pipelines.

This guide details the primary ways to integrate Ghostclaw into your workflows:

1. **As an OpenClaw Skill**
2. **As an MCP (Model Context Protocol) Server**
3. **With External Analysis Engines (PySCN & AI-CodeIndex)**
4. **Supported Agentic Platforms (VSCode, Antigravity, OpenCode)**

---

## 1. OpenClaw Skill Integration

Ghostclaw is natively packaged as a skill for the **[OpenClaw](https://github.com/Ev3lynx727/OpenClaw)** framework. This allows OpenClaw agents to invoke Ghostclaw's architectural vibe checking during autonomous development tasks.

### Installation via `npx`

You can run or install Ghostclaw directly using OpenClaw's CLI:

```bash
npx clawhub-cli install ghostclaw
```

### Metadata Configuration

The integration is defined in the `package.json` at the root of the repository:

```json
{
    "name": "ghostclaw",
    "openclaw": {
        "skill": true,
        "entry": "src/ghostclaw/cli/ghostclaw.py"
    }
}
```

This metadata tells OpenClaw that the repository is a valid skill and points to the primary CLI entry point.

---

## 2. Model Context Protocol (MCP) Server

Ghostclaw exposes an **MCP Server** that allows any compatible LLM or agent environment (like Claude Desktop) to invoke architectural analysis dynamically via tool calling.

### Available MCP Tools

The server exposes the following tools to the LLM:

* `ghostclaw_analyze(repo_path: str) -> str`: Performs a full architectural vibe analysis, returning the overall vibe score, identified structural issues, and architectural "ghosts".
* `ghostclaw_get_ghosts(repo_path: str) -> str`: A lightweight tool that skip the full report and only extracts the identified "ghosts" (hidden architectural smells).
* `ghostclaw_refactor_plan(repo_path: str) -> str`: Generates an actionable, markdown-formatted blueprint for refactoring the codebase based on the latest vibe score.

### Running the MCP Server

The server requires the optional `mcp` dependency. Ensure you install the project with:

```bash
pip install -e .[mcp]
```

Then, configure your MCP client to start the server:

```json
{
  "mcpServers": {
    "ghostclaw": {
      "command": "python",
      "args": ["-m", "ghostclaw_mcp.server"]
    }
  }
}
```

---

## 3. External Analysis Engines

Ghostclaw's core analysis engine (`CodebaseAnalyzer`) can be supercharged by integrating with dedicated AST parsing and logic-graphing tools. Currently, Ghostclaw supports two optional engines:

### PySCN

**PySCN** is utilized for high-speed dead code detection and code clone (copy-paste) analysis.

* **Invocation**: Pass `--pyscn` to the CLI, or `use_pyscn=True` to the Python API.
* **Wrapper**: `src/ghostclaw/core/pyscn_wrapper.py`
* **Requirement**: Requires the `pyscn` binary to be installed and available in your system `$PATH`.

### AI-CodeIndex

**AI-CodeIndex** replaces the default regex-based dependency graphing with advanced `tree-sitter` analysis, enabling deep inheritance tree mapping and cross-stack complex coupling detection.

* **Invocation**: Pass `--ai-codeindex` to the CLI, or `use_ai_codeindex=True` to the Python API.
* **Wrapper**: `src/ghostclaw/core/ai_codeindex_wrapper.py`
* **Requirement**: Requires the `ai-codeindex` binary to be installed and available in your system `$PATH`.

---

## 4. Supported Agentic Platforms

Ghostclaw is fully compatible with state-of-the-art agentic coding platforms and AI-enhanced IDEs:

* **VSCode**: You can run Ghostclaw seamlessly within the VSCode integrated terminal or via VSCode-compatible agent extensions.
* **OpenCode**: Ghostclaw can be integrated into OpenCode environments, allowing architectural vibe checks to be part of the automated code review loop.
* **Antigravity**: As a highly advanced AI system, Antigravity natively supports calling Ghostclaw via MCP or OpenClaw integration, utilizing it as an architectural sentinel.
