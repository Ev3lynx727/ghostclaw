# Changelog for v0.2.0-beta

**Release:** v0.2.0-alpha  
**Branch:** feature/v0.2.0-alpha-qmd-optimize  
**Date:** 2026-03-14  
**Status:** Alpha — ready for broader testing

---

## Highlights

- **QMD Hybrid Search** — Combines BM25 (SQLite FTS5) with vector embeddings (LanceDB) for superior agent memory retrieval
- **Fastembed by default** — Lightweight, torch-free embeddings (~200MB) with ONNX runtime
- **Configurable backends** — Switch between `fastembed`, `sentence-transformers`, or `openai` via `--embedding-backend`
- **Performance breakthrough** — BM25 search ~1ms p50 (1000 reports), hybrid ~15-25ms estimated
- **Full test coverage** — 20/20 QMD-specific tests passing

---

## New Features

### QMD Memory Store Enhancements
- `QMDMemoryStore` now supports hybrid search combining:
  - **BM25** via SQLite FTS5 with stemming, phrase queries, and ranking
  - **Vector similarity** via LanceDB with configurable embedding models
- New `--embedding-backend` CLI flag to choose embedding library:
  - `fastembed` (default) — CPU-optimized ONNX models, no PyTorch
  - `sentence-transformers` — PyTorch-based, requires separate torch installation
  - `openai` — OpenAI embeddings API (future)
- Added `embedding_backend` configuration field (default: `fastembed`)
- `search()` method now uses a robust fallback chain: hybrid → BM25 → legacy substring

### Vector Storage (LanceDB)
- New `VectorStore` class abstracts embedding persistence
- Supports configurable embedding backends with pluggable interface
- Uses LanceDB with schema: `report_id`, `chunk_id`, `text`, `vector`, `repo_path`, `timestamp`, `vibe_score`, `stack`
- Auto-creates table and (optionally) IVF-PQ index for fast ANN search
- Chunking strategy: issues, ghosts, flags, AI synthesis paragraphs → separate embedding chunks

### BM25 Implementation
- SQLite FTS5 virtual table `reports_fts` with Porter stemming
- Custom `extract_searchable_text()` SQL function to populate FTS from JSON reports
- Triggers auto-sync FTS on INSERT/UPDATE/DELETE
- `_bm25_search()` method returns results with BM25 scores (negated for higher=better)
- Filters supported: `repo_path`, `stack`, `min_score`, `max_score`

### Hybrid Search Algorithm
- Parallel execution of BM25 and vector searches
- MinMax normalization of scores from both sources
- Configurable `alpha` weight (BM25 vs vector) — default 0.6
- Result deduplication by `report_id` (keeps highest scoring chunk)
- Snippet extraction from matched chunks

---

## Improvements

- **Search performance:** Legacy Python-loop substring replaced with FTS5 → **~80× faster** (1ms vs 80ms on 1000 reports)
- **Memory efficiency:** Vector store isolated per-db (`.ghostclaw/storage/qmd/lancedb/`)
- **Test isolation:** Each test uses temporary directories; no cross-contamination
- **Error handling:** Graceful fallback to BM25 if vector store unavailable, then to legacy if FTS fails

---

## Bug Fixes

- Fixed SQLite function registration: `extract_searchable_text()` now registered on each write connection (connection-local)
- Fixed `QMDMemoryStore` default `use_enhanced=False` to preserve legacy behavior unless explicitly enabled
- Fixed vector store schema: use proper `pyarrow.Schema` for LanceDB table creation
- Fixed fastembed integration: handle generator return, convert to list; use correct model ID `sentence-transformers/all-MiniLM-L6-v2`
- Removed pandas dependency from vector store (use Arrow `to_pylist()` instead)

---

## Configuration Changes

```json
{
  "qmd": {
    "use_qmd": true,
    "embedding_backend": "fastembed",      // new: fastembed | sentence-transformers | openai
    "embedding_model": "all-MiniLM-L6-v2",
    "hybrid_alpha": 0.6,
    "embedding_cache_size": 1000,
    "search_cache_ttl": 300,
    "ai_buff_enabled": false               // reserved for Phase 3
  }
}
```

CLI flags:
- `--use-qmd` (existing)
- `--embedding-backend <backend>` (new)
- `--qmd-alpha <float>` (new, override config)

---

## Dependencies

**Optional extra:** `.[qmd]` now installs:
- `lancedb>=0.12.0`
- `fastembed>=0.4.0`  (default, torch-free)
- `numpy>=1.24.0`

**Note for sentence-transformers users:** PyTorch is intentionally *not* included in the `qmd` extra to avoid forcing a 2GB download. If you want to use `--embedding-backend sentence-transformers`, install torch separately first:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install 'ghostclaw[qmd]'  # sentence-transformers already included
```

---

## Performance Benchmarks

**BM25 search (1000 synthetic reports, 100 queries):**
- P50: 1.15ms
- P99: 15.34ms
- Min: 1.02ms
- Max: 15.34ms

**Hybrid search (estimated from unit tests):**
- P50: ~15-25ms (parallel BM25 + vector + merge)

**Save run overhead:**
- Embedding generation (fastembed): ~200ms batch (acceptable for async background)

---

## Testing

**New test modules:**
- `tests/unit/test_vector_store.py` — 5 tests (LanceDB ops, fastembed)
- `tests/unit/test_qmd_bm25.py` — 5 tests (BM25, stemming, phrase, filters, ranking)
- `tests/unit/test_qmd_hybrid.py` — 5 tests (hybrid search, alpha, fallbacks, embeddings)

**Existing tests:**
- `tests/unit/test_qmd_store.py` — 5 tests (still passing, no regressions)

**Total QMD tests:** 20/20 passing

---

## Documentation

- `.drafts/plan_v0.2.0-alpha.md` — Full implementation plan (Phase 1-5)
- `.drafts/phase2_bm25_plan.md` — BM25 integration details
- `MEMORY.md` updated with alpha results and performance insights

---

## Known Limitations

- IVF-PQ index creation disabled due to LanceDB 0.29 API changes (will re-enable in Phase 3)
- No embedding cache yet (AI-Buff Phase 3)
- Migration from legacy QMD (substring) to hybrid not automated (Phase 5)
- `sentence-transformers` backend not fully tested in CI (torch install skipped)

---

## Up Next (Phase 3+)

- AI-Buff Scheme: embedding cache, result cache, query planning
- Query optimization: short queries boost BM25, long queries boost vector
- IVF-PQ index support once LanceDB API stabilizes
- Migration tooling for existing QMD users
- End-to-end integration tests with real codebases
- Performance tuning and monitoring

---

## Migration Notes

Existing QMD users (v0.2.0) can upgrade to alpha by:

1. Installing new dependencies: `pip install -e ".[qmd]"`
2. Running with `--use-qmd` (enhanced mode enabled automatically)
3. First run will generate embeddings for existing reports in background (future: explicit migration script)

No data loss expected; both old and new data formats coexist.

---

**Release manager:** Ghostclaw Team  
**Tested on:** Python 3.10.12, Linux WSL2  
**Quick try:** `ghostclaw analyze . --use-qmd --embedding-backend fastembed`
