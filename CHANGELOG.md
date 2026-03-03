# Changelog

All notable changes to the Ghostclaw project will be documented in this file.

## [0.1.4] - 2026-03-03

### Added

- **MCP Server Support**: Integrated OpenClaw-compatible MCP server in `ghostclaw_mcp/` exposing analyzing and planning as AI tools.
- **AI-CodeIndex Integration**: Added AST-based tree-sitter coupling logic to detect deep class hierarchies (optional dependency: `ai-codeindex`).
- **PySCN Integration**: Added support for structural clone detection and dead code identification (optional dependency: `pyscn`).
- **Feature Flags**: Added explicit CLI flags (`--pyscn`, `--ai-codeindex`) to `scripts/ghostclaw` and `scripts/watcher` to toggle engines manually.
- **Engine Badging**: Added CLI terminal badges to display active analysis engines (e.g., `🚀 Engines: PySCN, AI-CodeIndex`).
- **Graceful Fallbacks**: Implemented non-breaking analyzer fallbacks when optional dependencies are missing but invoked.

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
