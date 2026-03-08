import asyncio
import logging
from enum import Enum, auto
from typing import Dict, List, Callable, Any, Optional
from ghostclaw.core.config import GhostclawConfig
from ghostclaw.core.analyzer import CodebaseAnalyzer
from ghostclaw.core.llm_client import LLMClient

logger = logging.getLogger("ghostclaw.agent")

class AgentEvent(Enum):
    INIT = auto()
    PRE_ANALYZE = auto()
    POST_METRICS = auto()
    PRE_SYNTHESIS = auto()
    SYNTHESIS_CHUNK = auto()
    REASONING_CHUNK = auto()
    POST_SYNTHESIS = auto()
    ERROR = auto()

class GhostAgent:
    """
    Orchestrator for the analysis lifecycle.
    Encapsulates metrics collection and LLM synthesis with hooks for monitoring.
    """

    def __init__(self, config: GhostclawConfig, repo_path: str, analyzer: Optional[CodebaseAnalyzer] = None):
        self.config = config
        self.repo_path = repo_path
        self.analyzer = analyzer or CodebaseAnalyzer()
        self.llm_client = LLMClient(config, repo_path)
        self.hooks: Dict[AgentEvent, List[Callable[[Dict], Any]]] = {
            event: [] for event in AgentEvent
        }

    def on(self, event: AgentEvent, callback: Callable[[Dict], Any]):
        """Register a callback for a specific AgentEvent."""
        self.hooks[event].append(callback)

    async def _emit(self, event: AgentEvent, data: Dict = None):
        """Emit an event and trigger all registered hooks and adapters."""
        data = data or {}
        # Create a copy for hooks and adapters to avoid mutating caller's dict
        event_data = dict(data)
        event_data["event"] = event

        # 1. Trigger internal hooks with event_data (includes event)
        for hook in self.hooks[event]:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(event_data)
                else:
                    hook(event_data)
            except Exception as e:
                logger.error(f"Error in hook {hook} for event {event}: {e}")

        # 2. Trigger TargetAdapters via PluginRegistry with event_data
        from ghostclaw.core.adapters.registry import registry
        await registry.emit_event(event.name, event_data)

    async def run(self) -> Dict:
        """Execute the full agent workflow with lifecycle hooks and persistence."""
        try:
            from ghostclaw.core.adapters.registry import registry
            registry.register_internal_plugins()

            await self._emit(AgentEvent.INIT)
            
            await self._emit(AgentEvent.PRE_ANALYZE)
            report_model = await self.analyzer.analyze(self.repo_path, config=self.config)
            report = report_model.model_dump()
            await self._emit(AgentEvent.POST_METRICS, report)
            
            if self.config.use_ai and "ai_prompt" in report:
                await self._emit(AgentEvent.PRE_SYNTHESIS, report)
                
                content = []
                reasoning = []
                async for chunk_info in self.llm_client.stream_analysis(report["ai_prompt"]):
                    chunk = chunk_info["content"]
                    if chunk_info["type"] == "reasoning":
                        reasoning.append(chunk)
                        await self._emit(AgentEvent.REASONING_CHUNK, {"chunk": chunk})
                    else:
                        content.append(chunk)
                        await self._emit(AgentEvent.SYNTHESIS_CHUNK, {"chunk": chunk})
                
                report["ai_synthesis"] = "".join(content)
                report["ai_reasoning"] = "".join(reasoning)
                
                # Persist via StorageAdapters
                await registry.save_report(report)
                
                await self._emit(AgentEvent.POST_SYNTHESIS, report)
                
            self.timings['total'] = time.perf_counter() - self._start_time
        return report
        except Exception as e:
            await self._emit(AgentEvent.ERROR, {"error": str(e)})
            raise e
