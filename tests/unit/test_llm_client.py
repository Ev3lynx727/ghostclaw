import pytest
import httpx
from unittest.mock import AsyncMock, patch
from ghostclaw.core.config import GhostclawConfig
from ghostclaw.core.llm_client import LLMClient, TokenBudgetExceededError

@pytest.fixture
def config():
    return GhostclawConfig(api_key="test-key", use_ai=True, ai_provider="openrouter")

@pytest.mark.asyncio
async def test_generate_analysis_dry_run():
    config = GhostclawConfig(dry_run=True, use_ai=True)
    client = LLMClient(config, ".")
    result = await client.generate_analysis("test prompt")
    assert result == "Dry run enabled. API call skipped."

@pytest.mark.asyncio
async def test_generate_analysis_missing_api_key():
    config = GhostclawConfig(api_key=None, use_ai=True)
    client = LLMClient(config, ".")
    with pytest.raises(ValueError, match="API key not provided"):
        await client.generate_analysis("test prompt")

def test_token_budget_exceeded(config):
    client = LLMClient(config, ".")
    client.max_tokens = 10  # Artificial limit
    with pytest.raises(TokenBudgetExceededError):
        client._check_token_budget("This is a very long prompt that will exceed the artificial ten token budget")

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_generate_analysis_success(mock_post, config):
    # Mock the return value of response.json() directly instead of making the mock method async itself
    mock_response = AsyncMock()
    mock_response.json = lambda: {
        "choices": [{"message": {"content": "Test synthesis"}}]
    }
    mock_response.raise_for_status = lambda: None
    mock_post.return_value = mock_response

    client = LLMClient(config, ".")
    result = await client.generate_analysis("Analyze this codebase")

    assert result == "Test synthesis"
    mock_post.assert_called_once()
