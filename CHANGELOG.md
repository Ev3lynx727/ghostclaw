# Changelog

All notable changes to Ghostclaw will be documented here.

## [v0.2.4] - Upcoming

### Added
- **Orchestrator CLI flags** — new options:
  - `--orchestrate-verbose` — print detailed planning info to stderr
  - `--orchestrate-cache-dir <path>` — specify custom plan cache directory
  - `--orchestrate-history-len <N>` — number of past runs for vector similarity (default: 20)
  - `--orchestrate-no-cache` — disable plan caching (alias)
- **Orchestrator configuration** — new fields:
  - `orchestrator.verbose` — enable verbose output
  - `orchestrator.cache_dir` — custom cache location
- **Comprehensive Orchestrator documentation** — added README section with LLM setup, config reference, troubleshooting

### Improved
- **Registry robustness** — early creation in `CodebaseAnalyzer.analyze()` guarantees availability for `save_report`, fixing "Analyzer registry not available" errors.
- **Duplicate plugin discovery** — noisy "Plugin name already registered" errors are now logged at DEBUG level; duplicates are skipped silently.
- **Config validation** — core `OrchestratorConfig` now validates:
  - `vector_weight + heuristics_weight ≈ 1.0`
  - `max_plugins`, `max_concurrent_plugins`, `plugin_history_lookback >= 1`
  - `plan_cache_ttl_hours >= 0`
- **CLI overrides builder** — correctly maps `--orchestrate-history-len` → `plugin_history_lookback`
- **Test coverage** — added 8 new unit tests for orchestrator CLI flags (total 21); full suite now 298 passed, 2 skipped.

### Fixed
- `test_cli_json_mode_streaming_to_stderr` — fixed registry mocking issue
- Orchestrator CLI tests — safe `getattr` usage for optional flags
- Cache fingerprinting includes orchestrator parameters for accurate invalidation

---

## [v0.2.3] - 2026-03-24

### Added
- **CI/CD Pipeline** — Introduced GitHub Actions for lint (ruff), test (pytest matrix), build verification, and automated releases (TestPyPI + PyPI).
- **Release Workflows** — `release-testpypi.yml` triggers on tag push; `release-pypi.yml` for manual promotion to production.
- **Comprehensive Test Suite** — Added 100+ new unit tests covering CLI, orchestrator, QMD, and vector store components.

### Improved
- **Orchestrator Config Normalization** — Refined handling of `--orchestrate` and `--no-orchestrate` flags; config semantics now consistent and predictable.
- **CLI Robustness** — Safe attribute access for optional flags (`getattr` usage) prevents crashes in test environments and edge cases.
- **Analyzer Registry Handling** — `CodebaseAnalyzer` now properly sets `self.registry` for post-analysis operations (e.g., save_report).
- **Non-Git Repo Support** — Gracefully handles analysis when `git` operations fail (e.g., not a git repo).
- **Lint Compliance** — Codebase now passes `ruff` check with zero errors (E701, E741, F401, etc.) under Python 3.12.

### Fixed
- **`test_cli_json_mode_streaming_to_stderr`** — Fixed registry mocking issue causing JSON output failure in `--json` mode.
- **Orchestrator CLI Tests** — Resolved `AttributeError` for missing optional CLI arguments by using safe defaults.
- **Configuration Deep-Merge** — Nested dict overrides now merge correctly, preserving default values.
- **Per-File Cache Global Data Preservation** — Global/cross-file results (coupling_metrics, symbol_index) no longer dropped during cached runs.
- **Delta Mode Base Report Discovery** — Improved async SHA resolution and error handling.

### Documentation
- Added `MIGRATION_GUIDE.md` for upgrading from v0.1.x to v0.2.x.
- Extended README with Orchestrator section (setup, CLI options, experimental status).
- Added benchmark scripts and QMD reference documentation.

### Tests
- All tests passing: **290 passed, 2 skipped** (Python 3.10, 3.11, 3.12).
- Added dedicated suites: `test_orchestrator_cli.py`, `test_orchestrator_integration.py`, `test_qmd_*`, `test_vector_store.py`.

