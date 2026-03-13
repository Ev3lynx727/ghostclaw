# Changelog

All notable changes to Ghostclaw will be documented here.

## [0.2.0] - 2026-03-12

### Added

- **QMD Backend (experimental)** — High-performance alternative to SQLite storage
  - `--use-qmd` CLI flag and `use_qmd` config option
  - `QMDMemoryStore` adapter implements MemoryStore interface (currently SQLite-based, path to true vector DB)
  - Dual-write mode: when enabled, writes to both SQLite and QMD for smooth transition
- **JSON5 Config Support** — Configuration files now support JSON5 (comments, trailing commas) when `json5` package is installed
  - `ConfigService.init_project()` writes JSON5 template if available
  - Automatic fallback to stdlib `json` when `json5` not present
- **Storage Reorganization** — Standardized `.ghostclaw/storage/` layout
  - Reports: `.ghostclaw/storage/reports/`
  - Cache: `.ghostclaw/storage/cache/`
  - Database: `.ghostclaw/storage/ghostclaw.db`
  - **Automatic migration** from legacy `.ghostclaw/{reports,cache,ghostclaw.db}` on first run
- **Delta-Context Enhancements**
  - VCS metadata in reports: `metadata.vcs.commit`, `metadata.vcs.branch`, `metadata.vcs.dirty`
  - Exact base matching by commit SHA (fallback to latest with warning)
  - `--delta-summary` flag to print diff statistics (files changed, insertions, deletions)
- **Color-coded Terminal Output** — ANSI colors for vibe score (green/yellow/orange/red) and section headers (Issues, Ghosts, Flags)

### Changed

- Delta-Context (v0.1.10) integrated as part of v0.2.0 release (no separate version)
- `_find_base_report()` now accepts `base_ref` parameter and resolves to commit SHA for precise matching
- `ConfigService.init_project()` template includes new `use_qmd` option
- `SQLiteStorageAdapter` storage path moved to `.ghostclaw/storage/ghostclaw.db`

### Fixed

- Security check for local API key now correctly raises error (not swallowed)
- Migration function robust to missing directories
- `--delta-summary` safe with `getattr` to avoid attribute errors in tests

### Testing

- 209 unit/integration tests passing, 2 skipped
- New tests: QMDMemoryStore (5), QMDStorageAdapter (4), migration, config loading, terminal formatting with ANSI

### Documentation

- Added MCP client configuration examples for Claude Desktop, Cursor, VS Code, OpenCode, Antigravity
- New `MIGRATION_GUIDE.md` with detailed upgrade instructions from v0.1.x
- Expanded README with QMD, JSON5, storage layout, and delta-summary

---

## [0.1.9] - 2026-03-12

### Added

- **MemoryStore** — Persistent SQLite-backed analysis history
- **Agent memory search** — MCP tools for cross-run queries:
  - `ghostclaw_memory_search` — keyword search with snippets
  - `ghostclaw_memory_get_run` — fetch full report by ID
  - `ghostclaw_memory_list_runs` — list recent runs
  - `ghostclaw_memory_diff_runs` — compare two runs
  - `ghostclaw_knowledge_graph` — aggregate trends and recurring issues
- 25 unit tests + 5 integration tests for memory tools

### Changed

- **CLI architecture** — Full modular commander pattern, auto-discovery, services, formatters
- Performance — parallel scanning by default; auto-enables for large repos (>5000 files)

### Performance

- Memory search: ~5ms (1000 runs), knowledge graph: ~7.5ms, get run: ~0.6ms

### Fixed

- Struct compatibility for issues/ghosts/flags in memory operations

---

## [0.1.8] - 2026-03-11

### Added

- Modular CLI foundation with dual-mode (modern + legacy fallback)
- Warning for `--no-parallel` to prevent timeouts
- Performance profiling tools

[Older history omitted]
