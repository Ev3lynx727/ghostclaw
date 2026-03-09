from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseFormatter(ABC):
    """
    Base interface for formatting architecture reports.
    """

    @abstractmethod
    def format(self, report: Dict[str, Any]) -> str:
        """
        Format the given report dictionary into a string.

        Args:
            report (Dict[str, Any]): The report data.

        Returns:
            str: The formatted output.
        """
        pass
