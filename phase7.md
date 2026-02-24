# Phase 7: Plugin System Strategy

**Version:** 0.2.0 (with integration examples)  
**Status:** Proposed  
**Author:** Ghostclaw (self-reflection)  
**Last Updated:** 2026-02-23

---

## 📜 Table of Contents

1. [Vision](#vision)
2. [Architecture Overview](#architecture-overview)
3. [Integration Mechanism](#integration-mechanism) ← NEW
4. [Plugin Types & APIs](#plugin-types--apis)
5. [Q&A: Built-in vs Plugin?](#qa-built-in-vs-plugin) ← NEW
6. [Security Model](#security-model)
7. [Plugin Distribution](#plugin-distribution)
8. [Example: `ghostclaw-pyguard` Integration](#example-ghostclaw-pyguard-integration)
9. [Implementation Roadmap](#implementation-roadmap)
10. [Testing Strategy](#testing-strategy)
11. [Configuration Schema](#configuration-schema)
12. [Open Questions](#open-questions)
13. [Success Metrics](#success-metrics)
14. [Next Steps](#next-steps)

---

## 🎯 Vision

Enable **third-party extensions** without modifying ghostclaw core. Users can:
- Add new tech stack analyzers (Rust, Java, Kotlin, Swift, PHP, etc.)
- Define organization-specific rules (security, compliance, style)
- Hook into analysis lifecycle (notifications, custom PR templates)
- Output custom report formats (HTML, dashboards, Slack cards)

**Key principle:** Ghostclaw remains lightweight core; advanced features opt-in via plugins.

---

## 🏗️ Architecture Overview

### Three Plugin Categories

| Category | Purpose | Example |
|----------|---------|---------|
| **Stack Plugins** | Teach ghostclaw how to analyze a new language/framework | `ghostclaw-rust`, `ghostclaw-java` |
| **Rule Plugins** | Add custom quality gates (security, compliance, org conventions) | `ghostclaw-security`, `ghostclaw-internal` |
| **Hook Plugins** | React to events (notify, enrich PRs, update tickets) | `ghostclaw-slack`, `ghostclaw-jira` |

### Discovery Mechanisms

**1. Entry Points (setuptools)** — For packaged plugins (preferred distribution):

```python
# In plugin's pyproject.toml
[project.entry-points."ghostclaw.stacks"]
rust = "ghostclaw_rust.analyzer:RustAnalyzer"

[project.entry-points."ghostclaw.rules"]
security = "ghostclaw_security.rules:load_rules"

[project.entry-points."ghostclaw.hooks"]
on_pr_created = "ghostclaw_slack.hooks:pr_notification"
```

**2. Plugin Directory (user space)** — For local .py/.yaml files:

```
~/.ghostclaw/plugins/
├── stacks/
│   └── my_java_analyzer.py    # StackAnalyzer subclass (opt-in)
├── rules/
│   └── company_rules.yaml     # Additional rule definitions
└── hooks.py                   # Hook functions (opt-in)
```

**3. Configuration (enable/disable/configure)**

```yaml
# ~/.ghostclaw/config.yaml
plugins:
  stacks:
    - "ghostclaw-rust"          # pip-installed (entry point)
    - "~/.ghostclaw/plugins/stacks/my_java_analyzer.py"  # local file
  rules:
    - "ghostclaw-security"
    - "~/.ghostclaw/plugins/rules/company_rules.yaml"
  hooks:
    - "ghostclaw-slack.on_pr_created"
    - "~/.ghostclaw/plugins/hooks.py:on_analysis_complete"
```

---

## 🔧 Integration Mechanism

### How Plugins Hook Into Ghostclaw

The plugin system operates at **three integration points**:

#### 1. **Stack Analyzer Registry**

Core maintains a global registry of `StackAnalyzer` instances. By default, it contains Node, Python, Go.

```python
# ghostclaw/stacks/__init__.py (current)
STACK_REGISTRY = {
    'node': NodeAnalyzer(),
    'python': PythonAnalyzer(),
    'go': GoAnalyzer()
}
```

**Plugin integration:** Load additional analyzers and merge into registry.

```python
# After plugin loader runs
STACK_REGISTRY.update({
    'rust': RustAnalyzer(),           # from ghostclaw-rust
    'java': JavaAnalyzer(),           # from ghostclaw-java
    'pyguard': PyGuardAnalyzer()      # from ghostclaw-pyguard
})
```

**Detection flow:**
1. `detect_stack()` returns 'python' (from build files)
2. Core looks up `STACK_REGISTRY['python']` → gets PythonAnalyzer
3. If user enabled `ghostclaw-pyguard`, registry also contains 'pyguard'
4. **Both analyzers run!** (multiple plugins can handle same stack)
5. Their issues/ghosts are merged into final report

**Key insight:** Stack plugins are **cumulative**, not exclusive. You can run ghostclaw's coupling analysis AND pyguard's type checking on the same Python repo.

---

#### 2. **Rule Validator Extension**

`core/validator.py` loads rules from multiple sources and applies them all.

```python
class RuleValidator:
    def __init__(self):
        # Load core rules from references/stack-patterns.yaml
        self.core_rules = load_yaml('references/stack-patterns.yaml')

        # Load plugin rules from config-specified paths
        self.plugin_rules = []
        for rule_source in config.get('plugins', {}).get('rules', []):
            if rule_source.endswith('.yaml'):
                self.plugin_rules.append(load_yaml(rule_source))
            # Could also load from Python functions

    def validate(self, stack, report):
        all_rules = self.core_rules[stack]['rules'] + \
                    sum([r[stack]['rules'] for r in self.plugin_rules], [])
        # Apply all rules and collect issues
```

**Result:** Issues from core YAML + plugin YAMLs are merged.

---

#### 3. **Hook Invocation**

Core defines hook points. Plugins register functions to be called.

```python
# ghostclaw/core/hooks.py
HOOKS = {
    'on_analysis_start': [],
    'on_analysis_complete': [],
    'on_pr_created': [],
    'on_issue_found': []
}

def trigger(hook_name, *args, **kwargs):
    for func in HOOKS.get(hook_name, []):
        try:
            func(*args, **kwargs)
        except Exception as e:
            log.warning(f"Hook {hook_name} failed: {e}")
```

Plugins register during loader:

```python
# In plugin loader
from ghostclaw.core import hooks
hooks.HOOKS['on_analysis_complete'].append(my_completion_handler)
```

Usage in `CodebaseAnalyzer.analyze()`:

```python
def analyze(self, root):
    hooks.trigger('on_analysis_start', root, config)
    # ... do analysis ...
    hooks.trigger('on_analysis_complete', report, cache)
    return report
```

---

### Plugin Loader Flow

```python
# PluginLoader (to be implemented)
class PluginLoader:
    def load_all(self, config):
        # 1. Load from config.yaml 'plugins' section
        for plugin_spec in config['plugins']['stacks']:
            analyzer = self._load_stack_plugin(plugin_spec)
            STACK_REGISTRY[analyzer.get_name()] = analyzer

        for plugin_spec in config['plugins']['hooks']:
            hook_func = self._load_hook(plugin_spec)
            HOOKS[hook_namespace].append(hook_func)

        for rule_source in config['plugins']['rules']:
            validator.load_rules(rule_source)
```

**Loading sources:**
- **Entry point:** `importlib.metadata.entry_points(group='ghostclaw.stacks')`
- **File path:** `importlib.util.module_from_spec()` after reading .py file
- **YAML rules:** `yaml.safe_load()` and merge into validator

---

### Example: How `ghostclaw-pyguard` Integrates

1. **User installs:** `pip install ghostclaw-pyguard`
2. **Plugin registers:** Entry point `ghostclaw.stacks` → `PyGuardAnalyzer` class
3. **User enables:** Add to `~/.ghostclaw/config.yaml`:
   ```yaml
   plugins:
     stacks:
       - "ghostclaw-pyguard"
   ```
4. **Loader runs:** Discovers entry point, imports `PyGuardAnalyzer`, adds to `STACK_REGISTRY['pyguard']`
5. **Analysis:** When Python repo analyzed:
   - `detect_stack()` returns 'python'
   - Core gets `STACK_REGISTRY['python']` → runs `PythonAnalyzer` (coupling)
   - ** ALSO ** gets `STACK_REGISTRY['pyguard']` → runs `PyGuardAnalyzer`
   - Merges issues: `report['issues'] = pyanalyzer_issues + pyguard_issues`
6. **Output:** Single report with both coupling and type-checking issues.

---

## 🔌 Plugin Types & APIs

### 1. Stack Plugins

**Goal:** Add support for a new technology stack.

**Interface:**
```python
# Abstract base (from ghostclaw.stacks.base)
class StackAnalyzer(ABC):
    @abstractmethod
    def get_extensions(self) -> List[str]:
        """File extensions this stack handles."""

    @abstractmethod
    def get_large_file_threshold(self) -> int:
        """Line count threshold for 'large files'."""

    @abstractmethod
    def analyze(self, root: str, files: List[str], metrics: Dict) -> Dict:
        """
        Perform analysis. Must return dict with:
        - issues: List[str]
        - architectural_ghosts: List[str]
        - red_flags: List[str]
        - coupling_metrics: Dict (optional, if AST analysis available)
        """
```

**Example: Rust Plugin (`ghostclaw-rust`)**

```python
from ghostclaw.stacks.base import StackAnalyzer

class RustAnalyzer(StackAnalyzer):
    def get_extensions(self):
        return ['.rs']

    def get_large_file_threshold(self):
        return 800  # Rust files can be larger

    def analyze(self, root, files, metrics):
        issues = []
        ghosts = []
        # Use cargo to get module structure
        # Analyze pub/private boundaries
        # Detect async/sync mismatches
        # ... (plugin-specific logic)
        return {
            "issues": issues,
            "architectural_ghosts": ghosts,
            "red_flags": [],
            "coupling_metrics": {}
        }
```

### 2. Rule Plugins

**Goal:** Add new rule types to the validator engine.

**Approach A: YAML-only (safe, no code execution)**

Additional rule types can be added to core validator:

```yaml
# ~/.ghostclaw/plugins/rules/custom.yaml
rules:
  - id: no_todos_in_production
    type: content_search
    pattern: "TODO|FIXME|HACK"
    paths: ["src/", "lib/"]
    exclude: ["test"]  # Allow in tests
    message: "Found {match} in production code"

  - id: max_function_lines
    type: function_metric
    metric: lines
    threshold: 50
    message: "Function {func} is {lines} lines (>50)"

  - id: forbid_import
    type: import_pattern
    pattern: "from.*requests.*import.*post"  # forbid raw HTTP POST
    message: "Use secure HTTP client wrapper"
```

**Rule Types (extensible):**
- `metric` (existing) — average_lines, large_file_count
- `metric_coupling` (existing) — instability, afferent, efferent
- `content_search` — regex in file contents
- `function_metric` — analyze individual function complexity (requires AST)
- `import_pattern` — ban specific import patterns
- `directory_structure` — enforce/forbid directories

**Approach B: Python-custom rules (opt-in, powerful)**

```python
# In plugin file enabled in config
def custom_security_rule(report):
    """Custom Python function to add issues."""
    # Can inspect full report, read external data, etc.
    if "password" in report.get('stack', ''):
        return [{
            "id": "insecure_stack",
            "message": "Don't use password stack",
            "severity": "critical"
        }]
    return []

# Config tells loader to import and call this
plugins:
  rules:
    - module: "~/.ghostclaw/plugins/security_rules.py"
      function: "custom_security_rule"
```

### 3. Hook Plugins

**Goal:** React to events without forking ghostclaw.

**Hook Points:**
- `on_analysis_start(repo_path, config)` — before analysis begins
- `on_analysis_complete(report, cache)` — after analysis, before output
- `on_issue_found(issue, report)` — for each issue (filter/transform)
- `on_pr_created(repo, pr_url, report)` — after PR opened
- `on_watcher_cycle_start()`, `on_watcher_cycle_complete(repos_processed)`

**Example: Slack Notification Hook**

```python
# ~/.ghostclaw/plugins/hooks.py
import os
import requests

def on_analysis_complete(report, cache):
    if report['vibe_score'] < 60:
        webhook = os.getenv('SLACK_WEBHOOK')
        if webhook:
            requests.post(webhook, json={
                "text": f"🚨 Repository {report['repo']} vibe dropped to {report['vibe_score']}/100"
            })
```

**Example: Jira Ticket Creation Hook**

```python
def on_pr_created(repo, pr_url, report):
    if report['vibe_score'] < 50:
        create_jira_ticket(
            project="ARCH",
            summary=f"Architectural debt in {repo}",
            description=f"Score: {report['vibe_score']}/100\nIssues:\n" + "\n".join(report['issues'])
        )
```

---

## ❓ Q&A: Built-in vs Plugin?

> **Q: Why should `pyguard` be a plugin instead of built into `analyze()`?**

### Short Answer

**`pyguard` should be a plugin** because:
1. **Separation of concerns** — Ghostclaw core focuses on architecture; pyguard focuses on type safety
2. **Opt-in** — Not all users need type checking; keep core lean
3. **Independent evolution** — Separate release cycles, dependencies
4. **Zero bloat** — Core remains ~100KB; pyguard adds ~10MB dependencies only for those who want it

---

### Detailed Reasoning

| Aspect | Built-in | Plugin |
|--------|----------|--------|
| **Core size** | bloated with pyguard deps (mypy, typeshed) | lean, only what's needed |
| **User choice** | forced to pay for type checking even if unused | install `ghostclaw-pyguard` only if wanted |
| **Dependency conflicts** | pyguard's version requirements may clash with user's projects | isolated in plugin's virtualenv (conceptually) |
| **Release coupling** | ghostclaw must wait for pyguard updates | independent PyPI releases |
| **Domain focus** | mixes architecture + type safety concerns | single responsibility per package |
| **Upgrade path** | breaking changes in pyguard force ghostclaw bump | users upgrade pyguard plugin separately |

---

### The Architecture Coupling Principle

Ghostclaw's **core competency** is analyzing:
- **Module coupling** (import graphs, circular deps)
- **Cohesion** (file sizes, responsibility distribution)
- **Layering** (dependency direction, forbidden imports)
- **Naming conventions** (via rules engine)

`pyguard`'s **core competency** is:
- **Type annotation completeness**
- **Type correctness** (parameter/return matching)
- **Protocol/interface adherence**
- **Generic/parametric type usage**

These are **orthogonal concerns**. One can have:
- Excellent type safety but terrible coupling (God classes with perfect types)
- Poor type safety but excellent architecture (small modules, but untyped)

**Therefore: keep them separate.** Plugin system allows users to compose the exact analysis stack they need:

```bash
# Minimal: only architecture
pip install ghostclaw

# With type safety
pip install ghostclaw ghostclaw-pyguard

# Full suite
pip install ghostclaw ghostclaw-pyguard ghostclaw-security ghostclaw-rust
```

---

### Technical Integration Mechanism

**Plugin integration** doesn't mean "copy-paste code into core". It means:

1. **Plugin defines** a class inheriting from `StackAnalyzer`
2. **Core loads** that class dynamically at runtime
3. **Core calls** `.analyze()` alongside other stack analyzers
4. **Issues merge** transparently

Example:

```python
# User has both plugins enabled
plugins:
  stacks:
    - "ghostclaw-pyguard"    # adds PyGuardAnalyzer to registry
    - "ghostclaw-rust"       # adds RustAnalyzer to registry

# When analyzing:
analyzer = CodebaseAnalyzer()
report = analyzer.analyze('myrepo/')

# report['issues'] contains:
# - Issues from PythonAnalyzer (coupling)
# - Issues from PyGuardAnalyzer (types)
# - Issues from RustAnalyzer (if repo is Rust)
```

**No core modification needed.** The plugin system registers new analyzers, and core automatically runs all registered analyzers for the detected stack.

---

### Why Not Build `pyguard` Directly?

If we built pyguard directly:

- **Would require** `mypy` as a hard dependency → all users pay 10MB+ install cost
- **Would break** if pyguard has breaking API changes (requires ghostclaw release)
- **Would conflate** two distinct quality dimensions (architecture vs types)
- **Would prevent** users from using alternative type checkers (pyright, mypy, pytype) without modifying core

**Plugin system avoids all these problems.**

---

### Precedent: Linter Ecosystem

Consider how **linters** evolved:

- **Old model:** `pylint` did everything (style, bugs, complexity)
- **New model:** Flake8 + plugins (each focused on one thing)
  - `flake8-bugbear` — bug patterns
  - `flake8-bandit` — security
  - `flake8-docstrings` — documentation

Ghostclaw follows the **Flake8 model**:
- Core = minimal validator + plugin loader
- Each concern = separate installable plugin
- Users compose their toolchain

---

### When _Would_ Something Be Built-in?

Only if:
1. **Universal** — Every user needs it (e.g., stack detection)
2. **Core to vision** — Architecture analysis _is_ ghostclaw's purpose
3. **Tight coupling** — Feature cannot be isolated (requires deep changes)
4. **Zero dependency** — No external packages required

`pyguard` fails all four:
- Not universal (only Python users, and even then optional)
- Not about architecture (different domain)
- Can be isolated (implements `StackAnalyzer` interface)
- Has heavy dependencies

**Conclusion:** Plugin is the correct architectural boundary.

---

## 🔒 Security Model

**Threat:** Plugins execute arbitrary Python code with full access to user's system.

**Mitigations:**
1. **Explicit opt-in** — No auto-loading from plugin dir. User must list each plugin in `~/.ghostclaw/config.yaml`.
2. **Capability declarations** — Plugins declare required permissions:
   ```yaml
   plugins:
     my_plugin:
       enabled: true
       capabilities: [read_files, network, git, subprocess]
   ```
   Core can enforce (e.g., block `subprocess` if user disallows).
3. **Warning on first load** — Show fingerprint/description, ask user to confirm (like VS Code extension install).
4. **Sandbox future** — Optionally run plugins in restricted subprocess (no file access, limited network).
5. **Audit log** — Log plugin actions to `~/.ghostclaw/plugin_audit.log`.

**Default stance:** **Deny by default**. Only plugins user explicitly trusts (via config + manual install) are loaded.

---

## 🧩 Plugin Distribution

**Option 1: PyPI Packages** (recommended for org-wide plugins)

```bash
pip install ghostclaw-rust
# Automatically registers entry points; enable in config.yaml:
plugins:
  stacks:
    - "ghostclaw-rust"
```

**Option 2: Git Clone into `~/.ghostclaw/plugins/`** (for internal scripts)

```bash
cd ~/.ghostclaw/plugins
git clone https://github.com/your-org/ghostclaw-company-rules.git
# Enable in config.yaml:
plugins:
  rules:
    - "~/.ghostclaw/plugins/company-rules/rules.yaml"
  hooks:
    - "~/.ghostclaw/plugins/company-rules/hooks.py:on_pr_created"
```

**Option 3: Direct File Path** (single-file plugins)

```yaml
plugins:
  rules:
    - "/path/to/my_custom_rules.yaml"
  stacks:
    - "/path/to/my_analyzer.py"
```

---

## 📦 Answering Your Question: `pyguard` Integration

> **Should pyguard be built into ghostclaw's `analyze()` or supported via plugins?**

**Answer: Plugin support via a `pyguard` plugin package (`ghostclaw-pyguard`).**

### Why Plugin?

1. **Separation of concerns** — Ghostclaw focuses on **architecture** (module coupling, layering, cohesion). `pyguard` focuses on **type safety and contracts**. Distinct domains.
2. **Dependency management** — `pyguard` may have heavy dependencies (mypy, typeshed). Not everyone wants them in core ghostclaw.
3. **Opt-in** — Some users want type checking; others don't. Plugin keeps core lean.
4. **Independent evolution** — `pyguard` can have its own release cycle, configuration format, and update without ghostclaw core changes.
5. **Better user experience** — Users who only care about coupling metrics don't pay the cost of type checking.

### Implementation: `ghostclaw-pyguard` Plugin

```python
# ghostclaw-pyguard/analyzer.py
from ghostclaw.stacks.base import StackAnalyzer
from ghostclaw.detector import detect_stack  # reuse detector

class PyGuardAnalyzer(StackAnalyzer):
    """Runs pyguard (or mypy/pyright) and converts results to ghostclaw format."""

    def get_extensions(self):
        return ['.py']  # Only Python

    def get_large_file_threshold(self):
        return 300

    def analyze(self, root, files, metrics):
        issues = []
        ghosts = []
        flags = []

        # Run pyguard (or mypy) as subprocess
        try:
            result = subprocess.run(
                ["pyguard", root],
                capture_output=True,
                text=True,
                timeout=60
            )
            # Parse pyguard output (JSON if available)
            findings = self._parse_pyguard_output(result.stdout)
            for finding in findings:
                issues.append(f"[pyguard] {finding['message']}")
                if finding['severity'] == 'error':
                    ghosts.append(f"Type safety violation: {finding['code']}")
        except FileNotFoundError:
            issues.append("pyguard not installed (pip install pyguard)")
        except Exception as e:
            issues.append(f"pyguard execution failed: {e}")

        return {
            "issues": issues,
            "architectural_ghosts": ghosts,
            "red_flags": flags,
            "coupling_metrics": {}  # PyGuard doesn't compute coupling
        }
```

**User experience:**

```bash
pip install ghostclaw-pyguard
# Enable in ~/.ghostclaw/config.yaml:
plugins:
  stacks:
    - "ghostclaw-pyguard"
# Run:
ghostclaw /path/to/python/project
# Output includes:
# • [pyguard] Missing type annotation for function 'foo'
# • [pyguard] Parameter has incompatible type 'int' expected 'str'
```

**Benefits:**
- Core ghostclaw unchanged
- pyguard plugin can be developed/maintained separately
- Users choose which Python analyzers to use (ghostclaw's coupling, pyguard's types, or both)

---

## 🗺️ Implementation Roadmap (Phase 7)

### Week 1: Plugin Loader Core
- [ ] `plugins/loader.py` — discovers plugins from config
- [ ] `plugins/interface.py` — abstract base classes (already implicitly exist in `stacks/base.py`)
- [ ] `config.yaml` schema expansion (plugins section)
- [ ] Safe import mechanism (importlib, catch errors)

### Week 2: Stack Plugin Support
- [ ] Load additional `StackAnalyzer` classes from entry points + local files
- [ ] Register them in `stacks/STACK_REGISTRY` dynamically
- [ ] Test with dummy plugin (e.g., `ghostclaw-example-stack`)
- [ ] Handle plugin errors gracefully (disable broken plugins, log warning)

### Week 3: Rule Plugin Support
- [ ] Extend `core/validator.py` to load rules from plugin YAMLs
- [ ] Merge all rules (core + plugins) into single validator
- [ ] Add new rule types: `content_search`, `import_pattern`
- [ ] Test with custom rule plugin

### Week 4: Hook System
- [ ] Define hook points in core (`hooks.py` module)
- [ ] Load hook functions from plugins
- [ ] Call hooks at appropriate lifecycle events
- [ ] Example: `on_analysis_complete` hook sends notification
- [ ] Error isolation: broken hook shouldn't crash analysis

### Week 5: Documentation & Examples
- [ ] Create `plugins/` directory in repo with example plugins
- [ ] `example-stack/` — minimal stack plugin (HelloWorldAnalyzer)
- [ ] `example-rules/` — custom YAML rules
- [ ] `example-hooks/` — Slack webhook example
- [ ] Update README with plugin development guide
- [ ] Publish placeholder packages to Test PyPI:
  - `ghostclaw-pyguard` (demo)
  - `ghostclaw-security` (example)

---

## 🧪 Testing Strategy

**Unit tests:**
- Plugin loader discovers entry points correctly
- Config parsing with multiple plugin sources
- Graceful degradation when plugin fails to load

**Integration tests:**
- Install a mock plugin (`ghostclaw-test`) and verify it runs
- Hook invocation order and error handling

**Security tests:**
- Plugin with malicious code is not executed unless explicitly enabled
- Capability system (if implemented) blocks disallowed operations

---

## 📋 Configuration Schema

```yaml
# ~/.ghostclaw/config.yaml

# Core ghostclaw settings
vibe_thresholds:
  healthy: 80
  warning: 60
  critical: 40

# Plugin system
plugins:
  # Load additional stack analyzers
  stacks:
    - "ghostclaw-rust"                    # pip package (entry point)
    - "/path/to/custom_stack.py"          # local file (StackAnalyzer subclass)

  # Load extra rule definitions (YAML)
  rules:
    - "ghostclaw-security"                # pip package
    - "~/.ghostclaw/plugins/rules.yaml"  # local file

  # Load hook functions
  hooks:
    - "ghostclaw-slack.on_pr_created"                # entry point
    - "~/.ghostclaw/plugins/hooks.py:on_analysis_complete"  # module:function

  # Per-plugin configuration
  config:
    ghostclaw-slack:
      webhook_url: "https://hooks.slack.com/..."
      channel: "#arch-alerts"
    ghostclaw-pyguard:
      strict: true
      extra_checks: ["security", "performance"]
```

---

## 🎬 Example Plugin: `ghostclaw-pyguard` (Complete Integration)

This example demonstrates the **complete plugin mechanism** from package creation to user experience.

---

### Part 1: Plugin Package Structure

```
ghostclaw-pyguard/
├── pyproject.toml
├── README.md
├── src/
│   └── ghostclaw_pyguard/
│       ├── __init__.py
│       ├── analyzer.py
│       └── config.py
└── tests/
```

---

### Part 2: The Analyzer Implementation

**`src/ghostclaw_pyguard/analyzer.py`**

```python
"""PyGuard integration plugin for ghostclaw."""

import subprocess
import json
from typing import Dict, List
from ghostclaw.stacks.base import StackAnalyzer


class PyGuardAnalyzer(StackAnalyzer):
    """
    Runs pyguard type checker and translates results into ghostclaw's format.

    This analyzer:
    - Only handles .py files
    - Invokes pyguard as subprocess
    - Parses JSON output
    - Converts type errors into architectural ghosts
    """

    def get_extensions(self) -> List[str]:
        return ['.py']

    def get_large_file_threshold(self) -> int:
        return 300  # Use same threshold as core Python analyzer

    def analyze(self, root: str, files: List[str], metrics: Dict) -> Dict:
        issues = []
        ghosts = []
        flags = []

        # Skip if pyguard not installed
        try:
            subprocess.run(["pyguard", "--version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            issues.append("pyguard not installed (pip install pyguard)")
            return {"issues": issues, "architectural_ghosts": [], "red_flags": []}

        # Run pyguard on the repository
        try:
            result = subprocess.run(
                ["pyguard", "--json", root],
                capture_output=True,
                text=True,
                timeout=120
            )

            # pyguard returns non-zero exit code when issues found
            if result.returncode == 0:
                return {"issues": [], "architectural_ghosts": [], "red_flags": []}

            findings = json.loads(result.stdout)

            for finding in findings.get('issues', []):
                # Format: [pyguard] message (file:line)
                msg = f"[pyguard] {finding['message']} ({finding['file']}:{finding['line']})"
                issues.append(msg)

                # Type errors are architectural ghosts (break contracts)
                if finding.get('severity') in ('error', 'critical'):
                    ghosts.append(f"Type safety violation: {finding['code']}")

        except json.JSONDecodeError:
            issues.append("pyguard output parsing failed (invalid JSON)")
        except subprocess.TimeoutExpired:
            issues.append("pyguard timed out (>120s)")
        except Exception as e:
            issues.append(f"pyguard execution error: {str(e)}")

        return {
            "issues": issues,
            "architectural_ghosts": ghosts,
            "red_flags": flags,
            "coupling_metrics": {}  # PyGuard doesn't compute coupling metrics
        }


# Setuptools entry point returns an instance
def register() -> StackAnalyzer:
    """Entry point for ghostclaw to discover this plugin."""
    return PyGuardAnalyzer()
```

---

### Part 3: Package Configuration with Entry Point

**`pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "ghostclaw-pyguard"
version = "0.1.0"
description = "PyGuard type checking plugin for ghostclaw"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [{name = "Your Name"}]
dependencies = [
    "ghostclaw>=0.1.3",  # depends on plugin-capable ghostclaw
    "pyguard>=0.5.0",    # the actual type checker
]

[project.entry-points."ghostclaw.stacks"]
pyguard = "ghostclaw_pyguard.analyzer:register"
```

**Key line:** `[project.entry-points."ghostclaw.stacks"]` declares this plugin provides a stack analyzer.

---

### Part 4: User Installation & Configuration

**Step 1: Install plugin**

```bash
pip install ghostclaw-pyguard
# This also installs pyguard as dependency
```

**Step 2: Enable in config**

**`~/.ghostclaw/config.yaml`**

```yaml
plugins:
  stacks:
    - "ghostclaw-pyguard"   # discovered via entry point
  # Optionally also keep core Python analyzer (it's enabled by default)
```

**Step 3: Run ghostclaw**

```bash
ghostclaw /path/to/python/project --json
```

**Sample output:**

```json
{
  "vibe_score": 67,
  "stack": "python",
  "issues": [
    "[pyguard] Missing type annotation for function 'process_data' (app.py:42)",
    "[pyguard] Parameter has incompatible type 'int' expected 'str' (utils.py:15)",
    "3 files >300 lines (ModuleGhosts)"
  ],
  "architectural_ghosts": [
    "Type safety violation: missing_type_annotation",
    "ModuleGhosts: consider extracting smaller modules"
  ],
  "metadata": {
    "analyzer": "ghostclaw-refactored",
    "plugins_used": ["pyguard"]
  }
}
```

✅ **Notice:** Issues from **both** core Python analyzer (coupling) and pyguard plugin (types) are merged.

---

### Part 5: Advanced Configuration (Per-Plugin Options)

The plugin can read its own config section:

**`~/.ghostclaw/config.yaml`**

```yaml
plugins:
  stacks:
    - module: "ghostclaw-pyguard"
      config:
        strict: true          # treat warnings as errors
        exclude_tests: true  # ignore test files
        max_line_length: 120
```

**Plugin reads config:**

```python
# In analyzer.py
class PyGuardAnalyzer(StackAnalyzer):
    def __init__(self):
        self.config = {
            'strict': False,
            'exclude_tests': False,
            'max_line_length': 100
        }

    def analyze(self, root, files, metrics):
        # Apply plugin-specific config
        if self.config.get('exclude_tests'):
            files = [f for f in files if 'test' not in f]
        # ...
```

---

### Part 6: How Core Discovers & Loads the Plugin

*(This happens inside `PluginLoader.load_stacks()`)*

```python
# Simplified pseudocode
def load_stack_plugins(self, plugin_specs):
    # 1. Discover entry points
    from importlib.metadata import entry_points
    eps = entry_points(group='ghostclaw.stacks')
    for ep in eps:
        if ep.name in plugin_specs:  # user enabled this plugin
            analyzer_class = ep.load()  # imports the module
            instance = analyzer_class()  # instantiate
            STACK_REGISTRY[ep.name] = instance

    # 2. Load local file plugins
    for spec in plugin_specs:
        if spec.endswith('.py'):
            spec = importlib.util.spec_from_file_location("plugin", spec)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            # Assume module has `register()` function
            analyzer = module.register()
            STACK_REGISTRY[analyzer.get_name()] = analyzer
```

**Result:** `STACK_REGISTRY` now contains both core analyzers and plugin analyzers.

---

### Complete Integration Summary

| Step | What Happens |
|------|--------------|
| 1. User installs `ghostclaw-pyguard` | PyPI package with entry point |
| 2. User adds to `config.yaml` | Opt-in via `plugins.stacks: ["ghostclaw-pyguard"]` |
| 3. Ghostclaw starts | `PluginLoader` discovers entry point |
| 4. Plugin loaded | `PyGuardAnalyzer()` added to `STACK_REGISTRY` |
| 5. Analysis runs | For Python stack: **both** `PythonAnalyzer` and `PyGuardAnalyzer` run |
| 6. Results merge | Issues from both analyzers appear in final report |
| 7. User sees combined output | Coupling issues + type errors in one JSON |

---

## 📦 Answering Your Question: `pyguard` Integration

---

## 🤔 Open Questions

1. **Plugin isolation?** Should we run plugins in separate process (for crash safety)? Probably too heavy for v1; use try/except.
2. **Conflict resolution?** What if two plugins define same rule ID? Last loaded wins, or error? → **Error, force unique IDs.**
3. **Hook ordering?** Should plugins specify priority? → Simple: alphabetical by plugin name; allow `priority: high` in hook config.
4. **Missing dependencies?** If plugin requires `pyguard` but it's not installed, should we fail or warn? → **Warn and disable plugin.**
5. **Version compatibility?** Plugins target specific ghostclaw versions. Should we enforce? → **Optional: declare `requires-ghostclaw: ">=0.1.0"` in plugin metadata, warn if mismatch.**

---

## 📈 Success Metrics

- At least 3 community plugins published to PyPI within 6 months
- Users can install `ghostclaw-<stack>` without modifying core
- Plugin loading time < 100ms
- Zero security incidents from plugin system

---

## 🚀 Next Steps

If approved:
1. Implement `PluginLoader` class
2. Add plugin config to main config schema
3. Build example plugin repo (`ghostclaw-example-stack`)
4. Update `CodebaseAnalyzer` to use plugin stacks
5. Update `validator.py` to merge plugin rules
6. Add hook invocation in relevant places
7. Write docs: "Building Your First Plugin"

---

**Bottom line:** Plugin system makes ghostclaw **extensible without bloat**. `pyguard` is the perfect candidate: a powerful type checker that should be **optional**, not mandatory. Users who want it install `ghostclaw-pyguard`; others keep their lean coupling-only setup.

**Do you approve this design?** 🛠️
