"""Import coupling analysis — detect dependencies, circular imports, layer violations."""

import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, deque


class ImportGraph:
    """Represents module dependencies in a codebase."""

    def __init__(self):
        self.nodes: Set[str] = set()
        self.edges: List[Tuple[str, str]] = []  # (importer, imported)
        self.module_to_file: Dict[str, str] = {}  # Map module name to file path

    def add_edge(self, importer: str, imported: str):
        self.nodes.add(importer)
        self.nodes.add(imported)
        self.edges.append((importer, imported))

    def get_afferent_coupling(self, module: str) -> int:
        """Number of modules that import this module (incoming edges)."""
        return sum(1 for src, dst in self.edges if dst == module)

    def get_efferent_coupling(self, module: str) -> int:
        """Number of modules this module imports (outgoing edges)."""
        return sum(1 for src, dst in self.edges if src == module)

    def get_instability(self, module: str) -> float:
        """Instability = efferent / (afferent + efferent). 0=stable, 1=unstable."""
        ca = self.get_afferent_coupling(module)
        ce = self.get_efferent_coupling(module)
        total = ca + ce
        return ce / total if total > 0 else 0.0

    def detect_circular_dependencies(self) -> List[List[str]]:
        """Find cycles in the import graph."""
        # Build adjacency list
        graph = defaultdict(list)
        for src, dst in self.edges:
            graph[src].append(dst)

        # DFS to detect cycles
        visited = set()
        stack = []
        cycles = []

        def dfs(node, path):
            if node in stack:
                # Cycle detected: from node back to itself in current path
                cycle_start = stack.index(node)
                cycle = stack[cycle_start:] + [node]
                cycles.append(cycle)
                return
            if node in visited:
                return
            visited.add(node)
            stack.append(node)
            for neighbor in graph.get(node, []):
                dfs(neighbor, path + [neighbor])
            stack.pop()

        for node in self.nodes:
            dfs(node, [])

        return cycles


class PythonImportAnalyzer:
    """Analyzes Python imports using AST."""

    def __init__(self, root: str):
        self.root = Path(root)
        self.graph = ImportGraph()

    def analyze(self) -> Dict:
        """
        Scan all .py files and build import dependency graph.

        Returns:
            Dict with coupling metrics and detected issues
        """
        # Map file paths to module names (relative to root)
        for py_file in self.root.rglob("*.py"):
            rel_path = py_file.relative_to(self.root)
            # Convert path to dotted module name
            if rel_path.name == "__init__.py":
                module_name = ".".join(rel_path.parent.parts)
            else:
                module_name = ".".join(rel_path.with_suffix("").parts)
            self.graph.module_to_file[module_name] = str(py_file)
            self.graph.nodes.add(module_name)

        # Parse each file and extract imports
        for module_name, filepath in self.graph.module_to_file.items():
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported_module = alias.name
                            if self._is_local_import(imported_module):
                                self.graph.add_edge(module_name, imported_module)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imported_module = node.module
                            if self._is_local_import(imported_module):
                                self.graph.add_edge(module_name, imported_module)
            except Exception:
                continue  # Skip files with parse errors

        # Compute metrics
        return self._compute_report()

    def _is_local_import(self, module_name: str) -> bool:
        """Check if an import is likely from the local project (not stdlib/third-party)."""
        # Heuristic: if the module prefix exists in our graph, it's local
        for known in self.graph.nodes:
            if module_name == known or module_name.startswith(known + "."):
                return True
        return False

    def _compute_report(self) -> Dict:
        """Generate coupling report with issues."""
        issues = []
        ghosts = []
        flags = []

        # Detect circular dependencies
        cycles = self.graph.detect_circular_dependencies()
        if cycles:
            for cycle in cycles[:5]:  # Limit to first 5
                cycle_str = " → ".join(cycle)
                issues.append(f"Circular dependency: {cycle_str}")
                ghosts.append(f"Circular dependency: {cycle_str}")
            if len(cycles) > 5:
                issues.append(f"... and {len(cycles) - 5} more cycles")

        # Identify highly unstable modules (God modules)
        for module in self.graph.nodes:
            instability = self.graph.get_instability(module)
            if instability > 0.8:
                ce = self.graph.get_efferent_coupling(module)
                issues.append(f"Module {module} is highly unstable (I={instability:.2f}, ce={ce})")
                ghosts.append(f"Unstable module {module}: knows too many others")

        # Modules with high afferent coupling (utility modules)
        for module in self.graph.nodes:
            ca = self.graph.get_afferent_coupling(module)
            if ca > 10:
                issues.append(f"Module {module} is heavily depended upon (ca={ca}) — treat as stable layer")

        return {
            "coupling_metrics": {
                module: {
                    "afferent": self.graph.get_afferent_coupling(module),
                    "efferent": self.graph.get_efferent_coupling(module),
                    "instability": round(self.graph.get_instability(module), 2)
                }
                for module in self.graph.nodes
            },
            "circular_dependencies": [{"cycle": cycle} for cycle in cycles],
            "issues": issues,
            "architectural_ghosts": ghosts,
            "red_flags": flags
        }
