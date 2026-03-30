"""Storage management command group."""

import argparse
from pathlib import Path

from ghostclaw.cli.commander import Command
from ghostclaw.core.adapters.registry import PluginRegistry


class StorageListCommand(Command):
    """List all available storage adapters."""

    @property
    def name(self) -> str:
        """
        Command name for the storage-list CLI command.
        
        Returns:
            command_name (str): The literal string 'storage-list'.
        """
        return "storage list"

    @property
    def description(self) -> str:
        """
        Human-readable description of the storage-list command.
        
        Returns:
            str: The description text "List all storage adapters (built-in and external) with their availability".
        """
        return "List all storage adapters (built-in and external) with their availability"

    def configure_parser(self, parser: argparse.ArgumentParser):
        """
        Add the `--repo` command-line argument to specify the repository path used to scan for local plugins.
        
        Parameters:
            parser (argparse.ArgumentParser): The argument parser to configure. The added `--repo` option accepts a filesystem path (Path), defaults to the current working directory, and is used to locate the local plugins directory (<repo>/.ghostclaw/plugins).
        """
        parser.add_argument(
            "--repo",
            type=Path,
            default=Path.cwd(),
            help="Repository path to scan for local plugins (default: current directory)",
        )

    async def execute(self, args) -> int:
        """
        List storage adapter plugins and print their availability and enabled state.
        
        Scans the repository (from `args.repo` or the current working directory) for local plugins, registers built-in and discovered external plugins, and identifies plugins that expose the `ghost_save_report` capability. Prints a table (using Rich if available, otherwise plain text) with columns: Name, Version, Description, Available, and Enabled. If no storage adapters are found, prints "No storage adapters found." and exits.
        
        Parameters:
            args (argparse.Namespace): Parsed command-line arguments. The `repo` attribute, if present, is used as the repository Path to scan for local plugins.
        
        Returns:
            int: Exit code (always `0`).
        """
        repo_path = args.repo or Path.cwd()

        # Initialize registry and register plugins
        registry = PluginRegistry()
        registry.register_internal_plugins()
        local_plugins = repo_path / ".ghostclaw" / "plugins"
        if local_plugins.exists():
            registry.load_external_plugins(local_plugins)

        # Filter to storage adapters only (those that have ghost_save_report)
        storage_plugins = []
        for name, plugin in registry._registered_plugins:
            if hasattr(plugin, "ghost_save_report"):
                # Get metadata from plugin (might be method or attribute)
                meta = None
                if hasattr(plugin, "get_metadata"):
                    try:
                        meta = plugin.get_metadata()
                    except Exception:
                        pass
                elif hasattr(plugin, "ghost_get_metadata"):
                    try:
                        meta = plugin.ghost_get_metadata()
                    except Exception:
                        pass
                storage_plugins.append((name, meta, plugin))

        if not storage_plugins:
            print("No storage adapters found.")
            return 0

        # Print table
        try:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(title="Storage Adapters")
            table.add_column("Name", style="cyan")
            table.add_column("Version", style="magenta")
            table.add_column("Description")
            table.add_column("Available", style="green")
            table.add_column("Enabled", style="yellow")

            # Determine which are enabled (via enabled_plugins filter)
            enabled_set = registry.enabled_plugins if registry.enabled_plugins is not None else set(
                name for name, _, _ in storage_plugins
            )

            for name, meta, plugin in storage_plugins:
                meta_name = name
                meta_version = "?"
                meta_desc = ""
                if meta:
                    if hasattr(meta, "name"):
                        meta_name = getattr(meta.name, "value", meta.name) if hasattr(meta.name, "value") else meta.name
                    if hasattr(meta, "version"):
                        meta_version = meta.version
                    if hasattr(meta, "description"):
                        meta_desc = meta.description
                elif isinstance(meta, dict):
                    meta_name = meta.get("name", name)
                    meta_version = meta.get("version", "?")
                    meta_desc = meta.get("description", "")

                # Check availability
                available = False
                try:
                    if hasattr(plugin, "is_available"):
                        available = await plugin.is_available()
                    else:
                        available = True
                except Exception:
                    available = False

                enabled = name in enabled_set

                table.add_row(
                    meta_name,
                    meta_version,
                    meta_desc,
                    "✅" if available else "❌",
                    "✅" if enabled else "⭕",
                )
            console.print(table)
        except ImportError:
            # Fallback to plain text
            print("Name | Version | Description | Available | Enabled")
            for name, meta, plugin in storage_plugins:
                meta_name = name
                meta_version = "?"
                meta_desc = ""
                if meta:
                    if hasattr(meta, "name"):
                        meta_name = getattr(meta.name, "value", meta.name) if hasattr(meta.name, "value") else meta.name
                    if hasattr(meta, "version"):
                        meta_version = meta.version
                    if hasattr(meta, "description"):
                        meta_desc = meta.description
                elif isinstance(meta, dict):
                    meta_name = meta.get("name", name)
                    meta_version = meta.get("version", "?")
                    meta_desc = meta.get("description", "")

                available = False
                try:
                    if hasattr(plugin, "is_available"):
                        available = await plugin.is_available()
                    else:
                        available = True
                except Exception:
                    available = False

                enabled = name in (registry.enabled_plugins or {name})
                print(f"{meta_name} | {meta_version} | {meta_desc} | {'Yes' if available else 'No'} | {'Yes' if enabled else 'No'}")
        return 0
