"""Metric adapter for ai-codeindex symbol analysis."""

import json
from typing import Dict, List, Any, Optional
from ghostclaw.core.adapters.metric.base import AsyncProcessMetricAdapter
from ghostclaw.core.adapters.base import AdapterMetadata
from ghostclaw.core.adapters.hooks import hookimpl

class AICodeIndexAdapter(AsyncProcessMetricAdapter):
    """Wraps ai-codeindex tool into the Ghostclaw adapter interface."""

    def get_metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="ai-codeindex",
            version="0.1.0",
            description="Deep architectural analysis and symbol indexing.",
            dependencies=["ai-codeindex"]
        )

    async def is_available(self) -> bool:
        """Check if ai-codeindex binary is in the PATH."""
        result = await self.run_tool(["ai-codeindex", "--version"])
        return result.get("returncode") == 0

    @hookimpl
    async def ghost_analyze(self, root: str, files: List[str]) -> Dict[str, Any]:
        """Perform analysis using ai-codeindex."""
        return await self.analyze(root, files)

    async def analyze(self, root: str, files: List[str]) -> Dict[str, Any]:
        """Perform analysis implementation."""
        if not await self.is_available():
            return {}

        # Run ai-codeindex symbols
        result = await self.run_tool(["ai-codeindex", "symbols", "--root", root, "-o", "PROJECT_SYMBOLS.md"])
        if result.get("returncode") != 0:
            return {"issues": [f"AI-CodeIndex error: {result.get('stderr')}"]}

        # For now, it produces a file PROJECT_SYMBOLS.md.
        # In the future, we would parse it or use its JSON output if available.
        return {
            "issues": [],
            "architectural_ghosts": ["Symbols indexed and PROJECT_SYMBOLS.md updated."],
            "red_flags": []
        }

    @hookimpl
    def ghost_get_metadata(self) -> Dict[str, Any]:
        """Expose metadata to the plugin manager."""
        meta = self.get_metadata()
        return {
            "name": meta.name,
            "version": meta.version,
            "description": meta.description,
            "available": True
        }
