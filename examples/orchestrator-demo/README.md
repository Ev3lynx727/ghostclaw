# Orchestrator Demo

This example demonstrates how Ghostclaw's orchestrator plugin intelligently selects which analysis adapters to run, providing faster and more focused architectural reviews.

## What's Included

- `sample_project/` — a small Python codebase with intentional design issues
- `config.json` — sample Ghostclaw configuration enabling orchestrator mode
- `run.sh` — quick script to run the demo

## Quick Start

1. Ensure you have Ghostclaw and the orchestrator installed:

   ```bash
   pip install ghostclaw[orchestrator]
   ```

2. Make the demo script executable and run:

   ```bash
   chmod +x run.sh
   ./run.sh
   ```

3. Review the generated report in `.ghostclaw/storage/reports/`.

## Sample Configuration

```json
{
  "orchestrate": true,
  "orchestrator": {
    "use_llm": false,
    "max_plugins": 4,
    "vector_weight": 0.6,
    "heuristics_weight": 0.4,
    "verbose": true
  },
  "use_qmd": true
}
```

## Expected Behavior

When you run Ghostclaw with orchestrator enabled:

- Only a subset of adapters (typically 4-6) will run instead of all 12+.
- The log will show which plugins were selected and why (with `--orchestrate-verbose`).
- Analysis time should be noticeably faster than a full run.

## Comparing Runs

Try running the same repo with and without `--orchestrate` to compare:

```bash
# Full run (all plugins)
ghostclaw sample_project --use-qmd --json > full.json

# Orchestrated run
ghostclaw sample_project --orchestrate --use-qmd --json > orch.json
```

Compare the number of issues found and execution time. The orchestrated run should produce a more concise, prioritized set of findings.

## Troubleshooting

- If no plugins are selected, ensure `ghost-orchestrator` is installed and that QMD is enabled (`--use-qmd`) for vector similarity.
- Use `--orchestrate-verbose` to see detailed planning output.
- Check `ghostclaw plugins list` to verify available adapters.