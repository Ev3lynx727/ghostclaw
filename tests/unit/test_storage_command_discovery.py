"""Test auto-discovery of storage management commands."""

from ghostclaw.cli.commander import registry

def test_storage_commands_autodiscovered():
    """Ensure storage-list and storage-migrate are discovered by the command registry."""
    registry.auto_discover()
    command_names = list(registry._commands.keys())
    assert "storage-list" in command_names, "storage-list command not discovered"
    assert "storage-migrate" in command_names, "storage-migrate command not discovered"
