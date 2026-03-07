"""Plugin registry for Ghostclaw's modular architecture."""

import pluggy
import importlib.util
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from ghostclaw.core.adapters.hooks import GhostclawPluginSpecs
from ghostclaw.core.adapters.base import AdapterMetadata

class PluginRegistry:
    """Manages the lifecycle and invocation of Ghostclaw plugins."""

    def __init__(self, project_root: Optional[Path] = None):
        self.pm = pluggy.PluginManager("ghostclaw")
        self.pm.add_hookspecs(GhostclawPluginSpecs)
        # Wrap pm.register to track all plugins (name, instance)
        self._registered_plugins: List[Tuple[str, Any]] = []
        _original_register = self.pm.register
        def _tracked_register(plugin, name=None):
            _original_register(plugin, name=name)
            self._registered_plugins.append((name, plugin))
        self.pm.register = _tracked_register
        self.project_root = project_root
        
        # Track plugin names and their sources
        self.internal_plugins = set()
        self.external_plugins = set()

        # Accumulate errors during analysis runs
        self.errors: List[str] = []

        # Plugin enable/disable filter (None = all enabled)
        self.enabled_plugins: Optional[Set[str]] = None
        self._registered_plugins: List[Tuple[str, Any]] = []  # List of (name, plugin instance)

        # Internal registry of plugins for runtime filtering
        
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
            spec = importlib.util.spec_from_file_location(f"ghostclaw.plugins.{name}", str(path))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"ghostclaw.plugins.{name}"] = module
                spec.loader.exec_module(module)

                from ghostclaw.core.adapters.base import BaseAdapter
                import inspect

                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if obj.__module__ == module.__name__:
                        try:
                            instance = obj()
                            # Determine friendly name from metadata if available
                            try:
                                meta = instance.get_metadata()
                                plugin_name = meta.name
                            except Exception:
                                plugin_name = f"{name}_{obj.__name__}"
                                meta = None

                            # Check if plugin is enabled
                            if self.enabled_plugins is not None and plugin_name not in self.enabled_plugins:
                                logger.debug(f"Plugin '{plugin_name}' is disabled by config; skipping.")
                                continue

                            # Version compatibility check (only if we have metadata)
                            if meta and (meta.min_ghostclaw_version or meta.max_ghostclaw_version):
                                try:
                                    # Avoid circular import by fetching version via a central version module
                                    from ghostclaw.version import __version__ as gc_version
                                    if not self._check_version_compatible(gc_version, meta):
                                        logger.warning(
                                            f"Plugin '{plugin_name}' incompatible with Ghostclaw {gc_version} "
                                            f"(requires {meta.min_ghostclaw_version or 'any'} - {meta.max_ghostclaw_version or 'any'}). Skipping."
                                        )
                                        continue
                                except Exception as e:
                                    logger.debug(f"Version check error for plugin {plugin_name}: {e}")

                            self.pm.register(instance, name=plugin_name)

                            self._registered_plugins.append((plugin_name, instance))
                            self.external_plugins.add(plugin_name)
                        except Exception as e:
                            logger.error(f"Failed to load plugin class {obj.__name__}: {e}")
        except Exception as e:
            logger.debug(f"Error loading plugin module at {path}: {e}")

    async def run_analysis(self, root: str, files: List[str]) -> List[Dict[str, Any]]:
        """Invoke all enabled metric adapters concurrently, collecting errors."""
        import asyncio
        self.errors = []  # reset

        tasks = []
        # Determine which plugins to run
        for name, plugin in self.pm.list_name_plugin():
            # Filter by enabled_plugins if set
            if self.enabled_plugins is not None and name not in self.enabled_plugins:
                continue
            # Only consider adapters with ghost_analyze
            if hasattr(plugin, 'ghost_analyze'):
                tasks.append(self._run_adapter(name, plugin, root, files))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks)
        return results

    async def _run_adapter(self, name: str, plugin, root: str, files: List[str]) -> Dict[str, Any]:
        """Run a single adapter and capture errors."""
        try:
            return await plugin.ghost_analyze(root, files)
        except Exception as e:
            self.errors.append(f"Plugin '{name}': {type(e).__name__}: {e}")
            return {}

    def _check_version_compatible(self, current: str, meta: AdapterMetadata) -> bool:
        """Check if current Ghostclaw version is within plugin's required range using simple version comparison."""
        def parse(v: str):
            parts = v.split('.')
            nums = []
            for p in parts[:3]:
                try:
                    nums.append(int(p))
                except ValueError:
                    # numeric prefix only
                    num = ''
                    for ch in p:
                        if ch.isdigit():
                            num += ch
                        else:
                            break
                    nums.append(int(num) if num else 0)
            while len(nums) < 3:
                nums.append(0)
            return tuple(nums)

        cur_t = parse(current)
        if meta.min_ghostclaw_version:
            min_t = parse(meta.min_ghostclaw_version)
            if cur_t < min_t:
                return False
        if meta.max_ghostclaw_version:
            max_t = parse(meta.max_ghostclaw_version)
            if cur_t > max_t:
                return False
        return True

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
