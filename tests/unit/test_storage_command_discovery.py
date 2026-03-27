"""Test auto-discovery of storage management commands."""

import sys
from pathlib import Path
from ghostclaw.cli.commander import registry

def test_storage_commands_autodiscovered():
    """Ensure storage-list and storage-migrate are discovered by the command registry."""
    # Clear registry state if needed (registry is a singleton, but tests may have polluted it)
    # We'll just check that after auto_discover, our commands are present.
    registry.auto_discover()
    command_names = [cmd.name for cmd in registry.all()]
    assert "storage-list" in command_names, "storage-list command not discovered"
    assert "storage-migrate" in command_names, "storage-migrate command not discovered"

if __name__ == "__main__":
    test_storage_commands_autodiscovered()
    print("✅ Storage commands discovered:", [cmd.name for cmd in registry.all() if cmd.name.startswith("storage")])
