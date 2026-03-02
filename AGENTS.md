# Ghostclaw Agent Guidelines

## Project Structure

This project follows a modular architecture. Please respect the separation of concerns:

- `skill/ghostclaw/core/`: Core analysis orchestration, metrics, and rule validation.
- `skill/ghostclaw/lib/`: Shared utilities (Caching, GitHub integration, Notifications).
- `skill/ghostclaw/stacks/`: Tech-stack specific analysis strategies (Python, Node.js, Go).
- `skill/ghostclaw/cli/`: Command-line interface logic.
- `scripts/`: Executable entry points and automation scripts.

## Important: No Duplicate Modules

**DO NOT create duplicate module directories inside `scripts/`.**

If you create new scripts in `scripts/`, use the following pattern to ensure they can import the modules from the skill directory:

```python
import sys
from pathlib import Path
# Skill directory is skill/ghostclaw
sys.path.append(str(Path(__file__).parent.parent / "skill" / "ghostclaw"))

from core.analyzer import CodebaseAnalyzer
# ...
```

## Coding Conventions

- **Encoding**: Always use `utf-8` when opening files.
- **Timestamps**: Use UTC ISO format with a 'Z' suffix: `datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + 'Z'`.
- **Error Handling**: Always call `raise_for_status()` on `requests` responses.
- **Hashing**: Use SHA256 for fingerprints, not MD5.

## Testing

- Run tests from the `skill/ghostclaw` directory using `python3 -m pytest`.
- Integration tests are located in `skill/ghostclaw/tests/integration/`.
- Unit tests are located in `skill/ghostclaw/tests/unit/`.
