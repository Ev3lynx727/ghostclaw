"""Core analyzer — orchestrates stack detection, metrics, and stack-specific analysis."""

import datetime
import asyncio
from pathlib import Path
from typing import Dict, Optional
from ghostclaw.core.detector import detect_stack, find_files
from ghostclaw.core.validator import RuleValidator
from ghostclaw.stacks import get_analyzer
from ghostclaw.core.cache import LocalCache, compute_fingerprint
from ghostclaw.core.config import GhostclawConfig
from ghostclaw.core.llm_client import LLMClient
from ghostclaw.core.context_builder import ContextBuilder

# Defensive import for Phase 1: pyscn Integration
try:
    from ghostclaw.core.pyscn_wrapper import PySCNAnalyzer
    HAS_PYSCN = True
except ImportError:
    HAS_PYSCN = False

# Defensive import for Phase 1: ai-codeindex Integration
try:
    from ghostclaw.core.ai_codeindex_wrapper import AICodeIndexWrapper
    HAS_AI_CODEINDEX = True
except ImportError:
    HAS_AI_CODEINDEX = False


class CodebaseAnalyzer:
    """Main analyzer class that coordinates the full analysis pipeline."""

    def __init__(self, validator: RuleValidator = None, cache: LocalCache = None):
        """
        Initialize the analyzer with optional injected dependencies.

        Args:
            validator: Rule engine to use (Phase 4)
            cache: Optional LocalCache instance for result caching
        """
        self.validator = validator or RuleValidator()
        self.cache = cache

    def analyze(self, root: str, use_cache: bool = True, config: Optional[GhostclawConfig] = None) -> Dict:
        """
        Perform a complete architectural analysis of a codebase.

        Args:
            root: Path to repository root
            use_cache: Whether to use/write cache (if cache enabled)
            config: GhostclawConfig instance with user settings


        Returns:
            Complete analysis report with vibe score, issues, ghosts, etc.
        """
        root_path = Path(root)
        config = config or GhostclawConfig()
        use_pyscn = config.use_pyscn
        use_ai_codeindex = config.use_ai_codeindex

        fingerprint = None
        # 0. Cache shortcut if enabled
        if use_cache and self.cache is not None:
            fingerprint = compute_fingerprint(root_path)
            cached_report = self.cache.get(fingerprint)
            if cached_report is not None:
                # Mark as cache hit for transparency
                cached_report.setdefault("metadata", {})["cache_hit"] = True
                return cached_report

        # 1. Detect stack
        stack = detect_stack(root)

        # 2. Find relevant files based on stack
        analyzer = get_analyzer(stack)
        extensions = analyzer.get_extensions() if analyzer else []
        files = find_files(root, extensions) if extensions else []

        # 3. Compute base metrics
        total_lines = 0
        large_files = []
        line_counts = []
        for f in files:
            try:
                with open(f, 'rb') as file:
                    # Efficient chunk-based line counting
                    count = 0
                    while True:
                        chunk = file.read(65536)
                        if not chunk:
                            break
                        count += chunk.count(b'\n')
                    # Handle files without a final newline
                    if count > 0 or Path(f).stat().st_size > 0:
                        count += 1

                    total_lines += count
                    line_counts.append(count)
                    if count > (analyzer.get_large_file_threshold() if analyzer else 300):
                        large_files.append(f)
            except Exception:
                continue

        total_files = len(files)
        avg_lines = sum(line_counts) / total_files if total_files > 0 else 0
        large_count = len(large_files)

        base_metrics = {
            "total_files": total_files,
            "total_lines": total_lines,
            "large_file_count": large_count,
            "average_lines": avg_lines,
            "vibe_score": 100  # Will be computed later
        }

        # 4. Stack-specific analysis
        pyscn_used = False
        ai_codeindex_used = False
        import_edges = []

        if analyzer:
            stack_result = analyzer.analyze(root, files, base_metrics)
            issues = stack_result.get('issues', [])
            ghosts = stack_result.get('architectural_ghosts', [])
            flags = stack_result.get('red_flags', [])
            coupling_metrics = stack_result.get('coupling_metrics', {})

            # Extract edges if the analyzer has a graph
            if hasattr(analyzer, 'graph'):
                import_edges = analyzer.graph.edges

            # Integration Step: Additive Integration (Option A)
            if (use_pyscn is not False) and HAS_PYSCN:
                pyscn = PySCNAnalyzer(root)
                if pyscn.is_available():
                    pyscn_used = True
                    pyscn_report = pyscn.analyze()
                    if "error" not in pyscn_report:
                        # Enhance the report with pyscn insights
                        # For example, adding discovered clones/dead code to issues
                        clones = pyscn_report.get("clones", [])
                        if clones:
                            ghosts.append(f"Found {len(clones)} code clones via pyscn (Phase 1 Integration)")

                        dead_code = pyscn_report.get("dead_code", [])
                        if dead_code:
                            issues.append(f"Detected {len(dead_code)} potential dead code spots via pyscn")
                else:
                    if hasattr(self, 'logger'):
                        self.logger.info("Install 'pyscn' for deeper dead code and clone detection capabilities.")
                    else:
                        issues.append("Info: Optional dependency 'pyscn' not found. Install for clone detection.")

            # Integration Step: Additive Integration (Option A) - ai-codeindex
            if (use_ai_codeindex is not False) and HAS_AI_CODEINDEX:
                ai_codeindex = AICodeIndexWrapper(root)
                if ai_codeindex.is_available():
                    ai_codeindex_used = True
                    graph_data = ai_codeindex.build_graph()
                    if "error" not in graph_data:
                        # Enhance coupling metrics with tree-sitter based graph
                        inheritance = ai_codeindex.get_inheritance_depth()
                        if inheritance:
                            deep_inheritance = [c for c, d in inheritance.items() if d > 3]
                            if deep_inheritance:
                                ghosts.append(f"Deep inheritance hierarchies detected via ai-codeindex: {', '.join(deep_inheritance[:3])}")

                        # Mark report as having enhanced graphing
                        coupling_metrics["graph_engine"] = "ai-codeindex"
                else:
                    if hasattr(self, 'logger'):
                        self.logger.info("Install 'ai-codeindex' for deeper AST coupling metrics.")
                    else:
                        issues.append("Info: Optional dependency 'ai-codeindex' not found. Install for AST graphs.")

        else:
            # Upgrade: Fallback logic for unknown stacks
            issues = ["Standard stack detection failed."]
            ghosts = []
            flags = []
            coupling_metrics = {}

            if config.use_ai:
                ghosts.append("Attempting AI Synthesis fallback (Ghost Engine)")
                if HAS_AI_CODEINDEX:
                    ai_codeindex = AICodeIndexWrapper(root)
                    if ai_codeindex.is_available():
                        ai_codeindex_used = True
                        ghosts.append("Successfully hooked into AI CodeIndex to ingest unknown architecture.")
                    else:
                        issues.append("AI-CodeIndex unavailable for fallback ingestion.")
        # 5. Merge metrics for vibe score
        combined_metrics = {**base_metrics, "coupling_metrics": coupling_metrics}

        # 6. Apply rule validation (Phase 4)
        try:
            report_with_rules = self.validator.validate(stack, {
                "issues": issues,
                "architectural_ghosts": ghosts,
                "red_flags": flags,
                "coupling_metrics": coupling_metrics,
                "import_edges": import_edges,
                "files": files,
                "files_analyzed": total_files,
                "total_lines": total_lines,
                "stack": stack,
                **base_metrics
            })
            issues = report_with_rules['issues']
            ghosts = report_with_rules['architectural_ghosts']
            flags = report_with_rules['red_flags']
        except Exception as e:
            issues.append(f"Rule validation failed: {str(e)}")

        # 7. Compute final vibe score
        vibe_score = self._compute_vibe_score(base_metrics, len(issues), len(ghosts))

        # 8. Build final report
        try:
            from cli import __version__
        except ImportError:
            __version__ = "unknown"

        report = {
            "vibe_score": vibe_score,
            "stack": stack,
            "files_analyzed": total_files,
            "total_lines": total_lines,
            "issues": issues,
            "architectural_ghosts": ghosts,
            "red_flags": flags,
            "metadata": {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
                "analyzer": "ghostclaw-refactored",
                "version": __version__,
                "coupling_enabled": True,
                "rules_enabled": True,
                "pyscn_integrated": pyscn_used,
                "ai_codeindex_integrated": ai_codeindex_used
            }
        }

        # 9. Ghost Engine Synthesis
        if config.use_ai:
            llm_client = LLMClient(config, root)
            context_builder = ContextBuilder()
            prompt = context_builder.build_prompt(
                metrics=base_metrics,
                issues=issues,
                ghosts=ghosts,
                flags=flags,
                coupling_metrics=coupling_metrics,
                import_edges=import_edges
            )

            # Use asyncio to consume the stream generator with Rich UX
            async def _consume_stream():
                content = []
                import sys

                try:
                    from rich.console import Console
                    from rich.markdown import Markdown
                    from rich.status import Status
                    has_rich = True
                    console = Console()
                except ImportError:
                    has_rich = False

                print("\n" + "="*50 + "\n")
                print("🧠 Ghost Engine Synthesis:\n")

                if has_rich:
                    status = console.status("[bold green]Ghostclaw is analyzing architecture and synthesizing vibes...[/bold green]", spinner="dots")
                    status.start()

                first_chunk_received = False

                async for chunk in llm_client.stream_analysis(prompt):
                    if not first_chunk_received:
                        first_chunk_received = True
                        if has_rich:
                            status.stop()

                    # Print raw tokens as they stream to avoid UI flicker from unclosed markdown tags
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
                    content.append(chunk)

                full_text = "".join(content)
                print("\n\n" + "="*50)

                # Re-render the full string as beautifully formatted Markdown if rich is available
                if has_rich and full_text.strip():
                    # Instead of printing both, clear the raw stream with an ANSI code
                    # by moving the cursor up by the number of lines printed.
                    lines_printed = full_text.count('\n') + 2 # +2 for padding
                    sys.stdout.write(f"\033[{lines_printed}A\033[J")
                    sys.stdout.flush()
                    console.print(Markdown(full_text))

                return full_text

            ai_synthesis = asyncio.run(_consume_stream())
            report["ai_synthesis"] = ai_synthesis

        # Store in cache if enabled and we have a fingerprint
        if use_cache and self.cache is not None and fingerprint is not None:
            # Only cache if analysis succeeded (has vibe_score)
            if "vibe_score" in report:
                self.cache.set(fingerprint, report)

        return report

    def _compute_vibe_score(self, metrics: Dict, issue_count: int, ghost_count: int) -> int:
        """Calculate the final vibe score (0-100)."""
        score = 100

        # Penalty for large files
        large_file_penalty = min(30, metrics['large_file_count'] * 5)
        score -= large_file_penalty

        # Penalty for high average lines
        avg = metrics.get('average_lines', 0)
        if avg > 200:
            score -= 10

        # Additional penalty for explicit issues
        score -= min(20, issue_count * 3)
        score -= min(15, ghost_count * 5)

        return max(0, min(100, score))
