# TODO: v0.2.0 — Unified Release (Delta + QMD + JSON5)

**Branch:** `feature/v0.1.10-delta-context` (will become v0.2.0)  
**Unified from:** v0.1.10 (Delta-Context) + v0.1.11 (QMD/JSON5/Commit-Matching)

---

## Phase A: QMD Backend Integration

**Goal:** Add optional QMD memory backend with hybrid search.

- [x] Add `qmd` to optional dependencies in `pyproject.toml` (`ghostclaw[qmd]`)
- [x] Create `QMDMemoryStore` class (new file: `src/ghostclaw/core/qmd_store.py`) implementing MemoryStore interface
- [x] Add `use_qmd` config flag and `--use-qmd` CLI flag
- [x] Create `QMDStorageAdapter` plugin (`src/ghostclaw/core/adapters/storage/qmd.py`)
- [x] Register QMDStorageAdapter in internal plugins
- [x] Auto-enable qmd plugin when `config.use_qmd=True` (in analyzer)
- [x] Update MCP server to use QMDMemoryStore when `GHOSTCLAW_USE_QMD` env var set
- [x] Unit tests:
  - [x] `test_qmd_store.py` (5 tests)
  - [x] `test_qmd_adapter.py` (4 tests)
- [x] Fix existing tests to work with new flags
- [x] All tests passing: **205 passed, 2 skipped**
- [ ] TODO: Performance benchmark (verify <5ms for 1000 runs) — optional, deferred to future optimization
- [ ] TODO: Dual-write migration script — not needed for v0.2.0 (QMD is opt-in and already dual-writes)

**Status:** ✅ Core implementation complete. QMD backend ready for use via `--use-qmd` or `use_qmd: true`.

---

## Phase B: Configuration & Storage Cleanup

**Goal:** JSON5 support + standardized `.ghostclaw/` layout.

### JSON5 Config
- [ ] Add `json5` to optional dependencies (`ghostclaw[config]`)
- [ ] Update `GhostclawConfig.load()`:
  - [ ] Try `json5.load()` if module available, fallback to `json.load()`
  - [ ] Preserve comments/trailing-commas when writing (for `init`)
- [ ] Update `ConfigService.init_project()`:
  - [ ] Write config as `.ghostclaw/config.json` (not `ghostclaw.json`)
  - [ ] Use JSON5 format (comments, trailing commas)
  - [ ] Include new fields: `use_qmd`, `delta_mode`, `delta_base_ref`, etc.
- [ ] Update `examples/global_config.json` to JSON5 with QMD options
- [ ] Backward compatibility: still read old `.ghostclaw/ghostclaw.json` with warning
- [ ] Tests:
  - [ ] Test loading JSON5 config with comments
  - [ ] Test fallback to plain JSON
  - [ ] Test `init` creates new `.ghostclaw/config.json` in JSON5

### Storage Reorganization
- [ ] Create storage layout:
  ```
  .ghostclaw/
  ├── cache/           # Analysis cache (.json.gz)
  ├── storage/
  │   ├── reports/    # Historical analysis (JSON + MD)
  │   ├── qmd/        # QMD databases (if used)
  │   └── ghostclaw.db # SQLite DB (legacy, will migrate)
  ├── plugins/        # External adapters
  └── config.json     # Local project config
  ```
- [ ] Update `ConfigService` paths:
  - [ ] Config: `.ghostclaw/config.json` (new) or legacy `ghostclaw.json`
  - [ ] Reports: `.ghostclaw/storage/reports/`
  - [ ] Cache: `.ghostclaw/cache/` (unchanged)
  - [ ] DB: `.ghostclaw/storage/ghostclaw.db`
- [ ] Auto-migration on first run:
  - [ ] If old `.ghostclaw/reports/` exists → move to `storage/reports/`
  - [ ] If old `.ghostclaw/ghostclaw.db` exists → move to `storage/`
  - [ ] Create backups before moving
- [ ] Update all code that reads/writes reports to use new paths
- [ ] Update `.gitignore` templates to include `.ghostclaw/storage/`
- [ ] Tests:
  - [ ] Test migration from old layout to new
  - [ ] Test new paths are created correctly by `init`

