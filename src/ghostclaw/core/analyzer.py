"""Core analyzer — orchestrates stack detection, metrics, and stack-specific analysis."""

import datetime
import asyncio
from pathlib import Path
from typing import Dict, Optional, List
from ghostclaw.core.detector import detect_stack, find_files, find_files_parallel
from ghostclaw.core.validator import RuleValidator
from ghostclaw.stacks import get_analyzer
from ghostclaw.core.cache import LocalCache, compute_fingerprint
from ghostclaw.core.config import GhostclawConfig
from ghostclaw.core.llm_client import LLMClient
from ghostclaw.core.context_builder import ContextBuilder
from ghostclaw.core.models import ArchitectureReport




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
        self.progress_cb = None

    async def analyze(self, root: str, use_cache: bool = True, config: Optional[GhostclawConfig] = None) -> ArchitectureReport:
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
            base_fingerprint = await asyncio.to_thread(compute_fingerprint, root_path)
            config_suffix = f":ai={config.use_ai}:pyscn={config.use_pyscn}:codeindex={config.use_ai_codeindex}"
            fingerprint = base_fingerprint + config_suffix

            cached_data = await asyncio.to_thread(self.cache.get, fingerprint)
            if cached_data is not None:
                # Mark as cache hit for transparency
                cached_data.setdefault("metadata", {})["cache_hit"] = True
                return ArchitectureReport(**cached_data)

        # 1. Detect stack
        stack = await asyncio.to_thread(detect_stack, root)

        # 2. Find relevant files based on stack
        analyzer = get_analyzer(stack)
        extensions = analyzer.get_extensions() if analyzer else []
        if self.progress_cb: self.progress_cb("Scanning files")

        # Use parallel file scanning if enabled and available
        if extensions:
            if config.parallel_enabled:
                files = await find_files_parallel(root, extensions, config.concurrency_limit)
            else:
                files = await asyncio.to_thread(find_files, root, extensions)
        else:
            files = []

        # 3. Compute base metrics
        def _get_metrics(file_list, threshold):
            total_lines = 0
            large_files = []
            line_counts = []
            for f in file_list:
                try:
                    with open(f, 'rb') as file:
                        count = 0
                        while True:
                            chunk = file.read(65536)
                            if not chunk:
                                break
                            count += chunk.count(b'\n')
                        if count > 0 or Path(f).stat().st_size > 0:
                            count += 1
                        total_lines += count
                        line_counts.append(count)
                        if count > threshold:
                            large_files.append(f)
                except Exception:
                    continue
            return total_lines, line_counts, large_files

        threshold = (analyzer.get_large_file_threshold() if analyzer else 300)
        total_lines, line_counts, large_files = await asyncio.to_thread(_get_metrics, files, threshold)

        total_files = len(files)
        avg_lines = sum(line_counts) / total_files if total_files > 0 else 0
        large_count = len(large_files)

        base_metrics = {
            "total_files": total_files,
            "total_lines": total_lines,
            "large_file_count": large_count,
            "average_lines": avg_lines,
            "vibe_score": 100
        }

        # 4. Standardized Tool Ingestion via Adapters
        from ghostclaw.core.adapters.registry import registry
        registry.register_internal_plugins()
        
        # Load local plugins if any
        local_plugins = root_path / ".ghostclaw" / "plugins"
        if local_plugins.exists():
            registry.load_external_plugins(local_plugins)

        # Apply plugin enable/disable filter from config
        if config.plugins_enabled is not None:
            registry.enabled_plugins = set(config.plugins_enabled)
        else:
            registry.enabled_plugins = None

        if self.progress_cb: self.progress_cb("Running adapters")
        adapter_results = await registry.run_analysis(root, files)
        if self.progress_cb: self.progress_cb("Adapters completed")

        # Unify findings from all adapters
        issues = []
        ghosts = []
        flags = []
        coupling_metrics = {}
        import_edges = []

        # Collect errors from adapter registry (if any)
        errors = list(getattr(registry, 'errors', []))

        for res in adapter_results:
            issues.extend(res.get("issues", []))
            ghosts.extend(res.get("architectural_ghosts", []))
            flags.extend(res.get("red_flags", []))
            coupling_metrics.update(res.get("coupling_metrics", {}))

        # 5. Legacy Stack-specific analysis (Pre-adapter porting)
        if analyzer:
            stack_result = await asyncio.to_thread(analyzer.analyze, root, files, base_metrics)
            issues.extend(stack_result.get('issues', []))
            ghosts.extend(stack_result.get('architectural_ghosts', []))
            flags.extend(stack_result.get('red_flags', []))
            coupling_metrics.update(stack_result.get('coupling_metrics', {}))

            if hasattr(analyzer, 'graph'):
                import_edges = analyzer.graph.edges
        else:
            issues.append("Standard stack detection failed.")

        # 5. Rule validation (Phase 4)
        try:
            report_with_rules = await asyncio.to_thread(self.validator.validate, stack, {
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

        # 6. Finalibe score
        vibe_score = self._compute_vibe_score(base_metrics, len(issues), len(ghosts))

        # 7. Metadata
        try:
            from ghostclaw.cli import __version__
        except ImportError:
            __version__ = "unknown"

        report_data = {
            "vibe_score": vibe_score,
            "stack": stack,
            "files_analyzed": total_files,
            "total_lines": total_lines,
            "issues": issues,
            "architectural_ghosts": ghosts,
            "red_flags": flags,
            "errors": errors,
            "metadata": {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
                "analyzer": "ghostclaw-async",
                "version": __version__,
                "adapters_active": [m["name"] for m in registry.get_plugin_metadata()],
                "pyscn_integrated": registry.pm.get_plugin("pyscn") is not None,
                "ai_codeindex_integrated": registry.pm.get_plugin("ai-codeindex") is not None
            }
        }

        # 8. Prompt Building
        if config.use_ai:
            context_builder = ContextBuilder()
            prompt = context_builder.build_prompt(
                metrics=base_metrics,
                issues=issues,
                ghosts=ghosts,
                flags=flags,
                coupling_metrics=coupling_metrics,
                import_edges=import_edges,
                patch=config.patch
            )
            report_data["ai_prompt"] = prompt

        # 9. Cache pre-synthesis
        if fingerprint is not None:
            report_data["metadata"]["fingerprint"] = fingerprint
            if use_cache and self.cache is not None:
                await asyncio.to_thread(self.cache.set, fingerprint, report_data)

        return ArchitectureReport(**report_data)

    def _compute_vibe_score(self, metrics: Dict, issue_count: int, ghost_count: int) -> int:
        """Calculate the final vibe score (0-100)."""
        score = 100
        large_file_penalty = min(30, metrics['large_file_count'] * 5)
        score -= large_file_penalty
        avg = metrics.get('average_lines', 0)
        if avg > 200: score -= 10
        score -= min(20, issue_count * 3)
        score -= min(15, ghost_count * 5)
        return max(0, min(100, score))
