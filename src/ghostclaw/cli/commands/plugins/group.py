"""
PluginsCommand — Top-level 'plugins' command group.

This command groups all plugin management subcommands (list, add, remove, etc.).
"""

import sys
from argparse import ArgumentParser, Namespace
from ghostclaw.cli.commander import Command
from .base import PluginsCommand as SubCommandBase
from .list import PluginsListCommand
from .add import PluginsAddCommand
from .remove import PluginsRemoveCommand
from .info import PluginsInfoCommand
from .enable import PluginsEnableCommand
from .disable import PluginsDisableCommand
from .test import PluginsTestCommand
from .scaffold import PluginsScaffoldCommand


class PluginsCommand(SubCommandBase):
    """
    Main 'plugins' command that dispatches to subcommands.
    """
    _auto_register = True  # Override base to be registered

    def __init__(self):
        super().__init__()
        # Mapping of subcommand name to class
        self._subcommand_map = {}

    @property
    def name(self) -> str:
        return "plugins"

    @property
    def description(self) -> str:
        return "Manage ghostclaw plugins"

    def configure_parser(self, parser: ArgumentParser) -> None:
        # Create subparsers for each plugin subcommand
        subparsers = parser.add_subparsers(dest="plugin_subcommand", required=True, help="Plugin subcommand")

        # List of all subcommand classes
        subcommand_classes = [
            PluginsListCommand,
            PluginsAddCommand,
            PluginsRemoveCommand,
            PluginsInfoCommand,
            PluginsEnableCommand,
            PluginsDisableCommand,
            PluginsTestCommand,
            PluginsScaffoldCommand,
        ]

        for cls in subcommand_classes:
            # Instantiate to get metadata
            instance = cls()
            cmd_name = instance.name
            # Create subparser for this subcommand
            subparser = subparsers.add_parser(cmd_name, help=instance.description, description=instance.description)
            # Let subcommand add its own arguments
            instance.configure_parser(subparser)
            # Store class for dispatch
            self._subcommand_map[cmd_name] = cls

    async def execute(self, args: Namespace) -> int:
        subcmd_name = getattr(args, 'plugin_subcommand', None)
        if not subcmd_name:
            print("Error: plugin subcommand required", file=sys.stderr)
            parser = ArgumentParser()
            parser.print_help()
            return 1

        cls = self._subcommand_map.get(subcmd_name)
        if not cls:
            print(f"Error: unknown subcommand '{subcmd_name}'", file=sys.stderr)
            return 1

        # Instantiate and execute the subcommand
        subcmd = cls()
        return await subcmd.execute(args)
