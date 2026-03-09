"""
Config Service — Handles project configuration initialization.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigService:
    """Service for managing ghostclaw project configuration."""

    DEFAULT_TEMPLATE: Dict[str, Any] = {
        "use_ai": True,
        "ai_provider": "openrouter",
        "ai_model": None,
        "use_pyscn": False,
        "use_ai_codeindex": False
    }

    @classmethod
    def init_project(
        cls,
        project_path: str | Path,
        template: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Initialize a project with a .ghostclaw/ghostclaw.json config.

        Args:
            project_path: Path to the project root
            template: Optional custom template (uses DEFAULT_TEMPLATE if None)

        Returns:
            Path to the created config file

        Raises:
            FileExistsError: If config already exists
        """
        project_root = Path(project_path).resolve()
        gc_dir = project_root / ".ghostclaw"
        config_file = gc_dir / "ghostclaw.json"

        if config_file.exists():
            raise FileExistsError(f"Config already exists at {config_file}")

        # Create directory
        gc_dir.mkdir(parents=True, exist_ok=True)

        # Use provided template or default
        config_data = template or cls.DEFAULT_TEMPLATE.copy()

        # Write config
        config_file.write_text(json.dumps(config_data, indent=2), encoding='utf-8')

        print(f"✅ Created template config at {config_file}")
        print("💡 Remember: Do NOT save your GHOSTCLAW_API_KEY in this file. Use an environment variable or ~/.ghostclaw/ghostclaw.json.")

        return config_file

    @classmethod
    def load_project_config(
        cls,
        project_path: str | Path
    ) -> Optional[Dict[str, Any]]:
        """
        Load the project's ghostclaw.json config if it exists.

        Args:
            project_path: Path to the project root

        Returns:
            Config dict or None if no config exists
        """
        config_file = Path(project_path) / ".ghostclaw" / "ghostclaw.json"
        if config_file.exists():
            return json.loads(config_file.read_text(encoding='utf-8'))
        return None
