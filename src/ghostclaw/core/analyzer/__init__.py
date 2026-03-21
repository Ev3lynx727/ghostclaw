"""
CodebaseAnalyzer facade — orchestrates stack detection, metrics, and stack-specific analysis.
"""

import datetime
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List

from ghostclaw.core.detector import find_files, find_files_parallel
from ghostclaw.core.validator import RuleValidator
from ghostclaw.core.cache import LocalCache, compute_fingerprint
from ghostclaw.core.config import GhostclawConfig
from ghostclaw.core.models import ArchitectureReport
from ghostclaw.core import git_utils

from .metrics import MetricCollector
from .stacks import StackAnalyzer
from .scoring import VibeScorer

logger = logging.getLogger("ghostclaw.analyzer")


class CodebaseAnalyzer:
    """Main analyzer class that coordinates the full analysis pipeline."""

    def __init__(self, validator: RuleValidator = None, cache: LocalCache = None):
        self.validator = validator or RuleValidator()
        self.cache = cache
        self.progress_cb = None

    @staticmethod
    def _find_base_report(repo_path: Path, base_ref: str = "HEAD~1") -> Optional[dict]:
        """Find the base report for delta context by matching commit SHA."""
        reports_dir = repo_path / ".ghostclaw" / "storage" / "reports"
        if not reports_dir.exists():
            return None

        try:
            import subprocess
            result = subprocess.run(
                ["git", "-C", str(repo_path), "rev-parse", base_ref],
                capture_output=True, text=True, check=False, timeout=5
            )
            base_sha = result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            base_sha = None

        json_files = list(reports_dir.glob("*.json"))
        if not json_files:
            return None

        if base_sha:
            for path in json_files:
                try:
                    data = json.loads(path.read_text(encoding='utf-8'))
                    if data.get("metadata", {}).get("vcs", {}).get("commit") == base_sha:
                        return data
                except Exception:
                    continue

        latest = max(json_files, key=lambda p: p.stat().st_mtime)
        try:
            return json.loads(latest.read_text(encoding='utf-8'))
        except Exception:
            return None

    async def analyze(self, root: str, use_cache: bool = True, config: Optional[GhostclawConfig] = None) -> ArchitectureReport:
        """Perform a complete architectural analysis of a codebase."""
        root_path = Path(root)
        config = config or GhostclawConfig()
        
        delta_mode = getattr(config, 'delta_mode', False)
        delta_base_ref = getattr(config, 'delta_base_ref', None) or 'HEAD~1'

        fingerprint = None
        if use_cache and self.cache is not None:
            base_fingerprint = await asyncio.to_thread(compute_fingerprint, root_path)
            delta_suffix = f":delta={delta_mode}:base={delta_base_ref}" if delta_mode else ""
            config_suffix = f":ai={config.use_ai}:pyscn={config.use_pyscn}:codeindex={config.use_ai_codeindex}{delta_suffix}"
            fingerprint = base_fingerprint + config_suffix

            cached_data = await asyncio.to_thread(self.cache.get, fingerprint)
            if cached_data is not None:
                cached_data.setdefault("metadata", {})["cache_hit"] = True
                return ArchitectureReport(**cached_data)

        # 1. Detect stack
        stack = await StackAnalyzer.detect(root)
        analyzer_instance = StackAnalyzer.get_analyzer_instance(stack)
        extensions = analyzer_instance.get_extensions() if analyzer_instance else []

        # 2. Find relevant files
        if self.progress_cb: self.progress_cb("Scanning files")
        diff_result = None
        changed_rel_paths = []
        
        if delta_mode:
            diff_result = await asyncio.to_thread(git_utils.get_git_diff, delta_base_ref, root_path)
            changed_rel_paths = diff_result.files_changed
            files = [str(root_path / r) for r in changed_rel_paths if (root_path / r).exists() and (not extensions or (root_path / r).suffix in extensions)]
        else:
            if extensions:
                if config.parallel_enabled:
                    files = await find_files_parallel(root, extensions, config.concurrency_limit)
                else:
                    files = await asyncio.to_thread(find_files, root, extensions)
            else:
                files = []

        # 3. Compute base metrics
        threshold = (analyzer_instance.get_large_file_threshold() if analyzer_instance else 300)
        total_lines, line_counts, large_files = await asyncio.to_thread(MetricCollector.collect_metrics, files, threshold)

        total_files = len(files)
        avg_lines = sum(line_counts) / total_files if total_files > 0 else 0
        base_metrics = {
            "total_files": total_files, "total_lines": total_lines,
            "large_file_count": len(large_files), "average_lines": avg_lines, "vibe_score": 100
        }

        # 4. Standardized Tool Ingestion via Adapters
        from ghostclaw.core.adapters.registry import registry
        registry.register_internal_plugins()
        if (root_path / ".ghostclaw" / "plugins").exists():
            registry.load_external_plugins(root_path / ".ghostclaw" / "plugins")

        # Apply plugin filter
        # Orchestrator enforcement: if orchestrator is enabled, force only orchestrator to run
        if config.orchestrator and config.orchestrator.get('enabled'):
            registry.enabled_plugins = {'orchestrator'}
        elif config.plugins_enabled is not None:
            registry.enabled_plugins = set(config.plugins_enabled)
        elif config.use_qmd:
            registry.enabled_plugins = None  # All plugins enabled including qmd
        else:
            from ghostclaw.core.adapters.registry import INTERNAL_PLUGINS
            registry.enabled_plugins = (set(INTERNAL_PLUGINS) | set(registry.external_plugins)) - {"qmd"}

        if config.use_qmd and registry.enabled_plugins is not None:
            registry.enabled_plugins.add('sqlite')
            registry.enabled_plugins.add('qmd')


        if self.progress_cb: self.progress_cb("Running adapters")
        adapter_results = await registry.run_analysis(root, files)
        errors = list(getattr(registry, 'errors', []))
        
        issues, ghosts, flags, coupling_metrics, symbol_index = [], [], [], {}, ""
        for res in adapter_results:
            issues.extend(res.get("issues", []))
            ghosts.extend(res.get("architectural_ghosts", []))
            flags.extend(res.get("red_flags", []))
            coupling_metrics.update(res.get("coupling_metrics", {}))
            if "symbol_index" in res: symbol_index += res["symbol_index"] + "\n"

        # 5. Legacy Stack-specific analysis and Rule validation
        stack_result = await StackAnalyzer.analyze_stack(stack, root, files, base_metrics)
        issues.extend(stack_result.get('issues', []))
        ghosts.extend(stack_result.get('architectural_ghosts', []))
        flags.extend(stack_result.get('red_flags', []))
        coupling_metrics.update(stack_result.get('coupling_metrics', {}))
        import_edges = stack_result.get('import_edges', [])

        try:
            report_with_rules = await asyncio.to_thread(self.validator.validate, stack, {
                "issues": issues, "architectural_ghosts": ghosts, "red_flags": flags,
                "coupling_metrics": coupling_metrics, "import_edges": import_edges,
                "files": files, "files_analyzed": total_files, "total_lines": total_lines,
                "stack": stack, **base_metrics
            })
            issues, ghosts, flags = report_with_rules['issues'], report_with_rules['architectural_ghosts'], report_with_rules['red_flags']
        except Exception as e:
            issues.append(f"Rule validation failed: {str(e)}")

        # 6. Final vibe score
        context_data = {"metrics": base_metrics, "issues": issues, "ghosts": ghosts, "flags": flags, "stack": stack, "files": files, "coupling_metrics": coupling_metrics}
        vibe_score = await VibeScorer.compute_score(context_data)

        # 7. Metadata and AI Prompt
        try:
            from ghostclaw.cli import __version__
        except ImportError:
            __version__ = "unknown"

        report_data = {
            "repo_path": str(root_path),
            "vibe_score": vibe_score, "stack": stack, "files_analyzed": total_files, "total_lines": total_lines,

            "issues": issues, "architectural_ghosts": ghosts, "red_flags": flags, "coupling_metrics": coupling_metrics,
            "errors": errors,
            "metadata": {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
                "analyzer": "ghostclaw-async", "version": __version__,
                "adapters_active": [m["name"] for m in registry.get_plugin_metadata()],
                "pyscn_integrated": registry.pm.get_plugin("pyscn") is not None,
                "ai_codeindex_integrated": registry.pm.get_plugin("ai-codeindex") is not None
            }
        }
        try:
            report_data["metadata"]["vcs"] = {"commit": git_utils.get_current_sha(root_path), "branch": git_utils.get_current_branch(root_path), "dirty": git_utils.has_uncommitted_changes(root_path)}
        except Exception: pass

        # Attach delta-context metadata if in delta mode
        if delta_mode:
            report_data["metadata"]["delta"] = {
                "mode": True,
                "base_ref": delta_base_ref,
                "diff": diff_result.raw_diff if diff_result else "",
                "files_changed": changed_rel_paths
            }

        if config.use_ai:
            from ghostclaw.core.context_builder import ContextBuilder
            context_builder = ContextBuilder()
            if delta_mode:
                base_report = self._find_base_report(root_path, base_ref=delta_base_ref)
                report_data["ai_prompt"] = context_builder.build_delta_prompt(base_metrics, issues, ghosts, flags, diff_result.raw_diff if diff_result else "", base_report)
            else:
                report_data["ai_prompt"] = context_builder.build_prompt(base_metrics, issues, ghosts, flags, coupling_metrics, import_edges, config.patch, symbol_index)

        if fingerprint and use_cache and self.cache:
            report_data["metadata"]["fingerprint"] = fingerprint
            await asyncio.to_thread(self.cache.set, fingerprint, report_data)

        return ArchitectureReport(**report_data)