---

## [v0.2.2a0] - Upcoming

### Added
- **Orchestrator Integration** — Introduced `--orchestrate` / `--no-orchestrate` CLI flags to enable adaptive plugin routing via the `ghost-orchestrator` plugin.
- **Orchestrator Config** — Added top-level `orchestrate` boolean (env: `GHOSTCLAW_ORCHESTRATE`) and `orchestrator` dict for fine-grained control (LLM, weights).
- **Multi-Dimensional Scoring (Vibe Engine)** — Introduced a stack-aware scoring model that breaks down the 0-100 score into Complexity, Coupling, Cohesion, Naming, and Layering dimensions.
- **Stack-Specific Profiles** — Handlers for Python, Go, JS/TS, and Rust logic thresholds ensure language-appropriate scoring metrics.
- **Orchestrator-Only Mode** — When enabled, only the orchestrator plugin runs (plus storage plugins if QMD is active), reducing analysis time by ~50% on real-world codebases.
- **Optional Dependency** — `ghostclaw[orchestrator]` installs `ghost-orchestrator>=0.1.1a1`.
- **40 New Unit Tests** — Comprehensive coverage for config, enforcement, and CLI behavior.

### Improved
- **Performance Foundation (Phase 1)** — Implemented a multi-layered optimization strategy:
  - **Async Git Layer**: Optimized `AsyncGitExecutor` and `DiffCache` (LRU) to reduce Git overhead.
  - **Intelligent Caching**: Added `PerFileAnalysisCache` using SHA-256 content hashing to skip analysis for unchanged files.
  - **O(1) Discovery**: Replaced linear scans with `BaseReportIndex` for instant report lookup by commit SHA.
  - **Near-Instant Diffing**: Introduced `FingerprintedRun` with pre-computed hashes for O(1) run comparisons.
  - **Pre-commit Analysis**: Added support for analyzing staged/unstaged changes via `AsyncGitExecutor.staged_diff()`.
- **Selective Plugin Execution**: Significantly lowers analysis time by executing only relevant adapters.
- **Backward Compatibility**: Maintained legacy `vibe_score` while adding granular `vibe_detailed` metrics to the `ArchitectureReport`.
- **Plugin Discovery**: Decoupled entry-point discovery from directory scanning, ensuring plugins are always found even when analyzing subdirectories.
- **Schema Flexibility**: Updated `ArchitectureReport.issues` to `List[Any]` to support structured plugin data (e.g., Coderabbit) without validation errors.

### Fixed
- **Bandit Plugin Timeout**: Added `timeout` support to the `AsyncProcessMetricAdapter` base class and fixed the Bandit plugin's handling of asynchronous timeouts.
- **Plugin Discovery Regression**: Fixed an issue where entry-point plugins (like `orchestrator`) were not discovered unless a local `.ghostclaw/plugins` directory existed.

---

## [v0.2.1-beta] - 2026-03-17

### Added
- **Phase 5: Migration** — `EmbeddingBackfillManager` for legacy QMD reports; auto-migration on startup; resumable state; CLI `ghostclaw qmd migrate status|stop|trigger`.
- **Phase 6: Vector Optimization** — Optional IVF-PQ index (`VectorIndex.ensure_index()`); `QueryClassifier` for adaptive alpha; `max_chunks_per_report` diversity limit.
- **docs/references.md** — Comprehensive source code reference for plugin developers.
- **Plugin Auto-Discovery** — Ghostclaw now automatically discovers plugins installed via setuptools entry points (`ghostclaw.plugins` group). This eliminates manual copying to `.ghostclaw/plugins/` and simplifies CI/CD. See `PLUGINS.md` for details.
- **README Update** — Installation section now includes both `npm` and `pip` methods for clarity.

