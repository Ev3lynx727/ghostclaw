# Ghostclaw Troubleshooting Guide

If you encounter issues while installing, configuring, or running Ghostclaw, consult the common issues and resolutions below.

---

## 1. Installation & Import Errors

### `ModuleNotFoundError: No module named 'core.analyzer'`

**Symptom:** You try to run `ghostclaw` or a script and receive an error indicating `core` cannot be found.
**Cause:** This usually happens if you are running an outdated version of the codebase before the `src/ghostclaw/` restructuring, or if you haven't installed the package correctly.
**Solution:**

1. Ensure your repository is up to date.
2. If running from source, ensure you run `pip install -e .` from the repository root, OR use the wrapper scripts in `./scripts/` (e.g., `./scripts/ghostclaw.sh`).

### `Command 'ghostclaw' not found`

**Symptom:** You installed Ghostclaw via pip, but the CLI command is unavailable.
**Cause:** Your Python generic binaries directory (`~/.local/bin`) is not in your system `$PATH`.
**Solution:**
Add the Python user bin directory to your shell profile (e.g., `~/.bashrc` or `~/.zshrc`):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Or, as an alternative, run the module directly via python:

```bash
python3 -m ghostclaw.cli.ghostclaw
```

---

## 2. Advanced Engine Integration Issues

### Cannot Install `ai-codeindex` via `pipx`

**Symptom:** You try to run `pipx install ai-codeindex[all]` and get `Command 'pipx' not found`.
**Cause:** `pipx` is an isolated Python environment manager that is not installed by default on all systems.
**Solution:**
You have two choices:

1. Attempt a standard user-level pip install instead, which is usually sufficient for internal tools:

    ```bash
    pip install ai-codeindex[all]
    ```

2. Install `pipx` globally first via your OS package manager, then retry:

    ```bash
    sudo apt install pipx  # Debian/Ubuntu
    pipx install ai-codeindex[all]
    ```

### Missing PySCN or AI-CodeIndex Analytics

**Symptom:** You ran Ghostclaw with `--pyscn` or `--ai-codeindex` but see errors or missing insights in the JSON report.
**Cause:** The external binaries are not available in your `$PATH`. Ghostclaw's wrappers will gracefully fallback if the tools exit with a non-zero code or aren't found.
**Solution:** Ensure the tools are installed globally or in your current active virtual environment.

---

## 3. Automation and Webhook Issues

### PR Creation Fails / `HTTP 401 Unauthorized`

**Symptom:** The watcher script fails to open GitHub Pull Requests.
**Cause:** Missing or invalid GitHub API token.
**Solution:** Set the `GH_TOKEN` environment variable before running the script:

```bash
export GH_TOKEN="ghp_your_personal_access_token"
./scripts/watcher --repos-file repos.txt --create-pr
```

### No Data in Watcher Cache

**Symptom:** Running `./scripts/compare.sh` returns `Repositories: 0` or "No data."
**Cause:** The watcher script needs to successfully run on repositories *before* the compare script can detect historical data in the filesystem.
**Solution:** Ensure you've run `./scripts/watcher --repos-file repos.txt` successfully at least once. Data is cached at `~/.cache/ghostclaw/vibe_history.json`.
