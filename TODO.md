# Pre-release Checklist (v0.2.1-beta)

**Target:** 2026-03-18 (or upon manual QA sign-off)  
**Branch:** `release/v0.2.1-beta` (from `develop`)  
**Status:** Code complete, tests passing (36/36 QMD), docs updated

---

## Critical Pre-release Tasks

- [x] **Integration test:** Migrate a legacy QMD DB (pre-v0.2.0) with >1000 reports
  - ✅ Verified `EmbeddingBackfillManager` completes without errors
  - ✅ Processed 1200/1200 reports, 0 errors; all embeddings created
  - (Resumability: code path verified; manual interrupt test optional)
- [ ] **Benchmark:** Measure search latency with IVF-PQ enabled
  - Target: p50 <5ms on 1M+ chunk dataset
  - Compare recall vs brute-force
  - ⚠️ Script error during population — requires manual run in clean environment
- [ ] **CLI smoke test:** All commands functional
  - `ghostclaw analyze . --use-qmd`
  - `ghostclaw memory-stats --use-qmd`
  - `ghostclaw qmd migrate status`
- [ ] **MCP validation:** Ensure tools work with updated Pydantic models
  - `ghostclaw_analyze`, `ghostclaw_get_ghosts`, `ghostclaw_refactor_plan`
- [ ] **Formatter check:** Cognitive metrics display correctly in markdown/terminal/json
- [ ] **Config schema validation:** Test with sample project configs (JSON/JSON5)
- [x] **Docs:** Updated `README.md` to mention AI-Buff production readiness ✅
- [ ] **Git tag & release:** Create `v0.2.1-beta` tag, push, and draft GitHub release (use `.drafts/RELEASE-v0.2.1-beta.md`)
- [ ] **Community:** Announce release on Discord and relevant channels

---

## Post-release Ideas (v0.3.0 roadmap)

- [ ] Expose `QueryClassifier` weights in config for tuning
- [ ] Add classifier metrics to `ghostclaw memory-stats` output
- [ ] Implement `delete_report` cleanup in LanceDB (remove orphaned chunks)
- [ ] End-to-end integration tests with real codebases (multi-language)
- [ ] Performance tuning and monitoring dashboards
- [ ] Investigate ML-based alpha tuning (learning-to-rank from agent feedback)
- [ ] Add `prefetch_stats` to MCP tools for agent reasoning transparency
- [ ] Consider `vector_index` auto-enable after dataset crosses 10k vectors threshold

---

## Notes

- IVF-PQ is **disabled by default**; users must opt-in via config
- Migration auto-starts when `auto_migrate=true` (default) — monitor via `qmd migrate status`
- `max_chunks_per_report` defaults to `None` (unlimited); consider setting default to 3 in future
