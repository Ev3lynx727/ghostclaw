"""Unit tests for cache fingerprint inclusion of orchestrator parameters."""

import pytest
from ghostclaw.core.analyzer import CodebaseAnalyzer
from ghostclaw.core.config import GhostclawConfig


class CacheSpy:
    def __init__(self):
        self.fingerprint_seen = None
    def get(self, fingerprint):
        return None
    def set(self, fingerprint, report):
        self.fingerprint_seen = fingerprint


@pytest.fixture
def minimal_repo(tmp_path):
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
    async def fake_sha(*args, **kwargs):
        return "deadbeef"
    monkeypatch.setattr(
        "ghostclaw.core.analyzer.git_utils.get_current_sha_async", fake_sha
    )


@pytest.mark.asyncio
async def test_fingerprint_differs_when_orchestrate_becomes_true(minimal_repo):
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