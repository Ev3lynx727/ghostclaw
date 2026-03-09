# Internal API Migration Guide

This guide details the internal API changes made during the transition from the monolithic CLI (`v0.1.7`) to the modular Commander CLI (`v0.1.8`).

## Overview

The `ghostclaw.cli.ghostclaw` module has been heavily refactored. The monolithic `main()` function is now a thin dispatcher that routes commands to modular classes. This has internal implications for any external integrations, scripts, or plugins that directly imported functions from `ghostclaw.cli.ghostclaw`.

**The public CLI interface (e.g., running `ghostclaw analyze`) remains 100% backward compatible.**

## Breaking Changes (Internal)

Direct imports of the following functions from `ghostclaw.cli.ghostclaw` are **deprecated** and will be removed in `v0.1.9`. You must update your internal code to use the new Services and Formatters.

### 1. Generating Markdown Reports

**Old:**
```python
from ghostclaw.cli.ghostclaw import generate_markdown_report

md_content = generate_markdown_report(report)
```

**New:**
```python
from ghostclaw.cli.formatters.markdown import MarkdownFormatter

md_content = MarkdownFormatter().format(report)
```

### 2. Printing Terminal Reports

**Old:**
```python
from ghostclaw.cli.ghostclaw import print_report

print_report(report)
```

**New:**
```python
from ghostclaw.cli.formatters.terminal import TerminalFormatter

TerminalFormatter().print_to_terminal(report)
```

### 3. Creating GitHub PRs

**Old:**
```python
from ghostclaw.cli.ghostclaw import create_github_pr

create_github_pr(repo_path, report_file, title, body)
```

**New:**
```python
from ghostclaw.cli.services.pr_service import PRService
import asyncio

pr_service = PRService(repo_path)
asyncio.run(pr_service.create_pr(report_file, title, body))
```

### 4. Updating Ghostclaw

**Old:**
```python
from ghostclaw.cli.ghostclaw import update_ghostclaw

update_ghostclaw()
```

**New:**
```python
from ghostclaw.cli.commands.update import UpdateCommand
import argparse
import asyncio

cmd = UpdateCommand()
asyncio.run(cmd.execute(argparse.Namespace()))
```

### 5. Detecting GitHub Remotes

**Old:**
```python
from ghostclaw.cli.ghostclaw import detect_github_remote

remote_url = detect_github_remote(repo_path)
```

**New:**
```python
# Function remains available in the global scope of ghostclaw.py, but is currently internal to AnalyzeCommand's logic.
from ghostclaw.cli.ghostclaw import detect_github_remote
```

## Modular Commander Architecture

The new architecture splits CLI logic into:

1.  **Command Framework**: `src/ghostclaw/cli/commander/base.py` & `registry.py`
2.  **Commands**: Specific logic for each command in `src/ghostclaw/cli/commands/`
3.  **Services**: Reusable business logic separated from the CLI interface in `src/ghostclaw/cli/services/`
4.  **Formatters**: Output generation in `src/ghostclaw/cli/formatters/`

## Dual-Mode Dispatcher

During the transition, `ghostclaw.py` will automatically fall back to legacy operations (`legacy_main()`) if an unregistered command is encountered. This ensures complete backward compatibility for any edge cases while we finalize the migration in `v0.1.9`.
