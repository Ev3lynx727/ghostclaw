from abc import ABC
from ghostclaw.cli.commander import Command

class PluginsCommand(Command, ABC):
    """
    Base class for plugin subcommands.
    Subclasses will NOT be auto-registered as top-level commands.
    """
    _auto_register = False
    # No __init__ here; subclasses create their own service
