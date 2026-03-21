"""Tests for orchestrator CLI flags parsing and overrides."""

import pytest
from argparse import Namespace
from ghostclaw.cli.commands.analyze import AnalyzeCommand


class TestOrchestrateCLI:
    """Test that --orchestrate and --no-orchestrate flags are converted to config overrides."""

    def test_orchestrate_flag_sets_override(self):
        """--orchestrate should result in overrides['orchestrate']=True."""
        cmd = AnalyzeCommand()
        args = Namespace(
            orchestrate=True,
            no_orchestrate=False,
            use_ai=None, no_ai=None, ai_provider=None, ai_model=None,
            dry_run=None, verbose=None, patch=None, delta=None, delta_base_ref=None,
            use_qmd=None, embedding_backend=None,
            pyscn=None, no_pyscn=None, ai_codeindex=None, no_ai_codeindex=None,
            no_parallel=None, concurrency_limit=None
        )
        overrides = cmd._build_cli_overrides(args)
        assert overrides.get("orchestrate") is True

    def test_no_orchestrate_flag_sets_override_false(self):
        """--no-orchestrate should result in overrides['orchestrate']=False."""
        cmd = AnalyzeCommand()
        args = Namespace(
            orchestrate=False,
            no_orchestrate=True,
            use_ai=None, no_ai=None, ai_provider=None, ai_model=None,
            dry_run=None, verbose=None, patch=None, delta=None, delta_base_ref=None,
            use_qmd=None, embedding_backend=None,
            pyscn=None, no_pyscn=None, ai_codeindex=None, no_ai_codeindex=None,
            no_parallel=None, concurrency_limit=None
        )
        overrides = cmd._build_cli_overrides(args)
        assert overrides.get("orchestrate") is False

    def test_absent_orchestrate_flag_not_in_overrides(self):
        """When neither --orchestrate nor --no-orchestrate is used, 'orchestrate' should not be in overrides."""
        cmd = AnalyzeCommand()
        args = Namespace(
            orchestrate=False,
            no_orchestrate=False,
            use_ai=None, no_ai=None, ai_provider=None, ai_model=None,
            dry_run=None, verbose=None, patch=None, delta=None, delta_base_ref=None,
            use_qmd=None, embedding_backend=None,
            pyscn=None, no_pyscn=None, ai_codeindex=None, no_ai_codeindex=None,
            no_parallel=None, concurrency_limit=None
        )
        overrides = cmd._build_cli_overrides(args)
        assert "orchestrate" not in overrides

    def test_orchestrate_flag_with_other_flags(self):
        """Orchestrate should coexist with other overrides."""
        cmd = AnalyzeCommand()
        args = Namespace(
            orchestrate=True,
            no_orchestrate=False,
            use_ai=True, no_ai=False, ai_provider=None, ai_model=None,
            dry_run=False, verbose=True, patch=False, delta=False, delta_base_ref=None,
            use_qmd=True, embedding_backend=None,
            pyscn=False, no_pyscn=False, ai_codeindex=None, no_ai_codeindex=False,
            no_parallel=False, concurrency_limit=16
        )
        overrides = cmd._build_cli_overrides(args)
        assert overrides["orchestrate"] is True
        assert overrides.get("use_ai") is True
        assert overrides.get("use_qmd") is True
        assert overrides.get("verbose") is True
        assert overrides.get("concurrency_limit") == 16
