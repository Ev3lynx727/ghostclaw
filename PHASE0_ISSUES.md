# Phase 0 – Foundational Fixes

This document outlines the critical issues identified during self-analysis of ghostclaw and the corresponding fixes implemented as Phase 0 before proceeding with Phase 1 integrations.

## Issues Fixed

### 1. File Exclusion Missing
**Problem:** `core/detector.find_files()` recursively included all files, leading to analysis of `.venv/`, `tests/`, `node_modules/`, and other non-production directories. This contaminated metrics (e.g., vibe score 25/100 due to thousands of third-party files).

**Fix:** Introduced `EXCLUDE_DIRS` set and `_should_exclude()` helper to filter out common non-source directories:
`.venv`, `venv`, `.env`, `__pycache__`, `.pytest_cache`, `.coverage`, `.git`, `.hg`, `.svn`, `node_modules`, `dist`, `build`, `target`, `vendor`, `.deps`, `tests`, `test`, `spec`, `specs`, `docs`, `doc`, `example`, `examples`, `scripts`.

**Files changed:**
- `core/detector.py`

**Tests added:**
- `tests/unit/test_detector.py::test_find_files_excludes_venv`
- `tests/unit/test_detector.py::test_find_files_excludes_tests`
- `tests/unit/test_detector.py::test_find_files_excludes_node_modules`

---

### 2. Stack Detection False Positive (OpenClaw Skill)
**Problem:** Presence of `package.json` (used for OpenClaw skill metadata) caused the project to be misidentified as a Node.js codebase, even when `pyproject.toml` existed. This resulted in analyzing the wrong file extensions and skipping Python analysis.

**Fix:** Modified `detect_stack()` to:
- Check Python indicators first.
- If `package.json` contains an `openclaw` key, return `'unknown'` to avoid Node detection and allow Python detection to take precedence.
- This preserves correct stack detection for hybrid projects.

**Files changed:**
- `core/detector.py`

**Tests added:**
- `tests/unit/test_detector.py::test_detect_python_over_node_with_openclaw_skill`
- `tests/unit/test_detector.py::test_detect_node_without_openclaw`

---

### 3. Instability Metric False Positives for Entry Points
**Problem:** Orchestrator modules (CLI, scripts) flagged as "highly unstable" because they import many modules (high efferent coupling). While correct numerically, these are architectural patterns, not issues.

**Fix:** Added `ENTRY_POINT_DIRS` constant (`{'cli', 'scripts', 'bin', '__main__'}`) to both `core/coupling.py` (Python) and `core/node_coupling.py` (Node). The instability check now skips modules whose dotted name contains any of these path components.

**Files changed:**
- `core/coupling.py`
- `core/node_coupling.py`

**Tests added:**
- `tests/unit/test_coupling_python.py::test_entry_point_not_flagged_as_unstable`
- `tests/unit/test_coupling_node.py::test_entry_point_not_flagged_as_unstable`

---

## Impact

These fixes ensure that:
- Ghostclaw analyzes only the intended source code, ignoring dependencies and tests.
- Stack detection works correctly even for OpenClaw skill repositories.
- Vibe scores reflect actual architectural health rather than noise from entry points or external files.

All existing tests continue to pass (51/51). The new tests provide regression protection for these core behaviors.
