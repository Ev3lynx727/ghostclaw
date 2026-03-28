# Orchestrator (Adaptive Routing)

Ghostclaw includes an **orchestrator** plugin that intelligently selects which analysis adapters to run based on the repository's characteristics and historical performance. This reduces analysis time by 30-60% and produces cleaner, more relevant reports.

## Installation

The orchestrator is an optional component. Install it via:

```bash
# Install with ghostclaw core (includes ghost-orchestrator as optional dependency)
pip install "ghostclaw[orchestrator]"

# Or install the orchestrator plugin separately
pip install ghost-orchestrator
```

## Enabling

Enable orchestrator mode via CLI flag or config:

```bash
# CLI
ghostclaw /path/to/repo --orchestrate

# Config file (~/.ghostclaw/ghostclaw.json or repo-local)
{
  "orchestrate": true
}
```

## LLM-Based Planning (Optional)

Orchestrator can use an LLM to generate adaptive analysis plans. To enable:

```bash
# Set AI provider and API key (OpenRouter recommended)
export OPENROUTER_API_KEY="your-key"
ghostclaw /path/to/repo --orchestrate --orchestrate-llm --ai-provider openrouter --ai-model anthropic/claude-3.5-sonnet

# Or via config
{
  "orchestrate": true,
  "orchestrator": {
    "use_llm": true,
    "llm_model": "openrouter/anthropic/claude-3.5-sonnet"
  }
}
```

**Note:** LLM planning requires network access and may incur costs. Use `--dry-run` to preview prompts.

## CLI Flags (v0.2.4+)

- `--orchestrate-verbose` — Print detailed planning information (selected plugins, weights, reasoning).
- `--orchestrate-cache-dir <path>` — Specify a custom directory for plan caching (default: `.ghostclaw/orchestrator_cache/`).
- `--orchestrate-history-len <N>` — Number of past analysis runs to consider for vector similarity (default: 20).
- `--orchestrate-no-cache` — Disable plan caching (useful for debugging or one-off runs).

Example:

```bash
ghostclaw . --orchestrate --orchestrate-verbose --orchestrate-cache-dir /tmp/orch-cache --orchestrate-history-len 50
```

## Configuration Reference

```json5
{
  // Top-level switch
  "orchestrate": true,

  // Nested orchestrator configuration
  "orchestrator": {
    // LLM Planning
    "use_llm": false,              // Enable LLM-based plan generation (default: false)
    "llm_model": "openrouter/anthropic/claude-3-sonnet",
    "llm_temperature": 0.7,
    "max_tokens": 4096,

    // Routing weights (sum to ~1.0, auto-normalized)
    "vector_weight": 0.7,          // Weight for QMD vector similarity
    "heuristics_weight": 0.3,      // Weight for rule-based heuristics

    // Limits
    "max_plugins": 8,              // Maximum plugins to execute
    "max_concurrent_plugins": 4,   // Concurrency limit

    // History & Caching
    "plugin_history_lookback": 50, // How many past runs to consider (v0.2.4: override via --orchestrate-history-len)
    "enable_plan_cache": true,     // Enable/disable plan caching (v0.2.4: override via --orchestrate-no-cache)
    "plan_cache_ttl_hours": 24,
    "plan_cache_file": null,       // Auto-determined; override with v0.2.4 --orchestrate-cache-dir

    // Observability (v0.2.4)
    "verbose": false,              // Print detailed plan info (--orchestrate-verbose)

    // Advanced
    "plan_only": false,            // Generate plan but do not execute (debug)
    "report_plan_details": true,   // Include plan details in final report
    "concurrency_limit": null      // Override global concurrency_limit (if set)
  }
}
```

## How It Works

1. **Before analysis**, orchestrator examines the repository (stack, file types, metrics).
2. **Vector similarity** — If QMD is enabled, it searches historical runs for similar repos to learn which plugins were most effective.
3. **Heuristics** — Applies rule-based filters (e.g., skip Python-specific plugins in a Go repo).
4. **LLM planning (optional)** — Sends repository context to an LLM to generate a custom plugin execution plan.
5. **Execution** — Only the selected plugins run; others are skipped entirely.
6. **Caching** — Plans are cached (by repository fingerprint) to avoid re-planning on identical codebases.

## Requirements

- **QMD backend** (`--use-qmd`) is **highly recommended** for accurate vector similarity. Without QMD, orchestrator falls back to heuristics only.
- **Orchestrator plugin** must be installed (`ghost-orchestrator` from PyPI). Ghostclaw will auto-discover it via entry points when `orchestrate=true`.

## Troubleshooting

### Orchestrator not activating despite `--orchestrate`

- Ensure `ghost-orchestrator` is installed: `pip list | grep ghost-orchestrator`
- Check that `orchestrator.enabled` is `true` (the `--orchestrate` flag sets it automatically).
- Verify the plugin appears in `ghostclaw plugins list`.

### LLM planning fails with authentication errors

- Set the appropriate API key environment variable for your provider (e.g., `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`).
- Confirm the model identifier is correct and your account has access (e.g., `openrouter/anthropic/claude-3.5-sonnet`).
- Use `--dry-run` to see the generated prompt and ensure network connectivity.

### Plan cache not being used

- Verify cache directory exists and is writable (`--orchestrate-cache-dir`).
- Check that `enable_plan_cache` is `true`.
- The cache key includes repository fingerprint + orchestrator config; any change invalidates the cache.

### Vector similarity seems off

- Ensure QMD is enabled (`--use-qmd`) and that you have historical runs in `.ghostclaw/storage/`.
- Increase `plugin_history_lookback` to consider more past runs (default 50).
- The vector weight (`vector_weight`) and heuristics weight (`heuristics_weight`) must sum to ~1.0. Invalid values cause validation errors.

## Performance Tips

- Combine `--orchestrate` with `--use-qmd` for the best adaptive routing.
- Tune `max_plugins` to balance thoroughness vs. speed (typical 4-8).
- Use `--orchestrate-verbose` to see which plugins were selected and why; adjust weights accordingly.
- Cache plans between runs by leaving `enable_plan_cache` on; it saves LLM costs and time.

## Future Roadmap

- Dynamic plugin weight tuning based on long-term outcome feedback.
- Per-repo orchestrator profiles stored in QMD.
- More sophisticated heuristics (dependency graph, complexity metrics).