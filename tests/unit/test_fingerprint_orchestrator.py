"""Unit tests for cache fingerprint inclusion of orchestrator parameters."""

import pytest
from unittest.mock import AsyncMock, patch
from ghostclaw.core.analyzer import CodebaseAnalyzer
from ghostclaw.core.config import GhostclawConfig


class CacheSpy:
    """Spy that captures the fingerprint passed to cache.set()."""
    def __init__(self):
        self.fingerprint_seen = None

    def get(self, fingerprint):
        return None  # Always miss to force analysis and then set

    def set(self, fingerprint, report):
        self.fingerprint_seen = fingerprint


@pytest.fixture
def minimal_repo(tmp_path):
    """Create a minimal repo with a Python file."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("print('hello')\n")
    return repo


@pytest.fixture(autouse=True)
def patch_git_sha(monkeypatch):
    """Patch get_current_sha_async to return a fixed SHA to avoid needing a real git repo."""
    async def fake_sha(*args, **kwargs):
        return "deadbeef"
    monkeypatch.setattr(
        "ghostclaw.core.analyzer.git_utils.get_current_sha_async", fake_sha
    )


@pytest.mark.asyncio
async def test_fingerprint_differs_when_orchestrate_becomes_true(minimal_repo):
    """Cache fingerprint should differ between orchestrate=False and orchestrate=True."""
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
    """Two runs with identical config should produce the same fingerprint."""
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
    """Changing orchestrator.max_plugins should produce different fingerprints."""
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
    """Different plugins_enabled lists should produce different fingerprints."""
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
async def test_fingerprint_changes_with_vector_weight(minimal_repo):
    """Changing orchestrator.vector_weight should produce different fingerprints."""
    spy1 = CacheSpy()
    analyzer1 = CodebaseAnalyzer(cache=spy1)
    cfg1 = GhostclawConfig.load(str(minimal_repo), orchestrate=True)  # default 0.7
    await analyzer1.analyze(str(minimal_repo), use_cache=True, config=cfg1)
    fp1 = spy1.fingerprint_seen
    assert fp1 is not None

    spy2 = CacheSpy()
    analyzer2 = CodebaseAnalyzer(cache=spy2)
    cfg2 = GhostclawConfig.load(
        str(minimal_repo), orchestrate=True, orchestrator={"vector_weight": 0.5}
    )
    await analyzer2.analyze(str(minimal_repo), use_cache=True, config=cfg2)
    fp2 = spy2.fingerprint_seen
    assert fp2 is not None

    assert fp1 != fp2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])