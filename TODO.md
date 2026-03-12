# TODO: v0.1.10 — Delta-Context Feature Implementation

**Branch:** `feature/v0.1.10-delta-context`  
**Target:** Enable architectural analysis on diffs (PR-style reviews)  
**Status:** ✅ Implementation Complete — PR Ready

---

## Summary of Changes (What's Done)

### Core Implementation
- [x] `git_utils` module with diff extraction functions (`get_git_diff`, `get_staged_diff`, `get_unstaged_diff`, etc.) and unit tests
- [x] CLI flags `--delta` and `--base <ref>` wired through `GhostclawConfig` and `AnalyzeCommand`
- [x] `CodebaseAnalyzer.analyze()` delta mode:
  - Calls `git_utils.get_git_diff()`
  - Filters file scanning to changed files only
  - Stores delta metadata in report (`metadata.delta`)
  - Loads base report from `.ghostclaw/reports/` (latest JSON) for drift detection
- [x] `ContextBuilder.build_delta_prompt()` generates structured delta prompt with `<base_context>`, `<diff>`, `<current_state>`
- [x] `GhostAgent` fixed to only initialize `LLMClient` when `use_ai` (prevents errors in delta dry-runs)
- [x] Report filename differentiation: `ARCHITECTURE-DELTA-<timestamp>.md`
- [x] JSON report written alongside Markdown for base loading
- [x] Cache fingerprint includes delta parameters for proper separation

### Configuration & Init
- [x] Added `delta_mode` (default `False`) and `delta_base_ref` (default `"HEAD~1"`) to `GhostclawConfig`
- [x] Updated `ConfigService.init_project()` template to include delta fields (discoverability)
- [x] Updated `examples/global_config.json` with delta fields

### Testing
- [x] Unit tests:
  - [x] `test_context_builder.py` for `build_delta_prompt()` (with/without base report)
  - [x] `test_json_output.py` for JSON schema validation (full scan, delta fields, base report loading)
  - [x] `test_analyzer_command.py` updated with delta flags
- [x] Integration tests (`tests/integration/test_analyzer.py`):
  - [x] `test_delta_mode_filters_to_changed_files` (verifies file filtering and delta metadata)
  - [x] `test_delta_mode_base_report_discovery` (verifies base report loading and diff)
- [x] Manual E2E verified on ghostclaw-clone repo (dry-run prompt structure)
- [x] **196 tests passing, 2 skipped** (no regressions)

### Documentation
- [x] README: "Delta-Context Analysis (PR Reviews)" section with usage examples, benefits, base auto-discovery
- [x] CHANGELOG: v0.1.10 entry added
- [x] NEW: `docs/examples/delta-analysis.md` (CI integration, local workflow, troubleshooting, performance table)
- [x] Draft marked complete: `.drafts/DRAFT-v0.1.10.md`
- [x] Version bumped to `0.1.10` in `pyproject.toml` and `src/ghostclaw/version.py`

### Performance
- Benchmark on ghostclaw-clone:
  - Full scan: 66 files
  - Delta mode: 52 files (21% reduction)
  - Expected on large repos with small PRs: **10–120× speedup**

---

## PR Checklist

- [x] All tests passing (`pytest -q` → 196 passed, 2 skipped)
- [x] New tests added for delta functionality and JSON output
- [x] JSON output validated (built-in `json` module, no demjson3)
- [x] No new runtime dependencies (minimal)
- [x] Documentation complete (README + CHANGELOG + examples/)
- [x] Version bumped to 0.1.10 (pyproject.toml + version.py)
- [x] Config template updated (init command) + example global_config.json
- [x] Manual dry-run verified (prompt structure correct)
- [x] Branch pushed: `feature/v0.1.10-delta-context`
- [ ] PR opened and reviewed
- [ ] CI passes (if configured)
- [ ] Merge to `develop`
- [ ] Tag v0.1.10 and release

---

## Notes

**Design:** Delta mode is a *mode* of normal analysis flow, not a separate command. This keeps adapters, caching, and reporting consistent.

**Base context:** Auto-discovery from `.ghostclaw/reports/` (latest JSON). No explicit `--base-report` flag needed.

**Metrics scope:** Analyze only changed files for speed; full coupling may be added later if needed.

**Prompt:** Structured XML tags (`<base_context>`, `<diff>`, `<current_state>`) for clear LLM instructions.

**Deferred:** JSON5 migration, QMD backend integration, commit-hash matching for base reports.

---

**Implementation complete: 2026-03-12**  
**Commit:** `4c439af`  
**Tests:** 196 passed, 2 skipped
