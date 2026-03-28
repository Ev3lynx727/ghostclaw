# Roadmap: Enhanced Logfire AI Instrumentation

## Goal

Improve observability of Ghostclaw's AI synthesis operations by:
1. Instrumenting OpenAI and Anthropic SDKs with Logfire to capture AI-specific spans (prompt tokens, completion tokens, latency, errors).
2. Adding tests to verify that AI spans are emitted when telemetry is enabled.

This will give users visibility into LLM usage, costs, and performance directly in their Logfire dashboard.

---

## Current State

- Logfire adapter only instruments `httpx` (low-level HTTP transport)
- LLM calls via `AsyncOpenAI`/`AsyncAnthropic` appear as generic HTTP requests, not as AI operations
- No dedicated test verifying that AI operations produce identifiable spans

---

## Proposed Changes

### 1. Extend `logfire_adapter.py` to instrument AI SDKs

```python
def initialize(self, context: Optional[Dict[str, Any]] = None) -> None:
    if os.environ.get("GHOSTCLAW_TELEMETRY") != "1":
        return
    if logfire is None:
        logger.warning("Logfire package not found. Telemetry disabled.")
        return

    try:
        logfire.configure(send_to_logfire=True)

        # Existing
        logfire.instrument_httpx()

        # New: AI SDK instrumentation (if available)
        try:
            logfire.instrument_openai()
        except AttributeError:
            logger.debug("Logfire does not support instrument_openai (older version). Skipping.")
        try:
            logfire.instrument_anthropic()
        except AttributeError:
            logger.debug("Logfire does not support instrument_anthropic. Skipping.")

        self._initialized = True
        logger.debug("Logfire telemetry initialized with AI instrumentation.")
    except ImportError as e:
        logger.warning(f"Logfire dependencies missing: {e}. Telemetry disabled.")
    except Exception as e:
        logger.error(f"Failed to initialize Logfire: {e}")
```

**Notes:**
- The `instrument_openai()` and `instrument_anthropic()` methods are provided by Pydantic Logfire when installed with AI extras. We should guard with `try/except` to avoid breaking on minimal Logfire installs.
- Optionally add `logfire.instrument_langchain()` etc. if Ghostclaw ever integrates with LangChain.

### 2. Add `tests/integration/test_logfire_ai_spans.py`

Create a new integration test that:
- Enables `GHOSTCLAW_TELEMETRY=1`
- Initializes telemetry
- Calls `LLMClient` to perform a minimal AI synthesis (mocked or using a dummy provider to avoid real API calls)
- Asserts that Logfire received spans with expected attributes (e.g., `span.name` containing "openai" or "anthropic", `otel_attributes` with `gen_ai.*` keys)

Because we don't want to hit real LLM APIs during CI, we can:
- Use `unittest.mock` to patch the provider's `stream_analysis` method and emit fake spans, or
- Use a lightweight fake LLM client that still triggers instrumentation

Alternatively, a **unit test** with mocks is simpler and CI-friendly:

```python
def test_ai_spans_emitted_when_telemetry_enabled(monkeypatch):
    monkeypatch.setenv("GHOSTCLAW_TELEMETRY", "1")
    with patch("ghostclaw.core.adapters.telemetry.logfire_adapter.logfire") as mock_lf:
        from ghostclaw.core.adapters.telemetry import bootstrap_telemetry
        bootstrap_telemetry()
        # Simulate an LLM call by manually creating a span
        # In real code, the instrumentation hooks would auto-create spans
        # We can assert that the mock's instrument_* methods were called
        mock_lf.instrument_openai.assert_called_once()
        mock_lf.instrument_anthropic.assert_called_once()
```

But note: We may only want to call `instrument_openai` if OpenAI SDK is installed. We should instead assert that `configure` was called and that at least one AI instrumenter was attempted.

A better integration test would invoke `LLMClient` with a mocked provider and verify that Logfire captured spans. However, this requires more complex setup.

---

## Implementation Steps

1. Update `src/ghostclaw/core/adapters/telemetry/logfire_adapter.py` with conditional AI instrumentation (as above).
2. Add a unit test in `tests/unit/test_telemetry.py` to verify that:
   - When telemetry is enabled, `logfire.configure` is called.
   - The adapter attempts to call `instrument_openai` and `instrument_anthropic` if Logfire provides them.
   - If the methods don't exist, no error is raised.
3. Optionally add an integration test `tests/integration/test_logfire_ai_integration.py` that performs a fake LLM call (with provider patched) and checks that spans appear in Logfire's in-memory exporter (if we use `logfire.testing` utilities).

---

## Dependencies

- **Logfire version** must include `instrument_openai` and `instrument_anthropic`. These are available in recent Pydantic Logfire releases. We should note this in `pyproject.toml` optional-dependencies as a recommended extra: `logfire[ai]`.
- No new runtime dependencies for Ghostclaw itself; the instrumentation is opt-in via `logfire` package extras.

---

## Risks & Considerations

- **Compatibility**: Older Logfire versions may not have the `instrument_*` methods. We must handle `AttributeError` gracefully.
- **Performance**: Instrumentation adds slight overhead but is acceptable for telemetry-enabled runs.
- **Testing**: We don't want real API calls in CI. Use mocks for unit tests; integration tests can be marked as manual (`pytest -m integration`).
- **Documentation**: Update `docs/TROUBLESHOOT.md` to mention that AI instrumentation requires `logfire[ai]` and to set `GHOSTCLAW_TELEMETRY=1`.

---

## Milestones

1. **v0.2.8 (Feature)**: Enhanced Logfire AI instrumentation merged to `develop`.
2. **v0.2.9 (Tests)**: AI span verification tests passing in CI (with mocks).
3. **v0.3.0 (Docs)**: Update telemetry documentation with AI instrumentation details and example Logfire queries.

---

## Example Logfire Queries (for users)

Once AI instrumentation is active, users can query in Logfire:

- `otel_attributes["gen_ai.prompt"]` > 0 to see all LLM prompts
- `otel_attributes["gen_ai.completion"]` for responses
- `otel_attributes["gen_ai.usage.total_tokens"]` for token consumption
- Filter by `service.name="ghostclaw"` and `span.kind="client"`

These queries can be added to the docs.
