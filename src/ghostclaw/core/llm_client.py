import json
import logging
from typing import AsyncGenerator
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ghostclaw.core.config import GhostclawConfig

# Setup logger for the file
logger = logging.getLogger("ghostclaw.llm_client")

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False


class TokenBudgetExceededError(Exception):
    pass


class LLMClient:
    """Wrapper for connecting to LLM providers (e.g. OpenRouter)."""

    def __init__(self, config: GhostclawConfig, repo_path: str):
        self.config = config
        self.repo_path = repo_path
        self.max_tokens = 100000  # Default sensible limit

        if self.config.ai_provider == "openrouter":
            self.base_url = "https://openrouter.ai/api/v1/chat/completions"
            self.model = "anthropic/claude-3.5-sonnet"
        elif self.config.ai_provider == "openai":
            self.base_url = "https://api.openai.com/v1/chat/completions"
            self.model = "gpt-4o"
        elif self.config.ai_provider == "anthropic":
            self.base_url = "https://api.anthropic.com/v1/messages"
            self.model = "claude-3-5-sonnet-20241022"
        else:
            # Default to OpenRouter as fallback
            self.base_url = "https://openrouter.ai/api/v1/chat/completions"
            self.model = "anthropic/claude-3.5-sonnet"

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for a given text."""
        if HAS_TIKTOKEN:
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
            except Exception:
                return len(text) // 4
        return len(text) // 4

    def _check_token_budget(self, prompt: str) -> str:
        """Check if prompt fits in budget; throw error or truncate if not."""
        token_count = self._estimate_tokens(prompt)

        # If dry run, just print and return
        if self.config.dry_run:
            print(f"[DRY RUN] Token budget check: Estimated {token_count} tokens.")
            print(f"[DRY RUN] Payload snippet:\n{prompt[:500]}...\n")
            return prompt

        if token_count > self.max_tokens:
            raise TokenBudgetExceededError(
                f"Prompt token count ({token_count}) exceeds the maximum allowed ({self.max_tokens}). "
                "Consider analyzing a smaller subset of the codebase or disabling AST graphs."
            )
        return prompt

    def _log_verbose(self, payload: dict, response_data: dict = None, error: str = None):
        """Log API requests and responses if verbose mode is enabled."""
        if not self.config.verbose:
            return

        debug_log_path = Path(self.repo_path) / ".ghostclaw" / "debug.log"
        debug_log_path.parent.mkdir(parents=True, exist_ok=True)

        log_entry = {"request": payload}
        if response_data:
            log_entry["response"] = response_data
        if error:
            log_entry["error"] = error

        try:
            with open(debug_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, indent=2) + "\n\n")
        except Exception as e:
            logger.error(f"Failed to write verbose log: {e}")

    def _get_headers(self) -> dict:
        if self.config.ai_provider == "anthropic":
            return {
                "x-api-key": self.config.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
        else:
            return {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/Ev3lynx727/ghostclaw",
                "X-Title": "Ghostclaw Architecture Engine"
            }

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError))
    )
    async def _make_api_call(self, payload: dict) -> dict:
        """Make the actual REST API call with retries for 429/50x errors."""
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                json=payload
            )

            # Raise exception for 4xx/5xx errors to trigger retry (if applicable)
            response.raise_for_status()

            return response.json()

    async def generate_analysis(self, prompt: str) -> str:
        """Generate analysis from the LLM based on the built prompt."""
        prompt = self._check_token_budget(prompt)

        if self.config.dry_run:
            return "Dry run enabled. API call skipped."

        if not self.config.api_key:
            raise ValueError("API key not provided. Set GHOSTCLAW_API_KEY environment variable.")

        if self.config.ai_provider == "anthropic":
            payload = {
                "model": self.model,
                "max_tokens": 4096,
                "system": "You are Ghostclaw, an expert software architect. Analyze the provided codebase metrics and context, and output a markdown report detailing system-level flow, cohesion, and tech stack best practices.",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        else:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are Ghostclaw, an expert software architect. Analyze the provided codebase metrics and context, and output a markdown report detailing system-level flow, cohesion, and tech stack best practices."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

        try:
            response_data = await self._make_api_call(payload)
            self._log_verbose(payload, response_data=response_data)

            if self.config.ai_provider == "anthropic":
                if "content" in response_data and len(response_data["content"]) > 0:
                    return response_data["content"][0].get("text", "Error: No content returned from model.")
                else:
                    raise ValueError(f"Unexpected response format: {json.dumps(response_data)}")
            else:
                # Extract content based on standard OpenAI-like schema
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    message = response_data["choices"][0].get("message", {})
                    return message.get("content", "Error: No content returned from model.")
                else:
                    raise ValueError(f"Unexpected response format: {json.dumps(response_data)}")

        except Exception as e:
            self._log_verbose(payload, error=str(e))
            raise e

    async def stream_analysis(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream analysis from the LLM based on the built prompt."""
        prompt = self._check_token_budget(prompt)

        if self.config.dry_run:
            yield "Dry run enabled. API call skipped."
            return

        if not self.config.api_key:
            raise ValueError("API key not provided. Set GHOSTCLAW_API_KEY environment variable.")

        if self.config.ai_provider == "anthropic":
            payload = {
                "model": self.model,
                "max_tokens": 4096,
                "system": "You are Ghostclaw, an expert software architect. Analyze the provided codebase metrics and context, and output a markdown report detailing system-level flow, cohesion, and tech stack best practices.",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": True
            }
        else:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are Ghostclaw, an expert software architect. Analyze the provided codebase metrics and context, and output a markdown report detailing system-level flow, cohesion, and tech stack best practices."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": True
            }

        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", self.base_url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                if self.config.ai_provider == "anthropic":
                                    if chunk.get("type") == "content_block_delta":
                                        delta = chunk.get("delta", {})
                                        if delta.get("type") == "text_delta":
                                            yield delta.get("text", "")
                                else:
                                    if "choices" in chunk and len(chunk["choices"]) > 0:
                                        delta = chunk["choices"][0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            yield content
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            self._log_verbose(payload, error=str(e))
            raise e