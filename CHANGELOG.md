# Changelog

All notable changes to the Ghostclaw project will be documented in this file.

## [0.1.5] - 2026-03-07 ([#9](https://github.com/Ev3lynx727/ghostclaw/pull/9))

### Added

- **Ghost Adapters Architecture**: Replaced monolithic tool logic with a modular **Adapter Pattern** ecosystem powered by `pluggy`.
- **Plugin Lifecycle Management**: Added a full suite of CLI commands for plugin management:
  - `ghostclaw plugins list`: Now distinguishes between **Built-in** and **External** plugins with rich table output.
  - `ghostclaw plugins add <path>`: Installs external adapters locally into `.ghostclaw/plugins/`.
  - `ghostclaw plugins remove <name>`: Safely deletes external adapters (with built-in protection).
  - `ghostclaw plugins scaffold <name>`: Generates boilerplate code for new custom adapters.
- **SQLite Storage Adapter**: Implemented asynchronous vibe history persistence using `aiosqlite`.
- **JSON Target Adapter**: Added a decoupled route for final report output, ideal for CI/CD and API integrations.
- **Async Engine Refactor**: Completely migrated `GhostAgent` and `CodebaseAnalyzer` to a non-blocking, asynchronous pipeline.
- **Enhanced MCP Performance**: Updated the MCP Server tools to use `async def`, enabling faster, parallelized architectural analysis.
- **Output Sandboxing**: Generated reports are now written into `<project_root>/.ghostclaw/`. The CLI automatically injects `.ghostclaw/` into the project's `.gitignore` to keep the git tree clean.
- **ContextBuilder**: Transforms AST graphs and metric reports into token-optimized, XML-tagged prompts for LLM consumption.
- **GhostclawConfig**: Pydantic-settings powered configuration with a strict hierarchy (`CLI > Env > Local > Global`). Includes a security guard that blocks loading `api_key` from a local `.ghostclaw.json`.
- **LLMClient**: Async REST client via `httpx` with exponential backoff (`tenacity`) and prompt token budgeting (`tiktoken`).
- **Rich TUI**: Animated terminal spinners during analysis, an `init` scaffolding command, and live-streaming AI responses that render as syntax-highlighted Markdown via the `rich` library.
- **`--dry-run` / `--verbose` flags**: New CLI flags for debugging and safe inspection without side effects.
- **Unit Tests**: Robust test coverage for new modules; all pre-commit steps verified.
- **Commander CLI Architecture**: Refactored the CLI to use a professional sub-command structure (`analyze`, `init`, `test`, `update`), improving extensibility and organization.
- **Agent Core Architecture**: Introduced `GhostAgent` with a lifecycle hook system (`INIT`, `PRE_ANALYZE`, `SYNTHESIS_CHUNK`, etc.), decoupling core logic from UI interfaces.
- **Official LLM SDK Migration**: Migrated `LLMClient` from manual `httpx` calls to official asynchronous SDKs (`openai>=1.0.0` and `anthropic>=0.30.0`) for better reliability and performance.
- **Diagnostic Tools**: Added `ghostclaw test --llm` to verify API connectivity and list available models from providers (OpenRouter, OpenAI, Anthropic).
- **Refactoring Patches**: Implemented the `--patch` flag to generate actionable AI-driven refactor suggestions and code diffs.

### Changed

- **Adapter Migration**: Ported `PySCN` and `AI-CodeIndex` into modular `MetricAdapters`.
- **Registration Idempotency**: Automated internal plugin registration to be idempotent, preventing duplicate tool loading.
- **Technical Debt Cleanup**: Removed legacy wrapper modules and 4 obsolete test files to streamline the codebase.
- **Test Suite Modernization**: Expanded the unit test suite to 77 passing tests, covering the new dynamic registry and adapter hooks.
- **CodebaseAnalyzer**: Refactored to work as a modular component orchestrated by `GhostAgent`.
- **Unit Tests**: Expanded coverage to 65+ passing tests, including full verification of the new agent and SDK layers.

## [0.1.4] - 2026-03-03

### Added

- **MCP Server Support**: Integrated OpenClaw-compatible MCP server in `ghostclaw_mcp/` exposing analyzing and planning as AI tools.
- **AI-CodeIndex Integration**: Added AST-based tree-sitter coupling logic to detect deep class hierarchies (optional dependency: `ai-codeindex`).
- **PySCN Integration**: Added support for structural clone detection and dead code identification (optional dependency: `pyscn`).
- **Feature Flags**: Added explicit CLI flags (`--pyscn`, `--ai-codeindex`) to `scripts/ghostclaw` and `scripts/watcher` to toggle engines manually.
- **Engine Badging**: Added CLI terminal badges to display active analysis engines (e.g., `🚀 Engines: PySCN, AI-CodeIndex`).
- **Documentation Overhaul**: Created `INTEGRATION.md`, `HOWTOUSE.md`, `ARCHITECTURE.md`, and `TROUBLESHOOT.md` guides.
- **Graceful Fallbacks**: Implemented non-breaking analyzer fallbacks when optional dependencies are missing but invoked.

### Changed

- **Standardised Layout**: Moved core modules (`cli/`, `core/`, `lib/`, `stacks/`) inside a `src/ghostclaw/` package to resolve namespace collisions (e.g., `ModuleNotFoundError: No module named 'core.analyzer'`).

## [0.1.3] - 2026-02-27

### Added

- **Build from Source**: Added instructions for building Ghostclaw from source.
- **Project License**: Added the MIT License file.
- **ClawHub Support**: Integrated ClawHub as the recommended installation method via `clawdhub`.
- **NPX Integration**: Added `package.json` to support installation via `npx skills add`.
- **Integration Guide**: Created `GUIDE.md` in `docs/` with comprehensive installation instructions.

### Removed

- **Legacy Installer**: Removed `scripts/install.sh` to reduce confusion for developers.

### Changed

- **Documentation Cleanup**: Improved formatting and layout of `SKILL.md` for better readability.
- **Task View Support**: Integrated with agentic task view and artifacts for better transparency in development.

## [0.1.2] - Previous

- Initial release of Ghostclaw as an OpenClaw skill.
- Core analyzer implementation for Python, Node, and Go.
- CLI and Watcher (Cron) scripts.
