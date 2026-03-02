"""Import coupling analysis — detect dependencies, circular imports, layer violations."""

import ast
from pathlib import Path
from typing import Dict, List
from core.graph import ImportGraph
from core.detector import EXCLUDE_DIRS, _should_exclude, ENTRY_POINT_DIRS


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
            # Apply exclusion filter
            if _should_exclude(rel_path.parts):
                continue
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
                            if self._is_local_import(imported_module) and imported_module in self.graph.module_to_file:
                                self.graph.add_edge(module_name, imported_module)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imported_module = node.module
                            if self._is_local_import(imported_module) and imported_module in self.graph.module_to_file:
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

        # Identify highly unstable modules (God modules), excluding entry points
        for module in self.graph.nodes:
            # Skip entry point modules (cli, scripts, etc.) from instability warnings
            module_parts = module.split('.')
            if any(part in ENTRY_POINT_DIRS for part in module_parts):
                continue

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
