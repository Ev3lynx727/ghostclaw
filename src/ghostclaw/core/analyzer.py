"""Core analyzer — orchestrates stack detection, metrics, and stack-specific analysis."""

import datetime
import asyncio
import json
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
from ghostclaw.core.score import ScoringEngine
from ghostclaw.core import git_utils




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

    @staticmethod
    def _find_base_report(repo_path: Path, base_ref: str = "HEAD~1") -> Optional[dict]:
        """Find the base report for delta context by matching commit SHA."""
        reports_dir = repo_path / ".ghostclaw" / "storage" / "reports"
        if not reports_dir.exists():
            return None

        # Resolve base_ref to a commit SHA
        try:
            import subprocess
            result = subprocess.run(
                ["git", "-C", str(repo_path), "rev-parse", base_ref],
                capture_output=True, text=True, check=False, timeout=5
            )
            if result.returncode != 0:
                # Invalid ref; fall back to latest
                base_sha = None
            else:
                base_sha = result.stdout.strip()
        except Exception:
            base_sha = None

        # Collect candidate JSON reports
        json_files = list(reports_dir.glob("*.json"))
        if not json_files:
            return None

        # If we have a SHA, try to find exact match
        if base_sha:
            for path in json_files:
                try:
                    data = json.loads(path.read_text(encoding='utf-8'))
                    vcs = data.get("metadata", {}).get("vcs", {})
                    if vcs.get("commit") == base_sha:
                        return data
                except Exception:
                    continue

        # Fallback: return latest report by modification time
        if base_sha:
            # Only warn if we tried to match a specific SHA but failed
            try:
                import sys
                print(f"⚠️  Could not find base report for commit {base_sha[:8]}. Using latest report as base.", file=sys.stderr)
            except Exception:
                pass

        latest = max(json_files, key=lambda p: p.stat().st_mtime)
        try:
            data = json.loads(latest.read_text(encoding='utf-8'))
            return data
        except Exception:
            return None

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

        # Delta mode detection (Phase 2)
        delta_mode = getattr(config, 'delta_mode', False)
        delta_base_ref = getattr(config, 'delta_base_ref', 'HEAD~1')

        # Prepare for delta metadata
        diff_result = None
        changed_rel_paths = []

        fingerprint = None
        # 0. Cache shortcut if enabled
        if use_cache and self.cache is not None:
            base_fingerprint = await asyncio.to_thread(compute_fingerprint, root_path)
            delta_suffix = f":delta={delta_mode}:base={delta_base_ref}" if delta_mode else ""
            config_suffix = f":ai={config.use_ai}:pyscn={config.use_pyscn}:codeindex={config.use_ai_codeindex}{delta_suffix}"
            fingerprint = base_fingerprint + config_suffix

            cached_data = await asyncio.to_thread(self.cache.get, fingerprint)
            if cached_data is not None:
                # Mark as cache hit for transparency
                cached_data.setdefault("metadata", {})["cache_hit"] = True
                return ArchitectureReport(**cached_data)

        # 1. Detect stack
        stack = await asyncio.to_thread(detect_stack, root)

        # 2. Find relevant files based on stack (Delta-Ctx aware)
        analyzer = get_analyzer(stack)
        extensions = analyzer.get_extensions() if analyzer else []
        if self.progress_cb: self.progress_cb("Scanning files")

        if delta_mode:
            # Delta mode: analyze only changed files from git diff
            diff_result = await asyncio.to_thread(git_utils.get_git_diff, delta_base_ref, root_path)
            changed_rel_paths = diff_result.files_changed

            # Filter to existing source files that match stack extensions
            files = []
            for rel_path in changed_rel_paths:
                abs_path = root_path / rel_path
                if not abs_path.exists():
                    continue
                if extensions and abs_path.suffix not in extensions:
                    continue
                files.append(str(abs_path))

            if self.progress_cb:
                self.progress_cb(f"Delta: analyzing {len(files)} changed files (from {len(changed_rel_paths)} diff hunks)")
        else:
            # Full scan: all files matching stack extensions
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
            # No explicit plugin filter from user
            if config.use_qmd:
                # All plugins (internal + external) enabled, including qmd
                registry.enabled_plugins = None
            else:
                # All plugins except qmd
                from ghostclaw.core.adapters.registry import INTERNAL_PLUGINS
                plugins = set(INTERNAL_PLUGINS)
                plugins.discard("qmd")
                # Include any external plugins that were loaded
                plugins.update(registry.external_plugins)
                registry.enabled_plugins = plugins

        # If QMD backend is requested via config.use_qmd, ensure both 'sqlite' and 'qmd' are enabled (dual-write)
        # This overrides any user omission from plugins_enabled.
        if config.use_qmd and registry.enabled_plugins is not None:
            registry.enabled_plugins.add("sqlite")
            registry.enabled_plugins.add("qmd")

        if self.progress_cb: self.progress_cb("Running adapters")
        adapter_results = await registry.run_analysis(root, files)
        if self.progress_cb: self.progress_cb("Adapters completed")

        # Unify findings from all adapters
        issues = []
        ghosts = []
        flags = []
        coupling_metrics = {}
        import_edges = []
        symbol_index = ""

        # Collect errors from adapter registry (if any)
        errors = list(getattr(registry, 'errors', []))

        for res in adapter_results:
            issues.extend(res.get("issues", []))
            ghosts.extend(res.get("architectural_ghosts", []))
            flags.extend(res.get("red_flags", []))
            coupling_metrics.update(res.get("coupling_metrics", {}))
            if "symbol_index" in res:
                symbol_index += res["symbol_index"] + "\n"

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

        # 6. Final vibe score
        # Attempt to use a custom ScoringAdapter first
        context_data = {
            "metrics": base_metrics,
            "issues": issues,
            "ghosts": ghosts,
            "flags": flags,
            "stack": stack,
            "files": files,
            "coupling_metrics": coupling_metrics
        }

        from ghostclaw.core.adapters.registry import registry
        custom_score = await registry.compute_custom_vibe(context=context_data)
        if custom_score is not None:
            vibe_score = int(custom_score)
        else:
            vibe_score = ScoringEngine.compute_vibe_score(base_metrics, len(issues), len(ghosts))

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
            "coupling_metrics": coupling_metrics,
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

        # Add VCS metadata (commit SHA, branch, dirty status)
        try:
            report_data["metadata"]["vcs"] = {
                "commit": git_utils.get_current_sha(Path(root)),
                "branch": git_utils.get_current_branch(Path(root)),
                "dirty": git_utils.has_uncommitted_changes(Path(root))
            }
        except Exception:
            # If git fails, ignore VCS metadata
            pass

        # Attach delta-context metadata if in delta mode
        if delta_mode:
            report_data["metadata"]["delta"] = {
                "mode": True,
                "base_ref": delta_base_ref,
                "diff": diff_result.raw_diff if diff_result else "",
                "files_changed": changed_rel_paths
            }

        # 8. Prompt Building (Delta or Full)
        if config.use_ai:
            context_builder = ContextBuilder()
            if delta_mode:
                # Delta mode: load base report and build delta prompt
                base_report = self._find_base_report(root_path, base_ref=delta_base_ref)
                prompt = context_builder.build_delta_prompt(
                    current_metrics=base_metrics,
                    current_issues=issues,
                    current_ghosts=ghosts,
                    current_flags=flags,
                    diff_text=diff_result.raw_diff if diff_result else "",
                    base_report=base_report
                )
            else:
                # Full analysis prompt
                prompt = context_builder.build_prompt(
                    metrics=base_metrics,
                    issues=issues,
                    ghosts=ghosts,
                    flags=flags,
                    coupling_metrics=coupling_metrics,
                    import_edges=import_edges,
                    patch=config.patch,
                    symbol_index=symbol_index
                )
            report_data["ai_prompt"] = prompt

        # 9. Cache pre-synthesis
        if fingerprint is not None:
            report_data["metadata"]["fingerprint"] = fingerprint
            if use_cache and self.cache is not None:
                await asyncio.to_thread(self.cache.set, fingerprint, report_data)

        return ArchitectureReport(**report_data)
