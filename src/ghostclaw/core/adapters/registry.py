"""Plugin registry for Ghostclaw's modular architecture."""

import pluggy
import importlib.util
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from ghostclaw.core.adapters.hooks import GhostclawPluginSpecs

class PluginRegistry:
    """Manages the lifecycle and invocation of Ghostclaw plugins."""

    def __init__(self, project_root: Optional[Path] = None):
        self.pm = pluggy.PluginManager("ghostclaw")
        self.pm.add_hookspecs(GhostclawPluginSpecs)
        self.project_root = project_root
        
        # Track plugin names and their sources
        self.internal_plugins = set()
        self.external_plugins = set()
        
    def register_internal_plugins(self):
        """Register built-in adapters if not already registered."""
        from ghostclaw.core.adapters.metric.pyscn import PySCNAdapter
        from ghostclaw.core.adapters.metric.ai_codeindex import AICodeIndexAdapter
        from ghostclaw.core.adapters.storage.sqlite import SQLiteStorageAdapter
        from ghostclaw.core.adapters.target.json import JsonTargetAdapter
        
        adapters = {
            "pyscn": PySCNAdapter,
            "ai-codeindex": AICodeIndexAdapter,
            "sqlite": SQLiteStorageAdapter,
            "json_target": JsonTargetAdapter
        }

        for name, adapter_cls in adapters.items():
            if not self.pm.get_plugin(name):
                self.pm.register(adapter_cls(), name=name)
                self.internal_plugins.add(name)

    def load_external_plugins(self, plugins_dir: Path):
        """
        Scan a directory for plugins and register them.
        
        A plugin is a Python module or package with 'hookimpl' markers.
        """
        if not plugins_dir.exists():
            return

        for path in plugins_dir.iterdir():
            if path.is_dir() and (path / "__init__.py").exists():
                self._load_module_plugin(path.name, path / "__init__.py")
            elif path.suffix == ".py":
                self._load_module_plugin(path.stem, path)

    def _load_module_plugin(self, name: str, path: Path):
        """Dynamically load a python module and register its adapters."""
        try:
            # Pluggy can register modules directly IF the hooks are top-level functions.
            # But our adapters are classes. We should instantiate them if they exist.
            spec = importlib.util.spec_from_file_location(f"ghostclaw.plugins.{name}", str(path))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"ghostclaw.plugins.{name}"] = module
                spec.loader.exec_module(module)
                
                # Register the module itself (for top-level hooks)
                # self.pm.register(module, name=name)
                
                # Search for classes with hook implementations
                from ghostclaw.core.adapters.base import BaseAdapter
                import inspect
                
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    # Check if it looks like an adapter (has our hooks or inherits from BaseAdapter)
                    if obj.__module__ == module.__name__:
                        instance = obj()
                        plugin_name = f"{name}_{obj.__name__}"
                        self.pm.register(instance, name=plugin_name)
                        self.external_plugins.add(plugin_name)
        except Exception:
            pass

    async def run_analysis(self, root: str, files: List[str]) -> List[Dict[str, Any]]:
        """Invoke all metric adapters concurrently."""
        import asyncio
        coroutines = self.pm.hook.ghost_analyze(root=root, files=files)
        if not coroutines:
            return []
        results = await asyncio.gather(*coroutines)
        return results if results else []

    async def emit_event(self, event_type: str, data: Any):
        """Broadcast events to all target adapters."""
        import asyncio
        coroutines = self.pm.hook.ghost_emit(event_type=event_type, data=data)
        if coroutines:
            await asyncio.gather(*coroutines)

    async def save_report(self, report: Any) -> List[str]:
        """Save report via all storage adapters."""
        import asyncio
        coroutines = self.pm.hook.ghost_save_report(report=report)
        if not coroutines:
            return []
        ids = await asyncio.gather(*coroutines)
        return [i for i in ids if i] if ids else []

    def get_plugin_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all registered plugins."""
        return self.pm.hook.ghost_get_metadata()

# Global registry instance
registry = PluginRegistry()
