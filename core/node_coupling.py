"""Node.js import analysis using built-in parsing (no external deps)."""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, deque


class NodeImportAnalyzer:
    """Analyzes Node.js imports using pattern matching."""

    # Patterns to match ES6 imports and CommonJS requires
    PATTERNS = [
        # import ... from 'module'
        re.compile(r"import\s+(?:[\w*{}\n, ]+)\s+from\s+['\"]([^'\"\n]+)['\"]"),
        # import 'module'
        re.compile(r"import\s+['\"]([^'\"\n]+)['\"]"),
        # require('module')
        re.compile(r"require\s*\(\s*['\"]([^'\"\n]+)['\"]\s*\)"),
        # require("module")
        re.compile(r'require\s*\(\s*[\'"]([^\'"\n]+)[\'"]\s*\)'),
        # export ... from 'module'
        re.compile(r"export\s*(?:[\w*{}\n, ]+)\s+from\s+['\"]([^'\"\n]+)['\"]"),
    ]

    def __init__(self, root: str):
        self.root = Path(root)
        self.graph = self._init_graph()

    def _init_graph(self) -> Dict:
        """Initialize empty graph structure."""
        return {
            "nodes": set(),
            "edges": [],
            "module_to_file": {}
        }

    def _is_local_import(self, module_path: str, known_modules: Set[str]) -> bool:
        """Heuristic: is this import from within the project?"""
        # Absolute/relative path imports (start with . or /)
        if module_path.startswith('.') or module_path.startswith('/'):
            return True
        # If it's a known module (we've seen it as a file in the project)
        if module_path in known_modules:
            return True
        return False

    def _module_name_from_file(self, filepath: Path) -> str:
        """Convert file path to a module identifier."""
        rel = filepath.relative_to(self.root)
        if rel.name == 'index.js':
            parent = rel.parent
            if parent == Path('.'):
                return '.'
            return str(parent).replace('/', '.')
        return str(rel.with_suffix('')).replace('/', '.')

    def analyze(self) -> Dict:
        issues = []
        ghosts = []
        flags = []

        # Map all relevant files to module names
        node_exts = ['.js', '.jsx', '.ts', '.tsx']
        files = []
        for ext in node_exts:
            files.extend(self.root.rglob(f"*{ext}"))

        known_modules = set()
        for f in files:
            module_name = self._module_name_from_file(f)
            self.graph["module_to_file"][module_name] = str(f)
            self.graph["nodes"].add(module_name)
            known_modules.add(module_name)

        # Also add directories that could be modules (have index.js or package.json)
        for dirpath in self.root.rglob('*'):
            if dirpath.is_dir():
                if any((dirpath / 'index.js').exists()) or (dirpath / 'package.json').exists():
                    module_name = str(dirpath.relative_to(self.root)).replace('/', '.')
                    self.graph["nodes"].add(module_name)
                    known_modules.add(module_name)

        # Parse each file for imports
        for f in files:
            try:
                content = f.read_text(encoding='utf-8', errors='ignore')
                importer = self._module_name_from_file(f)

                for pattern in self.PATTERNS:
                    for match in pattern.finditer(content):
                        imported = match.group(1)
                        # Strip ?query and #hash
                        imported = imported.split('?')[0].split('#')[0]
                        # Resolve relative paths?
                        if self._is_local_import(imported, known_modules):
                            self.graph["edges"].append((importer, imported))
            except Exception:
                continue

        # Detect cycles
        cycles = self._detect_cycles()
        if cycles:
            for cycle in cycles[:5]:
                cycle_str = " → ".join(cycle)
                issues.append(f"Circular dependency: {cycle_str}")
                ghosts.append(f"Circular dependency: {cycle_str}")
            if len(cycles) > 5:
                issues.append(f"... and {len(cycles) - 5} more cycles")

        # Compute coupling metrics per module
        coupling_metrics = {}
        for node in self.graph["nodes"]:
            afferent = sum(1 for src, dst in self.graph["edges"] if dst == node)
            efferent = sum(1 for src, dst in self.graph["edges"] if src == node)
            total = afferent + efferent
            instability = efferent / total if total > 0 else 0.0
            coupling_metrics[node] = {
                "afferent": afferent,
                "efferent": efferent,
                "instability": round(instability, 2)
            }
            if instability > 0.8:
                issues.append(f"Module {node} is highly unstable (I={instability:.2f}, ce={efferent})")
                ghosts.append(f"Unstable module {node}: knows too many others")

        return {
            "coupling_metrics": coupling_metrics,
            "circular_dependencies": [{"cycle": cycle} for cycle in cycles],
            "issues": issues,
            "architectural_ghosts": ghosts,
            "red_flags": flags
        }

    def _detect_cycles(self) -> List[List[str]]:
        """Detect cycles in the import graph."""
        graph = defaultdict(list)
        for src, dst in self.graph["edges"]:
            graph[src].append(dst)

        visited = set()
        stack = []
        cycles = []

        def dfs(node):
            if node in stack:
                cycle_start = stack.index(node)
                cycles.append(stack[cycle_start:] + [node])
                return
            if node in visited:
                return
            visited.add(node)
            stack.append(node)
            for neighbor in graph.get(node, []):
                dfs(neighbor)
            stack.pop()

        for node in self.graph["nodes"]:
            dfs(node)

        return cycles
