"""Tests for QMDMemoryStore."""
import pytest
import asyncio
import json
from pathlib import Path
from ghostclaw.core.qmd_store import QMDMemoryStore


@pytest.mark.asyncio
async def test_qmd_memory_store_init_and_save(tmp_path):
    """Test QMDMemoryStore can initialize DB and save a run."""
    db_path = tmp_path / "qmd.db"
    store = QMDMemoryStore(db_path=db_path)

    # Ensure DB doesn't exist yet
    assert not db_path.exists()

    # Create a dummy report
    report = {
        "vibe_score": 75,
        "stack": "python",
        "files_analyzed": 10,
        "total_lines": 500,
        "issues": ["Test issue"],
        "architectural_ghosts": ["Test ghost"],
        "metadata": {"timestamp": "2026-03-12T12:00:00Z"}
    }

    run_id = await store.save_run(report, repo_path=str(tmp_path))
    assert isinstance(run_id, int)
    assert db_path.exists()

    # Verify we can retrieve it
    retrieved = await store.get_run(run_id)
    assert retrieved is not None
    assert retrieved["vibe_score"] == 75
    assert retrieved["stack"] == "python"


@pytest.mark.asyncio
async def test_qmd_memory_store_list_runs(tmp_path):
    """Test listing runs from QMDMemoryStore."""
    db_path = tmp_path / "qmd.db"
    store = QMDMemoryStore(db_path=db_path)

    # Save a few runs
    for i in range(3):
        report = {
            "vibe_score": 50 + i,
            "stack": "python",
            "files_analyzed": 10,
            "total_lines": 500,
            "issues": [],
            "architectural_ghosts": [],
            "metadata": {"timestamp": f"2026-03-12T12:00:{i:02d}Z"}
        }
        await store.save_run(report, repo_path=str(tmp_path))

    runs = await store.list_runs(limit=10)
    assert len(runs) == 3
    # Should be in descending timestamp order
    vibe_scores = [r["vibe_score"] for r in runs]
    assert vibe_scores == sorted(vibe_scores, reverse=True)


@pytest.mark.asyncio
async def test_qmd_memory_store_search_basic(tmp_path):
    """Test basic search functionality (substring match)."""
    db_path = tmp_path / "qmd.db"
    store = QMDMemoryStore(db_path=db_path)

    # Save reports with specific issues
    report1 = {
        "vibe_score": 60,
        "stack": "python",
        "files_analyzed": 5,
        "total_lines": 200,
        "issues": ["Authentication bypass vulnerability"],
        "architectural_ghosts": [],
        "metadata": {"timestamp": "2026-03-12T12:00:00Z"}
    }
    report2 = {
        "vibe_score": 80,
        "stack": "node",
        "files_analyzed": 8,
        "total_lines": 300,
        "issues": ["Memory leak in event loop"],
        "architectural_ghosts": ["CallbackHell"],
        "metadata": {"timestamp": "2026-03-12T12:01:00Z"}
    }
    await store.save_run(report1, repo_path=str(tmp_path))
    await store.save_run(report2, repo_path=str(tmp_path))

    # Search for "authentication" should find report1
    results = await store.search("authentication")
    assert len(results) == 1
    assert results[0]["vibe_score"] == 60

    # Search for "callback" should find report2
    results = await store.search("callback")
    assert len(results) == 1
    assert results[0]["vibe_score"] == 80

    # Search for "memory" should find report2 (issue)
    results = await store.search("memory")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_qmd_memory_store_diff_runs(tmp_path):
    """Test diffing two runs."""
    db_path = tmp_path / "qmd.db"
    store = QMDMemoryStore(db_path=db_path)

    report_a = {
        "vibe_score": 70,
        "stack": "python",
        "files_analyzed": 10,
        "total_lines": 500,
        "issues": ["Issue A"],
        "architectural_ghosts": ["Ghost A"],
        "metadata": {"timestamp": "2026-03-12T12:00:00Z"}
    }
    report_b = {
        "vibe_score": 80,
        "stack": "python",
        "files_analyzed": 12,
        "total_lines": 600,
        "issues": ["Issue B", "Issue A"],  # Issue A persists, Issue B new
        "architectural_ghosts": [],  # Ghost A resolved
        "metadata": {"timestamp": "2026-03-12T12:10:00Z"}
    }

    id_a = await store.save_run(report_a, repo_path=str(tmp_path))
    id_b = await store.save_run(report_b, repo_path=str(tmp_path))

    diff = await store.diff_runs(id_a, id_b)
    assert diff is not None
    assert diff["vibe_score_delta"] == 10
    assert "Issue B" in diff["new_issues"]
    assert "Ghost A" in diff["resolved_ghosts"]


@pytest.mark.asyncio
async def test_qmd_memory_store_knowledge_graph(tmp_path):
    """Test knowledge graph aggregation."""
    db_path = tmp_path / "qmd.db"
    store = QMDMemoryStore(db_path=db_path)

    # Save multiple runs with recurring issues
    for i in range(3):
        report = {
            "vibe_score": 60,
            "stack": "python",
            "files_analyzed": 10,
            "total_lines": 500,
            "issues": ["Recurring issue"],
            "architectural_ghosts": ["Recurring ghost"],
            "metadata": {"timestamp": f"2026-03-12T12:00:{i:02d}Z"}
        }
        await store.save_run(report, repo_path=str(tmp_path))

    graph = await store.get_knowledge_graph(repo_path=str(tmp_path), limit=10)
    assert "nodes" in graph
    assert "edges" in graph
    # Should have nodes for the recurring issue and ghost
    node_labels = [n["label"] for n in graph["nodes"]]
    assert "Recurring issue" in node_labels
    assert "Recurring ghost" in node_labels