### Changed
- **AI-Buff** features (caching, prefetch, query planning) are now production-ready (removed experimental label).
- **QMD backend** is now considered stable for general use.
- **Config:** Added `embedding_model` option to customize model name for `sentence-transformers` or `openai` backends (fastembed uses its own default).
- **Versioning** — Pre-release versions now use `-beta` suffix (e.g., `0.2.1-beta`).

### Fixed
- CLI import error: added `migrate_legacy_storage` stub in `core/migration.py`.
- **`ghostclaw qmd-migrate` NameError**: Fixed missing `parser` reference in command handler.
- **PySCN integration**: Gracefully handle repositories with no Python files (no false error issues).
- **Dependencies**: Added `pandas` to `qmd` extra (required for vector store table scans). CI installs `.[qmd]` to get all QMD deps.

---

## [v0.2.0-beta] - 2026-03-17

### Added
- **QMD Hybrid Search** — combines BM25 (SQLite FTS5) with vector embeddings (LanceDB) for superior retrieval.
- **Fastembed by default** — torch-free ONNX embeddings (~200MB) with CPU-optimized runtime.
- **Configurable backends** — `--embedding-backend` choosing `fastembed` (default), `sentence-transformers`, or `openai`.
- **Performance breakthrough** — BM25 search ~1ms p50 (1000 reports); hybrid ~15-25ms estimated.
- **Full test coverage** — 20/20 QMD-specific tests passing.

### Improved
- **Search performance** — Legacy substring replaced with FTS5 → ~80× faster.
- **Memory efficiency** — Vector store isolated per-db (`.ghostclaw/storage/qmd/lancedb/`).
- **Error handling** — Graceful fallback chain: hybrid → BM25 → legacy.

### Fixed
- SQLite function registration: `extract_searchable_text()` now connection-local.
- `QMDMemoryStore` default `use_enhanced=False` preserves legacy behavior.
- Vector store schema uses proper `pyarrow.Schema`.
- Fastembed integration: handle generator, correct model ID.
- Removed pandas dependency from vector store.

### Configuration
```json
{
  "qmd": {
    "use_qmd": true,
    "embedding_backend": "fastembed",
    "embedding_model": "all-MiniLM-L6-v2",
    "hybrid_alpha": 0.6
  }
}
```

### Dependencies
- `ghostclaw[qmd]` installs: `lancedb>=0.12.0`, `fastembed>=0.4.0`, `numpy>=1.24.0`.
- `sentence-transformers` backend requires separate torch install.

---

## [v0.2.0-alpha] - 2026-03-14

### Highlights
- **QMD backend** (experimental) — high-performance memory store using hybrid BM25 + vector search.
- **Fastembed** default for embeddings (CPU-friendly, no torch).
- **Configurable** embedding backends via `--embedding-backend`.
- **Performance** — BM25 search p50 ~1.15ms on 1000 reports.

### Technical Details
- BM25 via SQLite FTS5 with Porter stemming and custom `extract_searchable_text()`.
- LanceDB vector store with chunking (issues, ghosts, flags, AI paragraphs).
- Hybrid algorithm: parallel BM25+vector, MinMax normalization, configurable `alpha`.
- Fallback chain: hybrid → BM25 → legacy substring.

### Testing
- New tests: `test_vector_store.py`, `test_qmd_bm25.py`, `test_qmd_hybrid.py`.
- Total QMD tests: 20/20 passing.

### Known Limitations
- IVF-PQ index disabled (LanceDB API changes).
- No embedding cache (AI-Buff Phase 3 pending).
- Legacy migration not automated (Phase 5 pending).

---

## [v0.1.9] - 2026-03-12

### Added
- **MemoryStore** — SQLite-backed persistent analysis history.
- **MCP tools**: `ghostclaw_memory_search`, `ghostclaw_memory_get_run`, `ghostclaw_memory_list_runs`, `ghostclaw_memory_diff_runs`, `ghostclaw_knowledge_graph`.
- Performance: search ~5ms, knowledge graph ~7.5ms (1000 runs).

### CLI
- Full modular commander pattern.

---

**Note:** Earlier releases (v0.1.8 and before) are omitted from this unified changelog for brevity. See git history for full details.
