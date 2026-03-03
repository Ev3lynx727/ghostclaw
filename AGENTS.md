# Ghostclaw Agent Guidelines

## Project Structure

This project follows a modular architecture. Please respect the separation of concerns:

- `core/`: Core analysis orchestration, metrics, and rule validation.
- `ghostclaw_mcp/`: Model Context Protocol (MCP) server implementation.
- `lib/`: Shared utilities (Caching, GitHub integration, Notifications).
- `stacks/`: Tech-stack specific analysis strategies (Python, Node.js, Go).
- `cli/`: Command-line interface logic.
- `scripts/`: Executable entry points, automation, and deployment scripts.

## Optional Integration Engines

Ghostclaw supports enhanced architectural analysis via two optional engines. These are natively integrated but must be explicitly toggled via CLI flags or installed in the host environment:

- **PySCN (`--pyscn`)**: Deep clone detection and dead code analysis.
- **AI-CodeIndex (`--ai-codeindex`)**: AST-based coupling graph and deep inheritance hierarchy detection.

## Important: No Duplicate Modules

**DO NOT create duplicate module directories inside `scripts/`.**

Historically, there were duplicates of `core/`, `lib/`, and `stacks/` inside the `scripts/` directory. These have been removed to maintain a single source of truth.

If you create new scripts in `scripts/`, use the following pattern to ensure they can import the root-level modules:

```python
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.analyzer import CodebaseAnalyzer
# ...
```

## Coding Conventions

- **Encoding**: Always use `utf-8` when opening files.
- **Timestamps**: Use UTC ISO format with a 'Z' suffix: `datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + 'Z'`.
- **Error Handling**: Always call `raise_for_status()` on `requests` responses.
- **Hashing**: Use SHA256 for fingerprints, not MD5.

## Testing

- Run tests from the root using `python3 -m pytest`.
- Integration tests are located in `tests/integration/`.
- Unit tests are located in `tests/unit/`.
