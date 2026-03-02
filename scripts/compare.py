#!/usr/bin/env python3
"""
Ghostclaw Compare — command-line interface for comparing vibe scores.
"""

import sys
from pathlib import Path

# Ensure skill directory is in sys.path
sys.path.append(str(Path(__file__).parent.parent / "skill" / "ghostclaw"))

from cli.compare import main

if __name__ == "__main__":
    main()
