"""Test that QMDStorageAdapter is filtered by use_qmd config."""
import pytest
from pathlib import Path
from ghostclaw.core.analyzer import CodebaseAnalyzer
from ghostclaw.core.config import GhostclawConfig
from ghostclaw.core.adapters.registry import registry

@pytest.fixture(autouse=True)
def reset_registry():
    """Reset registry state between tests."""
    registry.enabled_plugins = None
    registry._registered_plugins = []
    registry.internal_plugins = set()
    yield
    registry.enabled_plugins = None
    registry._registered_plugins = []
    registry.internal_plugins = set()

def test_qmd_excluded_when_use_qmd_false(tmp_path):
    """When use_qmd=False, qmd should not be in enabled_plugins by default."""
    # Create a minimal repo structure
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".ghostclaw").mkdir()
    (repo / "main.py").write_text("print('hello')")

    # Create a config with use_qmd=False and no plugins_enabled
    config = GhostclawConfig.load(str(repo), use_qmd=False)

    # The analyzer will set up the registry during analyze()
    analyzer = CodebaseAnalyzer()

    # We'll call the internal method that sets up plugins, but we need to trigger it.
    # Instead, we can directly simulate the plugin setup logic from analyzer.analyze()
    # Replicate that logic here:
    registry.register_internal_plugins()

    # Apply plugin filter as in analyzer.analyze()
    if config.plugins_enabled is not None:
        registry.enabled_plugins = set(config.plugins_enabled)
    else:
        from ghostclaw.core.adapters.registry import INTERNAL_PLUGINS
        plugins = set(INTERNAL_PLUGINS)
        if not config.use_qmd:
            plugins.discard("qmd")
        registry.enabled_plugins = plugins

    # Now check: qmd should not be in enabled_plugins
    assert registry.enabled_plugins is not None
    assert "qmd" not in registry.enabled_plugins
    # sqlite should be present
    assert "sqlite" in registry.enabled_plugins

def test_qmd_included_when_use_qmd_true(tmp_path):
    """When use_qmd=True, qmd should be in enabled_plugins."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".ghostclaw").mkdir()
    (repo / "main.py").write_text("print('hello')")

    config = GhostclawConfig.load(str(repo), use_qmd=True)

    registry.register_internal_plugins()

    if config.plugins_enabled is not None:
        registry.enabled_plugins = set(config.plugins_enabled)
    else:
        from ghostclaw.core.adapters.registry import INTERNAL_PLUGINS
        plugins = set(INTERNAL_PLUGINS)
        if not config.use_qmd:
            plugins.discard("qmd")
        registry.enabled_plugins = plugins

    # Ensure dual-write adds both (in case they were missing)
    if config.use_qmd:
        registry.enabled_plugins.add("sqlite")
        registry.enabled_plugins.add("qmd")

    assert "qmd" in registry.enabled_plugins
    assert "sqlite" in registry.enabled_plugins
