from argparse import ArgumentParser, Namespace
from ghostclaw.cli.commands.plugins.base import PluginsCommand
from ghostclaw.cli.services.plugin_service import PluginService
import sys

class PluginsInfoCommand(PluginsCommand):
    def __init__(self):
        self.service = PluginService()
    @property
    def name(self) -> str:
        return "info"

    @property
    def description(self) -> str:
        return "Show detailed info for a plugin"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("name", help="Name of the plugin")

    async def execute(self, args: Namespace) -> int:
        meta = self.service.get_plugin_info(args.name)
        if not meta:
            print(f"❌ Plugin '{args.name}' not found.", file=sys.stderr)
            return 1

        print(f"Plugin: {meta.get('name')}")
        print(f"Version: {meta.get('version')}")
        print(f"Description: {meta.get('description')}")
        return 0