---

## Phase C: Delta Precision & UX Polish

**Goal:** Accurate commit matching + better user feedback.

### Commit-Hash Matching
- [ ] In `CodebaseAnalyzer.analyze()`:
  - [ ] Record current commit SHA: `git rev-parse HEAD`
  - [ ] Store in report: `metadata["vcs"] = {"commit": "...", "branch": "...", "timestamp": "..."}`
- [ ] Update `_find_base_report(repo_path, base_ref)`:
  - [ ] Resolve `base_ref` to SHA via `git rev-parse base_ref`
  - [ ] Scan `.ghostclaw/storage/reports/*.json` for matching `metadata.vcs.commit`
  - [ ] If exact match → use that report
  - [ ] Else → fallback to latest by date (with warning: "No report found for commit X, using latest")
  - [ ] Cache lookup: speed up with index file `reports_index.json` (commit → filename)
- [ ] Tests:
  - [ ] Test exact commit matching
  - [ ] Test fallback to latest with warning
  - [ ] Test index file generation/usage

### UX Improvements
- [ ] Add `--delta-summary` flag: print `git diff --stat` summary before analysis
- [ ] TerminalFormatter: color-coded delta output
  - [ ] Green for improvements (vibe_score increase, ghosts resolved)
  - [ ] Red for degradations (vibe_score decrease, new ghosts)
  - [ ] Yellow for neutral changes
- [ ] Add `ghostclaw delta` subcommand (alias for `analyze --delta`)
- [ ] Tests:
  - [ ] Test `--delta-summary` prints diff stats
  - [ ] Test color codes in terminal (or skip if CI)

---

## Phase D: Documentation, Versioning & Release

**Goal:** Final polish and publish v0.2.0.

- [ ] Update `README.md`:
  - [ ] QMD section (benefits, `--use-qmd` or `use_qmd: true`)
  - [ ] JSON5 config examples with comments
  - [ ] Storage structure explanation (`.ghostclaw/`)
  - [ ] Delta commit-hash matching usage (`--base <sha>`)
  - [ ] Migration guide from v0.1.x to v0.2.0
- [ ] Update `CHANGELOG.md`:
  - [ ] Add v0.2.0 section with all features grouped
  - [ ] Include breaking changes (storage path changes) with migration notes
- [ ] Update `docs/examples/delta-analysis.md`:
  - [ ] Add QMD + JSON5 examples
  - [ ] Show new storage layout
  - [ ] Demonstrate commit-hash matching in CI
- [ ] Bump version:
  - [ ] `pyproject.toml`: `version = "0.2.0"`
  - [ ] `src/ghostclaw/version.py`: `__version__ = "0.2.0"`
- [ ] Final test sweep:
  - [ ] Run full suite: `pytest -q` (target: 200+ tests)
  - [ ] Manual E2E: delta + QMD + JSON5 + new storage
  - [ ] Performance benchmark: QMD vs SQLite
- [ ] PR preparation:
  - [ ] Squash commits (if desired) or keep logical grouping
  - [ ] Write comprehensive PR description
  - [ ] Ensure CI passes (if configured)
  - [ ] Merge to `develop`
  - [ ] Tag `v0.2.0` and publish release
- [ ] Post-release:
  - [ ] Announce on Discord
  - [ ] Update docs website (if any)
  - [ ] Plan v0.3.0 roadmap

---

## Additional Tasks

- [ ] Add test coverage for storage migration (copy old → new)
- [ ] Add telemetry (opt-in) to gauge QMD adoption rate
- [ ] Consider deprecation warnings for old config paths in v0.3.0
- [ ] Update npm package version (if published)

---

## Success Criteria

- ✅ QMD search latency <5ms for 1000 runs (benchmarked)
- ✅ JSON5 configs work seamlessly; no user-reported parse errors
- ✅ Delta base matching 100% accurate (no more "latest" ambiguity)
- ✅ Storage migration smooth: 0 data loss incidents
- ✅ Test coverage: >200 tests passing
- ✅ No breaking changes without migration path

---

**Start Date:** 2026-03-12 (post v0.1.10 PR ready)  
**Target Release:** 2026-04 (tentative, 4-week sprint)
