import asyncio
import sys
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from ghostclaw.core.analyzer import CodebaseAnalyzer
from ghostclaw.core.cache import LocalCache
from ghostclaw.core.config import GhostclawConfig
from ghostclaw.core.agent import GhostAgent, AgentEvent

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.status import Status
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

class AnalyzerService:
    """
    Service for orchestrating the codebase analysis.
    """

    def __init__(self, repo_path: str, config_overrides: Dict[str, Any], use_cache: bool = True,
                 cache_dir: Optional[Path] = None, cache_ttl: int = 7, json_output: bool = False,
                 benchmark: bool = False):
        self.repo_path = repo_path
        self.config_overrides = config_overrides
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        self.json_output = json_output
        self.benchmark = benchmark
        self.cache: Optional[LocalCache] = None
        self.timings: Dict[str, float] = {}
        self.synthesis_streamed = False

    async def run(self) -> Dict[str, Any]:
        """Run the analysis pipeline."""
        try:
            config = GhostclawConfig.load(self.repo_path, **self.config_overrides)
        except Exception as e:
            raise ValueError(f"Configuration Error: {e}")

        # Initialize cache if needed
        if self.use_cache:
            self.cache = LocalCache(
                cache_dir=self.cache_dir,
                ttl_days=self.cache_ttl,
                compression=config.cache_compression
            )

        analyzer = CodebaseAnalyzer(cache=self.cache if self.use_cache else None)
        agent = GhostAgent(config, self.repo_path, analyzer=analyzer)

        console = Console() if HAS_RICH and not self.json_output else None
        status = None
        live = None
        synthesis_content = []
        self.synthesis_streamed = False

        async def on_pre_analyze(data):
            nonlocal status
            if console:
                status = console.status("[bold green]Ghostclaw is analyzing architecture...[/bold green]", spinner="dots")
                status.start()

        async def on_post_metrics(data):
            nonlocal status
            if status:
                status.update("[bold blue]Metrics collected. Preparing Ghost Engine...[/bold blue]")

        async def on_pre_synthesis(data):
            nonlocal status
            if status:
                status.update("[bold cyan]🧠 Ghost Engine Synthesis starting...[/bold cyan]")
                print("\n" + "="*50 + "\n")
                print("🧠 Ghost Engine Synthesis:\n")

        async def on_synthesis_chunk(data):
            nonlocal status, live
            self.synthesis_streamed = True
            chunk = data["chunk"]
            synthesis_content.append(chunk)

            if console:
                if status:
                    status.stop()
                    status = None

                if not live:
                    from rich.live import Live
                    live = Live(Text(""), console=console, refresh_per_second=10, transient=True)
                    live.start()

                live.update(Text("".join(synthesis_content)))
            else:
                output_stream = sys.stderr if self.json_output else sys.stdout
                output_stream.write(chunk)
                output_stream.flush()

        async def on_post_synthesis(data):
            nonlocal live, status
            if live:
                live.stop()
                live = None
            if status:
                status.stop()
                status = None

            output_stream = sys.stderr if self.json_output else sys.stdout
            output_stream.write("\n\n" + "="*50)
            output_stream.flush()
            if console and synthesis_content:
                full_text = "".join(synthesis_content)
                if full_text.strip(): console.print(Markdown(full_text))

        async def on_reasoning_chunk(data):
            nonlocal status, live
            chunk = data["chunk"]
            if console:
                if status:
                    status.stop()
                    status = None
                if not live:
                    from rich.live import Live
                    live = Live(Text(""), console=console, refresh_per_second=10, transient=True)
                    live.start()
                current_text = live.get_renderable()
                if isinstance(current_text, Text):
                    current_text.append(chunk, style="dim italic")
                    live.update(current_text)
            else:
                output_stream = sys.stderr if self.json_output else sys.stdout
                output_stream.write(f"\033[2m{chunk}\033[0m")
                output_stream.flush()

        agent.on(AgentEvent.PRE_ANALYZE, on_pre_analyze)
        agent.on(AgentEvent.POST_METRICS, on_post_metrics)
        agent.on(AgentEvent.PRE_SYNTHESIS, on_pre_synthesis)
        agent.on(AgentEvent.REASONING_CHUNK, on_reasoning_chunk)
        agent.on(AgentEvent.SYNTHESIS_CHUNK, on_synthesis_chunk)
        agent.on(AgentEvent.POST_SYNTHESIS, on_post_synthesis)

        try:
            report = await agent.run()

            if self.benchmark:
                self.timings = getattr(agent, 'timings', {})

            report["_synthesis_streamed"] = self.synthesis_streamed

            if self.use_cache and self.cache and not config.dry_run and "metadata" in report and "fingerprint" in report["metadata"]:
                self.cache.set(report["metadata"]["fingerprint"], report)

            return report

        except Exception as e:
            if status: status.stop()
            if live: live.stop()
            raise Exception(f"Analysis Error: {e}")
