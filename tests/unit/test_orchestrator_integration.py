"""Tests for orchestrator integration (core PR-A/B/D)."""

import pytest
from pathlib import Path
from ghostclaw.core.config import GhostclawConfig
from ghostclaw.core.adapters.registry import registry, INTERNAL_PLUGINS


class TestOrchestrateConfigField:
    """Test the top-level 'orchestrate' boolean config field."""

    def test_orchestrate_default_false(self):
        """Default value of orchestrate should be False."""
        config = GhostclawConfig()
        assert config.orchestrate is False

    def test_orchestrate_cli_override_true(self):
        """CLI override can set orchestrate=True."""
        config = GhostclawConfig.load(".", orchestrate=True)
        assert config.orchestrate is True

    def test_orchestrate_cli_override_false(self):
        """CLI override can set orchestrate=False."""
        config = GhostclawConfig.load(".", orchestrate=False)
        assert config.orchestrate is False

    def test_orchestrate_env_var_true(self, monkeypatch, tmp_path):
        """Environment variable GHOSTCLAW_ORCHESTRATE can enable orchestrate."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("GHOSTCLAW_ORCHESTRATE", "true")
        config = GhostclawConfig.load(".")
        assert config.orchestrate is True

    def test_orchestrate_env_var_false(self, monkeypatch, tmp_path):
        """Environment variable GHOSTCLAW_ORCHESTRATE can disable orchestrate."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("GHOSTCLAW_ORCHESTRATE", "false")
        config = GhostclawConfig.load(".")
        assert config.orchestrate is False

    def test_orchestrate_and_orchestrator_dict_both_respected(self):
        """Both orchestrate flag and orchestrator dict can coexist; orchestrate takes precedence in enforcement."""
        config = GhostclawConfig.load(
            ".",
            orchestrate=True,
            orchestrator={"enabled": False, "use_llm": True}
        )
        assert config.orchestrate is True
        assert config.orchestrator["enabled"] is False
        assert config.orchestrator["use_llm"] is True


class TestOrchestratorEnforcement:
    """Test that analyzer enforces orchestrator-only mode when enabled."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry state between tests."""
        registry.enabled_plugins = None
        registry._registered_plugins = []
        registry.internal_plugins = set()
        registry.external_plugins = set()
        yield
        registry.enabled_plugins = None
        registry._registered_plugins = []
        registry.internal_plugins = set()
        registry.external_plugins = set()

    def _apply_plugin_filter(self, config):
        """Replicate the plugin filter logic from Analyzer.analyze()."""
        # Simulate register_internal_plugins() call: populate internal_plugins
        registry.internal_plugins = set(INTERNAL_PLUGINS)

        # Apply plugin filter
        orchestrator_enabled = config.orchestrate or (config.orchestrator and config.orchestrator.get('enabled', False))
        if orchestrator_enabled:
            registry.enabled_plugins = {'orchestrator'}
        elif config.plugins_enabled is not None:
            registry.enabled_plugins = set(config.plugins_enabled)
        elif config.use_qmd:
            registry.enabled_plugins = None  # All plugins enabled (including qmd)
        else:
            plugins = set(INTERNAL_PLUGINS) | registry.external_plugins
            plugins.discard("qmd")
            registry.enabled_plugins = plugins

        # Add storage plugins if needed
        if config.use_qmd and registry.enabled_plugins is not None:
            registry.enabled_plugins.add('sqlite')
            registry.enabled_plugins.add('qmd')

    def test_orchestrate_flag_enables_only_orchestrator_no_qmd(self):
        """With orchestrate=True and use_qmd=False, only orchestrator should be enabled."""
        config = GhostclawConfig.load(".", orchestrate=True, use_qmd=False)
        self._apply_plugin_filter(config)
        assert registry.enabled_plugins == {'orchestrator'}

    def test_orchestrate_flag_with_qmd_enables_orchestrator_and_storage(self):
        """With orchestrate=True and use_qmd=True, enabled set should contain orchestrator, sqlite, qmd."""
        config = GhostclawConfig.load(".", orchestrate=True, use_qmd=True)
        self._apply_plugin_filter(config)
        assert registry.enabled_plugins == {'orchestrator', 'sqlite', 'qmd'}

    def test_orchestrator_dict_enabled_with_qmd(self):
        """Setting orchestrator={'enabled': True} with use_qmd=True also yields orchestrator + storage."""
        config = GhostclawConfig.load(".", orchestrator={"enabled": True}, use_qmd=True)
        self._apply_plugin_filter(config)
        assert registry.enabled_plugins == {'orchestrator', 'sqlite', 'qmd'}

    def test_orchestrate_false_with_use_qmd_true_all_plugins(self):
        """Default case: orchestrate=False, use_qmd=True -> all plugins enabled (None)."""
        config = GhostclawConfig.load(".", orchestrate=False, use_qmd=True)
        self._apply_plugin_filter(config)
        assert registry.enabled_plugins is None

    def test_orchestrate_false_with_use_qmd_false_gives_standard_set(self):
        """orchestrate=False, use_qmd=False -> internal plugins except qmd."""
        config = GhostclawConfig.load(".", orchestrate=False, use_qmd=False)
        self._apply_plugin_filter(config)
        assert registry.enabled_plugins is not None
        assert 'orchestrator' not in registry.enabled_plugins
        assert 'lizard' in registry.enabled_plugins
        assert 'sqlite' in registry.enabled_plugins
        assert 'qmd' not in registry.enabled_plugins

    def test_orchestrate_overrides_plugins_enabled(self):
        """If both orchestrate=True and plugins_enabled set, orchestrate wins."""
        config = GhostclawConfig.load(
            ".",
            orchestrate=True,
            plugins_enabled=["lizard", "qmd"],
            use_qmd=False
        )
        self._apply_plugin_filter(config)
        assert registry.enabled_plugins == {'orchestrator'}

    def test_orchestrate_overrides_use_qmd_but_still_adds_storage(self):
        """When both orchestrate=True and use_qmd=True, still only orchestrator + storage."""
        config = GhostclawConfig.load(".", orchestrate=True, use_qmd=True)
        self._apply_plugin_filter(config)
        assert registry.enabled_plugins == {'orchestrator', 'sqlite', 'qmd'}

    def test_orchestrator_dict_disabled_does_not_force(self):
        """If orchestrator.enabled=False and orchestrate=False, normal rules apply (here we set use_qmd=True to avoid set test)."""
        config = GhostclawConfig.load(".", orchestrator={"enabled": False}, use_qmd=True)
        self._apply_plugin_filter(config)
        # use_qmd=True leads to None (all plugins)
        assert registry.enabled_plugins is None

    def test_orchestrator_dict_disabled_with_use_qmd_false(self):
        """orchestrator disabled and use_qmd=False yields standard set (no orchestrator)."""
        config = GhostclawConfig.load(".", orchestrator={"enabled": False}, use_qmd=False)
        self._apply_plugin_filter(config)
        assert registry.enabled_plugins is not None
        assert 'orchestrator' not in registry.enabled_plugins
        assert 'lizard' in registry.enabled_plugins


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
