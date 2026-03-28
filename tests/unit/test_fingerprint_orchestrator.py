"""Unit tests for cache fingerprint inclusion of orchestrator parameters."""

import pytest
from ghostclaw.core.analyzer import CodebaseAnalyzer
from ghostclaw.core.config import GhostclawConfig


class CacheSpy:
    def __init__(self):
        """
        Initialize the CacheSpy instance and its observed fingerprint state.
        
        fingerprint_seen is set to None and will be updated to the last fingerprint passed to set().
        """
        self.fingerprint_seen = None
    def get(self, fingerprint):
        """
        Indicates that the cache has no stored value for the given fingerprint.
        
        Parameters:
            fingerprint: The cache fingerprint/key to query.
        
        Returns:
            None: No cached report is available for the provided fingerprint.
        """
        return None
    def set(self, fingerprint, report):
        """
        Record the cache fingerprint observed when storing a report.
        
        Parameters:
        	fingerprint: The cache fingerprint/key passed to the cache.
        	report: The analysis report associated with the fingerprint (accepted for interface compatibility; not stored).
        """
        self.fingerprint_seen = fingerprint


@pytest.fixture
def minimal_repo(tmp_path):
    """
    Create a temporary repository directory containing a single main.py file with a print statement.
    
    Returns:
        pathlib.Path: Path to the created repository directory.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("print('hello')\n")
    return repo


@pytest.fixture(autouse=True)
def isolate_home(monkeypatch, tmp_path):
    """Force HOME to a temporary directory to avoid picking up real global config."""
    monkeypatch.setenv("HOME", str(tmp_path))


@pytest.fixture(autouse=True)
def patch_git_sha(monkeypatch):
    """
    Patch the git SHA retrieval to a deterministic fixed value for tests.
    
    Replaces `ghostclaw.core.analyzer.git_utils.get_current_sha_async` with an async stub that always returns the string "deadbeef", ensuring deterministic fingerprint generation in tests.
    """
    async def fake_sha(*args, **kwargs):
        return "deadbeef"
    monkeypatch.setattr(
        "ghostclaw.core.analyzer.git_utils.get_current_sha_async", fake_sha
    )


@pytest.mark.asyncio
async def test_fingerprint_differs_when_orchestrate_becomes_true(minimal_repo):
    """
    Verifies that toggling the top-level `orchestrate` flag produces different cache fingerprints for the analyzer.
    
    Runs two analyses on the same repository—one with `orchestrate=False` and one with `orchestrate=True`—and asserts each run produced a non-`None` fingerprint and that the two fingerprints are different.
    """
    spy1 = CacheSpy()
    analyzer1 = CodebaseAnalyzer(cache=spy1)
    cfg1 = GhostclawConfig.load(str(minimal_repo), orchestrate=False, use_qmd=False)
    await analyzer1.analyze(str(minimal_repo), use_cache=True, config=cfg1)
    fp1 = spy1.fingerprint_seen
    assert fp1 is not None

    spy2 = CacheSpy()
    analyzer2 = CodebaseAnalyzer(cache=spy2)
    cfg2 = GhostclawConfig.load(str(minimal_repo), orchestrate=True, use_qmd=False)
    await analyzer2.analyze(str(minimal_repo), use_cache=True, config=cfg2)
    fp2 = spy2.fingerprint_seen
    assert fp2 is not None

    assert fp1 != fp2


@pytest.mark.asyncio
async def test_fingerprint_same_for_same_config(minimal_repo):
    """
    Verify that the analyzer produces the same cache fingerprint when run twice with equivalent configuration.
    
    Runs two separate analyses on a minimal repository using identical GhostclawConfig (orchestrate=False) and asserts each run produced a non-None fingerprint and that both fingerprints are equal.
    
    Parameters:
        minimal_repo (pathlib.Path): Path to the temporary repository created by the fixture.
    """
    spy1 = CacheSpy()
    analyzer1 = CodebaseAnalyzer(cache=spy1)
    cfg1 = GhostclawConfig.load(str(minimal_repo), orchestrate=False)
    await analyzer1.analyze(str(minimal_repo), use_cache=True, config=cfg1)
    fp1 = spy1.fingerprint_seen
    assert fp1 is not None

    spy2 = CacheSpy()
    analyzer2 = CodebaseAnalyzer(cache=spy2)
    cfg2 = GhostclawConfig.load(str(minimal_repo), orchestrate=False)
    await analyzer2.analyze(str(minimal_repo), use_cache=True, config=cfg2)
    fp2 = spy2.fingerprint_seen
    assert fp2 is not None

    assert fp1 == fp2


@pytest.mark.asyncio
async def test_fingerprint_changes_with_max_plugins(minimal_repo):
    spy1 = CacheSpy()
    analyzer1 = CodebaseAnalyzer(cache=spy1)
    cfg1 = GhostclawConfig.load(
        str(minimal_repo), orchestrate=True, orchestrator={"max_plugins": 5}
    )
    await analyzer1.analyze(str(minimal_repo), use_cache=True, config=cfg1)
    fp1 = spy1.fingerprint_seen
    assert fp1 is not None

    spy2 = CacheSpy()
    analyzer2 = CodebaseAnalyzer(cache=spy2)
    cfg2 = GhostclawConfig.load(
        str(minimal_repo), orchestrate=True, orchestrator={"max_plugins": 10}
    )
    await analyzer2.analyze(str(minimal_repo), use_cache=True, config=cfg2)
    fp2 = spy2.fingerprint_seen
    assert fp2 is not None

    assert fp1 != fp2


@pytest.mark.asyncio
async def test_fingerprint_changes_with_plugins_enabled(minimal_repo):
    """
    Verifies that the analyzer's cache fingerprint changes when the enabled plugins list differs.
    
    Runs two analyses on the same repository with different GhostclawConfig.plugins_enabled values, asserts each produced a non-None fingerprint, and asserts the two fingerprints are different.
    """
    spy1 = CacheSpy()
    analyzer1 = CodebaseAnalyzer(cache=spy1)
    cfg1 = GhostclawConfig.load(str(minimal_repo), plugins_enabled=["lizard"])
    await analyzer1.analyze(str(minimal_repo), use_cache=True, config=cfg1)
    fp1 = spy1.fingerprint_seen
    assert fp1 is not None

    spy2 = CacheSpy()
    analyzer2 = CodebaseAnalyzer(cache=spy2)
    cfg2 = GhostclawConfig.load(str(minimal_repo), plugins_enabled=["lizard", "pyscn"])
    await analyzer2.analyze(str(minimal_repo), use_cache=True, config=cfg2)
    fp2 = spy2.fingerprint_seen
    assert fp2 is not None

    assert fp1 != fp2


@pytest.mark.asyncio
async def test_fingerprint_changes_with_plan_cache(minimal_repo):
    spy1 = CacheSpy()
    analyzer1 = CodebaseAnalyzer(cache=spy1)
    cfg1 = GhostclawConfig.load(str(minimal_repo), orchestrate=True)  # default False
    await analyzer1.analyze(str(minimal_repo), use_cache=True, config=cfg1)
    fp1 = spy1.fingerprint_seen
    assert fp1 is not None

    spy2 = CacheSpy()
    analyzer2 = CodebaseAnalyzer(cache=spy2)
    cfg2 = GhostclawConfig.load(
        str(minimal_repo), orchestrate=True, orchestrator={"enable_plan_cache": True}
    )
    await analyzer2.analyze(str(minimal_repo), use_cache=True, config=cfg2)
    fp2 = spy2.fingerprint_seen
    assert fp2 is not None

    assert fp1 != fp2, f"Fingerprints should differ: {fp1} vs {fp2}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])