import json
import logging
from pathlib import Path
from typing import AsyncGenerator, Optional
from ghostclaw.core.llm_client.providers import create_client, AsyncOpenAI, AsyncAnthropic
from ghostclaw.core.llm_client.retry import with_retry, with_retry_stream, estimate_tokens, TokenBudgetExceededError

logger = logging.getLogger("ghostclaw.llm_client")

class LLMClient:
    def __init__(self, config, repo_path: str):
        self.config = config
        self.repo_path = repo_path
        self.max_tokens = 100000
        self.client, self.model = create_client(config)
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.system_prompt = "You are Ghostclaw, an expert software architect. Analyze the provided codebase metrics and context, and output a markdown report detailing system-level flow, cohesion, and tech stack best practices."

    def _check_token_budget(self, prompt: str) -> str:
        token_count = estimate_tokens(prompt)
        if self.config.dry_run:
            print(f"[DRY RUN] Token budget check: Estimated {token_count} tokens.")
            return prompt
        if token_count > self.max_tokens:
            raise TokenBudgetExceededError(f"Prompt too long: {token_count} tokens exceeds {self.max_tokens}")
        return prompt

    def _log_verbose(self, payload: dict, response_data: dict = None, error: str = None):
        if not self.config.verbose: return
        debug_log_path = Path(self.repo_path) / ".ghostclaw" / "debug.log"
        debug_log_path.parent.mkdir(parents=True, exist_ok=True)
        log_entry = {"request": payload, "response": response_data, "error": error}
        try:
            with open(debug_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, indent=2) + "\n\n")
        except Exception as e:
            logger.error(f"Failed to write verbose log: {e}")

    async def generate_analysis(self, prompt: str) -> dict:
        prompt = self._check_token_budget(prompt)
        if self.config.dry_run:
            return {"content": "Dry run enabled. API call skipped."}
        if not self.config.api_key:
            raise ValueError("API key not provided.")

        return await with_retry(self._api_call, self.config, prompt)

    async def _api_call(self, prompt: str):
        try:
            if self.config.ai_provider == "anthropic":
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=self.system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
                reasoning = getattr(response, 'thinking', None)
                if hasattr(response, 'usage') and response.usage:
                    self.prompt_tokens += response.usage.input_tokens
                    self.completion_tokens += response.usage.output_tokens
                return {"content": content, "reasoning": reasoning}
            else:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ]
                )
                msg = response.choices[0].message
                content = msg.content
                reasoning = getattr(msg, 'reasoning_content', None)
                if hasattr(response, 'usage') and response.usage:
                    self.prompt_tokens += response.usage.prompt_tokens
                    self.completion_tokens += response.usage.completion_tokens
                return {"content": content, "reasoning": reasoning}
        except Exception as e:
            self._log_verbose({"model": self.model, "prompt_snippet": prompt[:100]}, error=str(e))
            raise e

    async def stream_analysis(self, prompt: str) -> AsyncGenerator[dict, None]:
        prompt = self._check_token_budget(prompt)
        if self.config.dry_run:
            yield {"type": "content", "content": "Dry run enabled. API call skipped."}
            return
        if not self.config.api_key:
            raise ValueError("API key not provided.")

        self.prompt_tokens = 0
        self.completion_tokens = 0

        async def _stream_call():
            if self.config.ai_provider == "anthropic":
                async with self.client.messages.stream(
                    model=self.model,
                    max_tokens=4096,
                    system=self.system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                ) as stream:
                    async for event in stream:
                        if event.type == "text_delta" and event.text is not None:
                            yield {"type": "content", "content": event.text}
                        elif event.type == "thinking_delta" and event.thinking is not None:
                            yield {"type": "reasoning", "content": event.thinking}
                    usage = stream.get_final_usage()
                    if usage:
                        self.prompt_tokens += usage.input_tokens
                        self.completion_tokens += usage.output_tokens
            else:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True
                )
                async for chunk in stream:
                    if not chunk.choices: continue
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content is not None:
                        yield {"type": "content", "content": delta.content}
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content is not None:
                        yield {"type": "reasoning", "content": delta.reasoning_content}
                    if hasattr(chunk, 'usage') and chunk.usage:
                        self.prompt_tokens += chunk.usage.prompt_tokens
                        self.completion_tokens += chunk.usage.completion_tokens

        async for item in with_retry_stream(_stream_call, self.config):
            yield item

    async def test_connection(self) -> bool:
        if not self.config.api_key: return False
        try:
            if self.config.ai_provider == "anthropic":
                await self.client.messages.create(model=self.model, max_tokens=1, messages=[{"role": "user", "content": "ping"}])
            else:
                await self.client.models.list()
            return True
        except:
            return False

    async def list_models(self) -> list:
        if not self.config.api_key: return []
        try:
            if self.config.ai_provider in ["openrouter", "openai"]:
                resp = await self.client.models.list()
                return sorted([m.id for m in resp.data])
            return [self.model]
        except:
            return [self.model]

    async def _retry(self, func, *args, **kwargs):
        return await with_retry(func, self.config, *args, **kwargs)

    def _retry_stream(self, gen_func, *args, **kwargs):
        return with_retry_stream(gen_func, self.config, *args, **kwargs)

__all__ = ["LLMClient", "TokenBudgetExceededError"]
