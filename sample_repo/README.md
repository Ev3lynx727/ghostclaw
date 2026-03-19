# Sample Repository for Ghostclaw Testing

This is a minimal Python project containing various code quality issues. It's used to demonstrate Ghostclaw's analysis capabilities.

## Usage

Run Ghostclaw analysis on this repository:

```bash
# Standard analysis
ghostclaw analyze .

# With QMD vector memory
ghostclaw analyze . --use-qmd
```

## What's Inside

- `sample.py` — A Python module with intentional issues:
  - Function with too many parameters (God Function smell)
  - Deeply nested conditionals (high cyclomatic complexity)
  - God Class with multiple responsibilities
  - Unused imports and variables
  - Magic numbers
  - Duplicate code blocks
  - Long functions

These issues will be detected by Ghostclaw's architectural and complexity analyzers.

## Expected Findings

- **High Complexity:** `complex_nested_function` and `very_long_function_with_many_parameters`
- **God Class:** `GodClass` (violates Single Responsibility)
- **Code Smells:** Unused variables, magic numbers, duplicate code
- **Architectural Ghosts:** Violations of SRP, high coupling, low cohesion

Perfect for quick testing and development!
