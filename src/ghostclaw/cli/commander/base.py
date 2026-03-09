from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace

class Command(ABC):
    """
    Base class for all modular CLI commands.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the command, used in the CLI argument parser."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of the command."""
        pass

    @abstractmethod
    def configure_parser(self, parser: ArgumentParser) -> None:
        """
        Configure the argparse subparser for this command.

        Args:
            parser (ArgumentParser): The subparser to configure.
        """
        pass

    @abstractmethod
    async def execute(self, args: Namespace) -> int:
        """
        Execute the command.

        Args:
            args (Namespace): The parsed arguments.

        Returns:
            int: The exit code (0 for success, non-zero for failure).
        """
        pass

    def validate(self, args: Namespace) -> None:
        """
        Validate the parsed arguments before execution.
        Raises ValueError if arguments are invalid.

        Args:
            args (Namespace): The parsed arguments.
        """
        pass
