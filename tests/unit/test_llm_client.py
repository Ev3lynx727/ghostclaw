import pytest
from unittest.mock import AsyncMock, patch, MagicMock
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
    assert result == {"content": "Dry run enabled. API call skipped."}

@pytest.mark.asyncio
async def test_generate_analysis_missing_api_key():
    # Mock SDKs so LLMClient can be instantiated without a valid key
    with patch("ghostclaw.core.llm_client.AsyncOpenAI"), \
         patch("ghostclaw.core.llm_client.AsyncAnthropic"):
        config = GhostclawConfig(api_key=None, use_ai=True, ai_provider="openrouter")
        client = LLMClient(config, ".")
        with pytest.raises(ValueError, match="API key not provided"):
            await client.generate_analysis("test prompt")

def test_token_budget_exceeded(config):
    client = LLMClient(config, ".")
    client.max_tokens = 10  # Artificial limit
    with pytest.raises(TokenBudgetExceededError):
        client._check_token_budget("This is a very long prompt that will exceed the artificial ten token budget")

@pytest.mark.asyncio
async def test_generate_analysis_success(config):
    # Mock AsyncOpenAI
    with patch("ghostclaw.core.llm_client.AsyncOpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        
        # Mock the completions.create call
        mock_message = MagicMock()
        mock_message.content = "Test synthesis"
        # Ensure reasoning_content is NOT present (simulating normal model)
        del mock_message.reasoning_content
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message = mock_message
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        client = LLMClient(config, ".")
        result = await client.generate_analysis("Analyze this codebase")

        assert result == {"content": "Test synthesis", "reasoning": None}

@pytest.mark.asyncio
async def test_generate_analysis_with_reasoning(config):
    with patch("ghostclaw.core.llm_client.AsyncOpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        
        mock_message = MagicMock()
        mock_message.content = "Test synthesis"
        mock_message.reasoning_content = "Thinking hard..."
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message = mock_message
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        client = LLMClient(config, ".")
        result = await client.generate_analysis("Analyze this codebase")

        assert result == {"content": "Test synthesis", "reasoning": "Thinking hard..."}

@pytest.mark.asyncio
async def test_test_connection_success(config):
    with patch("ghostclaw.core.llm_client.AsyncOpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.models.list = AsyncMock(return_value=MagicMock())
        
        client = LLMClient(config, ".")
        result = await client.test_connection()
        assert result is True

@pytest.mark.asyncio
async def test_list_models(config):
    with patch("ghostclaw.core.llm_client.AsyncOpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        
        mock_model_1 = MagicMock()
        mock_model_1.id = "model-1"
        mock_model_2 = MagicMock()
        mock_model_2.id = "model-2"
        
        mock_response = MagicMock()
        mock_response.data = [mock_model_1, mock_model_2]
        mock_client.models.list = AsyncMock(return_value=mock_response)
        
        client = LLMClient(config, ".")
        models = await client.list_models()
        assert models == ["model-1", "model-2"]
