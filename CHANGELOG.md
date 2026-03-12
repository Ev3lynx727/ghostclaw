# Changelog

All notable changes to Ghostclaw will be documented here.

## [0.1.10] - 2026-03-12 (In Development)

### Added
- **Delta-Context Analysis** — PR-style analysis on git diffs instead of full codebase
  - `--delta` flag to enable delta mode
  - `--base <ref>` option to specify the diff target (default: HEAD~1)
  - Automatic base report loading from `.ghostclaw/reports/` for architectural drift detection
  - Delta-specific AI prompt with `<base_context>`, `<diff>`, and `<current_state>` sections
  - Report filename differentiation: `ARCHITECTURE-DELTA-<timestamp>.md`
  - JSON report includes delta metadata (`metadata.delta`)

### Changed
- `CodebaseAnalyzer.analyze()` now accepts delta mode via config and filters file scanning accordingly
- `ContextBuilder.build_delta_prompt()` creates delta-specific prompts for comparative synthesis
- Cache fingerprint includes delta parameters for proper cache separation

### Testing
- Unit tests for `build_delta_prompt()`
- Integration tests for delta mode file filtering and base report discovery
- 193 tests passing (no regressions)

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

[Older history omitted for brevity]
