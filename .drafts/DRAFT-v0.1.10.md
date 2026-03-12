# Draft: v0.1.10 — Ghost-Delta

**Status:** ✅ Implementation Complete (2026-03-12)  
**Branch:** `feature/v0.1.10-delta-context`  
**Milestone:** PR ready for `develop`

---

## Implementation Summary

All core features have been implemented and tested (193 passing tests). The delta-context feature is fully functional with CLI flags, diff extraction, base report discovery, and delta-specific AI prompt generation.

### Completed Features

- ✅ `git_utils` module with diff extraction (`get_git_diff`, `get_staged_diff`, etc.) and unit tests
- ✅ CLI flags `--delta` and `--base <ref>` wired through `GhostclawConfig` and `AnalyzeCommand`
- ✅ `CodebaseAnalyzer.analyze()` delta mode:
  - Calls `git_utils.get_git_diff()`
  - Filters file scanning to changed files only
  - Stores delta metadata in report
  - Loads base report from `.ghostclaw/reports/` (latest JSON)
- ✅ `ContextBuilder.build_delta_prompt()` generates structured delta prompt with `<base_context>`, `<diff>`, `<current_state>`
- ✅ `GhostAgent` fixed to only initialize `LLMClient` when `use_ai` (prevents errors in delta dry-runs)
- ✅ Report differentiation: `ARCHITECTURE-DELTA-<timestamp>.md` filename
- ✅ JSON report written alongside Markdown for future base loading
- ✅ Unit tests for `build_delta_prompt()` (with/without base report)
- ✅ Integration tests for delta mode (file filtering, base discovery)
- ✅ Manual E2E test verified on ghostclaw-clone repository

### Deferred to v0.1.11

- **JSON5 migration**: Not needed; staying with JSON for now
- **QMD backend integration**: Research phase; out of scope for v0.1.10
- **Commit hash matching**: Auto-discovery uses latest report; matching to `delta_base_ref` is future work

---

## Original Draft Content (For Reference)

## Features: Delta-Context with Diff-Centric

### 1. Diff Extraction (`git-centric`)

- New internal `git_utils` module to safely extract unified diffs.
- Automatic detection of staged/unstaged changes.
- Integration with `git diff` for comparing against specific branches or tags.

### 2. Delta Synthesis Architecture

- **Diff-Centric Prompts**: New XML-tagged prompt structure featuring `<diff>` (the changes) and `<base_context>` (the starting point).
- **History Retrieval**: Leverages `MemoryStore` (introduced in v0.1.9 drafts) to provide architectural "memory" for the delta analysis.
- **Delta-Sync Flow**: A streamlined execution path in `GhostAgent` that bypasses full metric scans.

### 3. JSON5 Transition

- Migrate configuration (`ghostclaw.json`) and internal storage formats to **JSON5**.
- This enables comments, trailing commas, and unquoted keys in project configurations, improving developer ergonomics.
- Update `GhostclawConfig` and `LocalCache` to support JSON5 parsing.

### 4. CLI Enhancements

- `--delta`: Flag to trigger delta-context analysis on current uncommitted changes.
- `--base <ref>`: Compare current state against a specific git reference (default: `HEAD~1`).
- Sharper output reports that highlight the *delta* in the Vibe Score and architectural health.

---

## Research: QMD Backend Integration

Based on recent research into [tobi/qmd](https://github.com/tobi/qmd), Ghostv0.1.8.1 will integrate QMD as a high-performance **Architectural Memory Backend**.

- **Hybrid Search**: Leverages BM25 and Vector search for high-fidelity retrieval of past architectural states.
- **Local-First**: Runs entirely on-device, preserving codebase privacy.
- **Agent-Optimized**: Provides structured context that directly feeds into the Ghost-Delta synthesis loop.
- **Schema**: Architecture reports will be stored as searchable `.qmd` artifacts, enabling cross-version trend analysis.

### Architectural Discovery: "Intent vs Reality"

A key technical breakthrough in v0.1.8.1 is the ability to bridge the gap between **documented design (Intent)** and **historical implementation (Reality)** using QMD's dual-collection capability.

- **Intent Collection**: Indexes the "Ground Truth" (root `.md` files and `/docs`). This provides the AI with the project's normative design principles.
- **Reality Collection**: Simultaneously indexes the `.ghostclaw/` reports. This provides the AI with the historical synthesis of how the code actually evolved.

#### Discovery Workflow:
1.  **Context Fusion**: During a `--delta` run, Ghostclaw performs a semantic lookup across *both* collections for modified components.
2.  **Drift Detection**: The AI synthesis unit specifically cross-references these views. If the code `diff` deviates from both the intended design and previous implementation history, it is flagged as **Architectural Drift**.

---

## Research: `.ghostclaw` Storage Architecture

We have validated the localized storage structure in the repository root. Ghostv0.1.8.1 will standardize the usage of the `.ghostclaw/` directory:

| Component | Path | Format | Role |
| :--- | :--- | :--- | :--- |
| **Cache** | `.ghostclaw/cache/` | `.json.gz` | High-speed retrieval of file fingerprints and metric results. |
| **Reports** | `.ghostclaw/reports/` | `.json` / `.md` | Historical analysis snapshots for human and agent review. |
| **Storage** | `.ghostclaw/storage/` | `ghostclaw.db` | Persistent SQLite database for trend analysis and cross-run persistence. |
| **Plugins** | `.ghostclaw/plugins/` | `*` | Isolation for external adapters and hook extensions. |

**Key Decision**: All JSON-based storage in `.ghostclaw/` (specifically reports and internal config) will migrate to **JSON5** to support metadata comments and human-friendly editing without breaking the automation pipeline.

---

## The "Dot Connection": How Delta-Context uses `.ghostclaw/`

The **Delta-Context** feature is not just a UI change; it’s a deep integration with the `.ghostclaw` storage layer:

1. **Base Context Retrieval**: When `--delta` is run, Ghostclaw reaches into `.ghostclaw/reports/` to find the "Ground Zero" state. It uses the latest JSON5 report as the foundation for the new analysis.
2. **Semantic Memory (QMD)**: QMD scans the `.ghostclaw/reports/` directory to build its vector index. This allows the Delta analysis to "remember" why certain architectural decisions were made in previous versions.
3. **Delta Recording**: The output of a delta run is stored back into `.ghostclaw/reports/` but tagged as a `DELTA` report, preserving the lineage of architectural changes.
4. **Configuration Synergy**: The move to **JSON5** allows developers to add comments in `.ghostclaw/ghostclaw.json5` that the AI can actually read and use as "Architectural Intent" during the synthesis.

## Roadmap & Schema

- **v0.1.9**: Harden the implementation, integrate with full MemoryStore knowledge graph, and cleanup legacy paths.
- **v0.1.10**: Implement core delta-context flow, `git_utils`, and CLI flags.

## Next Steps

1. [ ] Finalize `git_utils.py` implementation.
2. [ ] Update `ContextBuilder` with `build_delta_prompt`.
3. [ ] Orchestrate `run_delta` in `GhostAgent`.
4. [ ] Add `--delta` and `--base` flags to CLI dispatcher.
