"""Unit tests for SupabaseStorageAdapter."""

import pytest
from unittest.mock import patch, MagicMock
from ghostclaw.core.adapters.storage.supabase import SupabaseStorageAdapter


@pytest.fixture
def adapter():
    return SupabaseStorageAdapter()


def test_supabase_adapter_metadata(adapter):
    meta = adapter.ghost_get_metadata()
    assert meta["name"] == "supabase"
    assert "supabase" in meta["description"].lower()
    assert "supabase" in meta["dependencies"]


@pytest.mark.asyncio
async def test_supabase_adapter_availability_without_lib(adapter):
    # Simulate supabase not installed
    with patch('ghostclaw.core.adapters.storage.supabase.HAS_SUPABASE', False):
        avail = await adapter.is_available()
        assert avail is False


@pytest.mark.asyncio
async def test_supabase_adapter_availability_with_lib(adapter):
    # Simulate supabase installed but no credentials
    with patch('ghostclaw.core.adapters.storage.supabase.HAS_SUPABASE', True):
        avail = await adapter.is_available()
        # Even if lib is available, _ensure_client may return None if no creds
        # is_available only checks library presence, not credentials
        assert avail is True


@pytest.mark.asyncio
async def test_supabase_save_report_missing_credentials(adapter):
    # No environment variables set, should raise RuntimeError
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(RuntimeError, match="Supabase client not available"):
            await adapter.save_report({"vibe_score": 100})


@pytest.mark.asyncio
async def test_supabase_save_report_success(adapter):
    report = {
        "vibe_score": 95,
        "stack": "python",
        "files_analyzed": 5,
        "total_lines": 500,
        "repo_path": "/test/repo",
        "metadata": {
            "vcs": {"commit": "abc123", "branch": "main", "dirty": False}
        },
    }

    # Mock environment and supabase client
    mock_client = MagicMock()
    mock_insert_res = MagicMock()
    mock_insert_res.data = [{"id": 42}]
    mock_client.table.return_value.insert.return_value.execute.return_value = mock_insert_res

    with patch.dict('os.environ', {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "testkey"}):
        with patch('ghostclaw.core.adapters.storage.supabase.create_client', return_value=mock_client):
            # Also patch asyncio.to_thread to run synchronously in test
            async def mock_to_thread(func):
                return func()
            with patch('asyncio.to_thread', side_effect=mock_to_thread):
                report_id = await adapter.save_report(report)
                assert report_id == "42"
                mock_client.table.assert_called_with("reports")
                mock_client.table.return_value.insert.assert_called_once()
                # Verify row content
                call_args = mock_client.table.return_value.insert.call_args[0][0]
                assert call_args["vibe_score"] == 95
                assert call_args["stack"] == "python"
                assert call_args["report_json"] == report


@pytest.mark.asyncio
async def test_supabase_get_history_success(adapter):
    # Mock environment and supabase client
    mock_client = MagicMock()
    mock_select_res = MagicMock()
    mock_select_res.data = [
        {
            "id": 1,
            "vibe_score": 80,
            "stack": "go",
            "timestamp": "2025-01-01T00:00:00Z",
            "report_json": {"vibe_score": 80},
        },
        {
            "id": 2,
            "vibe_score": 90,
            "stack": "rust",
            "timestamp": "2025-01-02T00:00:00Z",
            "report_json": {"vibe_score": 90},
        },
    ]
    mock_client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_select_res

    with patch.dict('os.environ', {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "testkey"}):
        with patch('ghostclaw.core.adapters.storage.supabase.create_client', return_value=mock_client):
            async def mock_to_thread(func):
                return func()
            with patch('asyncio.to_thread', side_effect=mock_to_thread):
                history = await adapter.get_history(limit=2)
                assert len(history) == 2
                assert history[0]["id"] == 1
                assert history[1]["vibe_score"] == 90
                mock_client.table.assert_called_with("reports")
                mock_client.table.return_value.select.assert_called_with("*")
