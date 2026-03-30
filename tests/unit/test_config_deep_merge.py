"""Unit tests for GhostclawConfig deep-merge of nested dict overrides."""

import pytest
from ghostclaw.core.config import GhostclawConfig, OrchestratorConfig


class TestDeepMergeNestedConfig:
    """Ensure partial overrides merge with existing config instead of replacing entire nested objects."""

    def test_orchestrator_partial_override_preserves_defaults(self):
        """Providing only use_llm in orchestrator dict should keep other defaults intact."""
        config = GhostclawConfig.load(
            ".",
            orchestrator={"use_llm": True}
        )
        assert isinstance(config.orchestrator, OrchestratorConfig)
        assert config.orchestrator.use_llm is True
        assert config.orchestrator.enabled is False
        # Use actual default from codebase
        assert config.orchestrator.llm_model == "openrouter/anthropic/claude-3-sonnet"
        assert config.orchestrator.vector_weight == 0.7
        assert config.orchestrator.max_plugins == 8

    def test_orchestrator_multiple_overrides_merge_correctly(self):
        """Multiple partial fields should merge, preserving unspecified defaults."""
        config = GhostclawConfig.load(
            ".",
            orchestrator={
                "use_llm": True,
                "max_plugins": 5,
                "plugin_history_lookback": 30,
            }
        )
        orch = config.orchestrator
        assert isinstance(orch, OrchestratorConfig)
        assert orch.use_llm is True
        assert orch.max_plugins == 5
        assert orch.plugin_history_lookback == 30
        assert orch.enabled is False
        assert orch.vector_weight == 0.7
        assert orch.heuristics_weight == 0.3
        assert orch.plan_cache_ttl_hours == 24

    def test_orchestrator_override_does_not_affect_other_top_level_fields(self):
        """Overriding orchestrator should not modify unrelated top-level config fields."""
        config = GhostclawConfig.load(
            ".",
            use_ai=True,
            ai_provider="anthropic",
            orchestrator={"use_llm": True}
        )
        assert config.use_ai is True
        assert config.ai_provider == "anthropic"
        assert config.orchestrator.use_llm is True
        assert config.orchestrator is not None

    def test_nested_dict_override_merges_with_existing_dict_from_file(self, tmp_path, monkeypatch):
        """Deep-merge should work even when a base orchestrator dict exists in local config."""
        import json

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        gc_dir = tmp_path / ".ghostclaw"
        gc_dir.mkdir()
        # Valid base config: weights must sum to 1.0. Keep default vector_weight=0.7 and set heuristics_weight=0.3.
        local_cfg = {
            "orchestrator": {
                "enabled": True,
                "use_llm": False,
                "max_plugins": 10,
                "vector_weight": 0.7,
                "heuristics_weight": 0.3,
            }
        }
        (gc_dir / "ghostclaw.json").write_text(json.dumps(local_cfg))

        # Override only use_llm
        config = GhostclawConfig.load(
            str(tmp_path),
            orchestrator={"use_llm": True}
        )
        orch = config.orchestrator
        assert orch.enabled is True
        assert orch.use_llm is True
        assert orch.max_plugins == 10
        assert orch.vector_weight == 0.7
        assert orch.heuristics_weight == 0.3
        # Other defaults preserved
        assert orch.plan_cache_ttl_hours == 24

    def test_supabase_partial_override_preserves_other_fields(self):
        """Providing a dict with one field yields a fully populated model."""
        config = GhostclawConfig.load(
            ".",
            orchestrator={"use_llm": True, "cache_dir": "/custom/cache"}
        )
        orch = config.orchestrator
        assert orch.use_llm is True
        assert orch.cache_dir == "/custom/cache"
        assert orch.enabled is False
        assert orch.max_plugins == 8

    def test_orchestrator_empty_dict_creates_default_config(self):
        """
        Ensure that passing an empty `orchestrator` dict with `orchestrate=False` produces a default OrchestratorConfig.
        
        Verifies the orchestrator is created and has default field values: `enabled` is disabled, `use_llm` is disabled, and `max_plugins` equals 8.
        """
        config = GhostclawConfig.load(".", orchestrate=False, orchestrator={})
        assert config.orchestrator is not None
        assert isinstance(config.orchestrator, OrchestratorConfig)
        assert config.orchestrator.enabled is False
        assert config.orchestrator.use_llm is False
        assert config.orchestrator.max_plugins == 8

    def test_orchestrator_none_when_orchestrate_false_no_explicit_dict(self):
        """If orchestrate=False and no explicit orchestrator, orchestrator should be None."""
        config = GhostclawConfig.load(".", orchestrate=False)
        assert config.orchestrator is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])