import json
from pathlib import Path
from typing import Dict, Any

class ConfigService:
    """
    Service for initializing Ghostclaw project configuration.
    """

    @staticmethod
    def init_project(path: str = ".") -> None:
        """
        Scaffold local project configuration.

        Args:
            path (str): The directory where the .ghostclaw config should be created.
        """
        cwd = Path(path)
        gc_dir = cwd / ".ghostclaw"
        gc_dir.mkdir(parents=True, exist_ok=True)
        config_file = gc_dir / "ghostclaw.json"

        if config_file.exists():
            raise FileExistsError(f"⚠️ {config_file} already exists. Skipping initialization.")

        template = {
            "use_ai": True,
            "ai_provider": "openrouter",
            "ai_model": None,
            "use_pyscn": False,
            "use_ai_codeindex": False
        }

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=2)

        print(f"✅ Created template config at {config_file}")
        print("💡 Remember: Do NOT save your GHOSTCLAW_API_KEY in this file. Use an environment variable or ~/.ghostclaw/ghostclaw.json.")
