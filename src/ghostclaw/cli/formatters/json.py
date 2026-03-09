import json
from typing import Dict, Any
from ghostclaw.cli.formatters.base import BaseFormatter

class JSONFormatter(BaseFormatter):
    """
    Format the architecture report as a JSON string.
    """

    def __init__(self, indent: int = 2):
        self.indent = indent

    def format(self, report: Dict[str, Any]) -> str:
        return json.dumps(report, indent=self.indent)
