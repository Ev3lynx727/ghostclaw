# Changelog

All notable changes to the Ghostclaw project will be documented in this file.

## [0.1.8-draft] - Unreleased

### Added

- **Scoring Engine Refinement**: Implemented `ghost_analyze` in the Lizard adapter to gather detailed architectural metrics (CCN, Nesting Depth).
- **Structural Weighted Formula**: Implemented a 30/50/20 (CCN/Avg-ND/Avg-LoC) split, placing high priority on cognitive debt and readability.
- **Advanced Metrics Output**: CLI now displays `Avg CCN` and `Avg Nesting Depth` in terminal and Markdown reports.
- **`--no-ai` Flag**: New CLI flag to explicitly skip LLM synthesis while preserving high-fidelity metrics.
- **JSON-RPC 2.0 Bridge Server**: Rebuilt the communication layer for full specification compliance, including support for batch requests and standard RPC error codes.
- **`GhostBridge` Interface**: Standardized methods (`analyze`, `status`, `plugins`) to facilitate IDE extension and VS Code integration.

### Fixed

- **Config Precedence**: Fixed resolution order to ensure CLI flags correctly override environment variables and configuration files (`CLI > Env > Local > Global`).
- **Analyzer Detection**: Fixed a critical issue where Lizard extensions skipped function detection due to missing core processors in `FileAnalyzer`.
- **Bridge Import Errors**: Resolved `ImportError` for package version telemetry within the bridge execution context.
- **Architecture Model**: Added missing `coupling_metrics` field to `ArchitectureReport` for robust validation.

### Changed

- **Agent Guidelines**: Modernized `AGENTS.md` with up-to-date architectural patterns, extensibility hooks, and project structure.
- **CLI Command Redundancy**: Refactored the `bridge` command to use a unified server class, improving maintainability.

## [0.1.7] - 2026-03-09

### Added

- **Bridge Protocol**: Initial implementation of JSON-RPC 2.0 for external tool and IDE integration.
- **`ghostclaw doctor`**: New diagnostic command for environment, API, and plugin verification.
- **Event Bus**: Standardized internal notification system for progress, streaming, and logging.
- **Multi-Model Synthesis**: Experimental support for separate "Fast" and "Deep" models in analysis.
- **Scoring Engine**: Centralized core for "Vibe Score" calculations, supporting `ScoringAdapter` plugins.
- **Pyre-Check**: High-performance static type auditing integrated into `doctor` and future sentinel loops.
- **Dynamic `base_url`**: Support for custom API endpoints and local proxies (Ollama/VLLM).

### Changed

- **Adapter Registry**: Refactored for asynchronous result streaming.
- **LLM Client**: Enhanced streaming with support for "reasoning" deltas.

## [0.1.6] - 2026-03-08

### Added

- **Full Shell Stack Support**: Automated detection and specialized analysis for Bash/Zsh scripts.
- **First-Class TypeScript Support**: Dedicated stack detection and rules (interface naming, DDD patterns, optimized thresholds).
- **Docker Tech Stack**: Infrastructure as Code analysis for `Dockerfile` and Compose files with hygiene rules.
- **Enhanced Go Stack**: Improved validation of Go project layouts (`cmd/`, `internal/`) and naming conventions.
- **Global Empty Codebase Rules**: Specialized handling/reporting for projects with zero files to prevent hallucinatory analysis.
- **AI-CodeIndex deep-proxy**: Restored deep symbol telemetry flow into AI prompts for richer architectural context.
- **Parallel scanning** with configurable concurrency; 2–5× speedup on large repos.
- **Cache compression** (gzip) reduces disk usage ~50%.
- **Retry logic** with exponential backoff for LLM API calls.
- **Plugin management**: enable/disable per‑project; version compatibility checks.

### Fixed

- **JSON Serialization Error**: Fixed `AgentEvent` Enum serialization failure in the final analysis reports.
- **Lifecycle Clarity**: Standardized the `GhostAgent` execution flow into explicit "Diagnostics" and "Synthesis" phases.
- **TokenBudgetExceededError**: Resolved token budgeting issues in the LLM client.
- **Plugin Filtering**: Fixed plugin filtering at registration.
- **Version Import Cycle**: Resolved cyclical import issues related to versioning.

## [0.1.5] - 2026-03-07 ([#9](https://github.com/Ev3lynx727/ghostclaw/pull/9))### Added

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
