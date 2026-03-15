import sys
import json
import datetime
import pdb
import os
from pathlib import Path
from typing import Dict, Any, Optional

from argparse import ArgumentParser, Namespace

from ghostclaw.cli.commander import Command
from ghostclaw.cli.services import AnalyzerService
from ghostclaw.cli.services import PRService
from ghostclaw.cli.formatters import MarkdownFormatter
from ghostclaw.cli.formatters import TerminalFormatter
from ghostclaw.cli.formatters import JSONFormatter
import subprocess

def detect_github_remote(repo_path: str) -> Optional[str]:
    """Detect if the repository has a GitHub remote (origin)."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            if "github.com" in url:
                return url
    except Exception:
        pass
    return None

def estimate_repo_file_count(repo_path: str) -> int:
    """Estimate the number of files in the repository, excluding common non-source dirs."""
    repo = Path(repo_path)
    if not repo.exists():
        return 0

    exclude_dirs = {
        '.git', 'node_modules', 'venv', '.venv', 'env', 'virtualenv',
        '__pycache__', '.pytest_cache', 'build', 'dist', 'target', 'bin', 'obj',
        '.idea', '.vscode', '.cache', 'tmp', 'temp', 'coverage', '.coverage', 'htmlcov',
        '.next', '.nuxt', 'out', 'turbo', '.turbo'
    }
    exclude_extensions = {
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.bin', '.obj', '.o', '.a', '.lib',
        '.class', '.jar', '.war', '.ear', '.log', '.cache', '.pid', '.lock',
        '.sqlite', '.db', '.sqlite3', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.ico',
        '.pdf', '.zip', '.tar', '.gz', '.tgz', '.rar', '.7z'
    }

    count = 0
    try:
        for root, dirs, files in os.walk(repo):
            # Skip excluded directories (modify dirs in-place to prevent walking into them)
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            for file in files:
                if file.startswith('.'):
                    continue
                if any(file.lower().endswith(ext) for ext in exclude_extensions):
                    continue
                count += 1
                # Early exit if count already exceeds threshold (performance)
                if count > 10000:
                    return count
    except Exception:
        return 0
    return count

class AnalyzeCommand(Command):
    """
    Command to analyze codebase architecture.
    """

    @property
    def name(self) -> str:
        return "analyze"

    @property
    def description(self) -> str:
        return "Analyze codebase architecture"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("repo_path", nargs="?", default=".", help="Path to the repository to analyze")
        parser.add_argument("--json", action="store_true", help="Output raw JSON")
        parser.add_argument("--no-write-report", action="store_true", help="Skip writing the .md report file")
        parser.add_argument("--create-pr", action="store_true", help="Automatically create a GitHub PR with the report")
        parser.add_argument("--pr-title", help="Custom PR title")
        parser.add_argument("--pr-body", help="Custom PR body")

        # Delta-Context Mode (v0.1.10)
        parser.add_argument("--delta", action="store_true", help="Enable delta-context analysis (PR-style review on diffs)")
        parser.add_argument("--base", dest="delta_base_ref", default=None, help="Git reference to diff against (branch, tag, commit). Default: from config (HEAD~1)")
        parser.add_argument("--delta-summary", action="store_true", help="Print diff statistics (files changed, insertions, deletions)")

        # QMD backend (v0.2.0)
        parser.add_argument("--use-qmd", action="store_true", help="Use QMD (Quantum Memory Database) backend for memory operations (experimental)")
        parser.add_argument("--embedding-backend", choices=["sentence-transformers", "fastembed", "openai"], help="Embedding backend for QMD hybrid search (default: sentence-transformers)")

        # Caching options
        parser.add_argument("--no-cache", action="store_true", help="Disable result caching")
        parser.add_argument("--cache-dir", type=Path, help="Custom cache directory (default: ~/.cache/ghostclaw)")
        parser.add_argument("--cache-ttl", type=int, default=7, help="Cache TTL in days (default: 7)")
        parser.add_argument("--cache-stats", action="store_true", help="Show cache statistics after analysis")

        # Parallel processing options
        parser.add_argument(
            "--no-parallel",
            action="store_true",
            help="Disable parallel file scanning (⚠️ WARNING: causes 300× slowdown. Only use for debugging.)"
        )
        parser.add_argument("--concurrency-limit", type=int, help="Max concurrent file operations (default: 32)")

        # AI options
        parser.add_argument("--use-ai", action="store_true", help="Enable Ghost Engine AI synthesis")
        parser.add_argument("--no-ai", action="store_true", help="Explicitly disable Ghost Engine AI synthesis")
        parser.add_argument("--ai-provider", help="AI Provider (openrouter, openai, anthropic)")
        parser.add_argument("--ai-model", help="Specific LLM model to use")
        parser.add_argument("--dry-run", action="store_true", help="Dry run mode: prints prompt and token count without API call")
        parser.add_argument("--verbose", action="store_true", help="Verbose mode: saves raw API requests/responses to debug.log")
        parser.add_argument("--patch", action="store_true", help="Enable refactor plan/patch suggestions from the AI engine")

        # Engine Integrations
        parser.add_argument("--pyscn", action="store_true", help="Enable PySCN integration")
        parser.add_argument("--no-pyscn", action="store_true", help="Explicitly disable PySCN integration")
        parser.add_argument("--ai-codeindex", action="store_true", help="Enable AI-CodeIndex integration")
        parser.add_argument("--no-ai-codeindex", action="store_true", help="Explicitly disable AI-CodeIndex integration")

        # Reliability
        parser.add_argument("--strict", action="store_true", help="Treat adapter errors as fatal (non-zero exit)")

        # Observability & Debugging
        parser.add_argument("--benchmark", action="store_true", help="Print performance timings after analysis")
        parser.add_argument(
            "--pdb",
            action="store_true",
            help="Drop into pdb post-mortem debugger on error (for development only)"
        )
        parser.add_argument(
            "--show-tokens",
            action="store_true",
            help="Show token usage statistics after AI synthesis (if --use-ai)"
        )

    def validate(self, args: Namespace) -> None:
        if not Path(args.repo_path).is_dir():
            print(f"Error: directory not found: {args.repo_path}", file=sys.stderr)
            sys.exit(1)

    async def execute(self, args: Namespace) -> int:
        self.validate(args)
        try:
            return await self._execute_impl(args)
        except Exception as e:
            if args.pdb:
                print("\n\x1b[31m⚠️  Debugger enabled. Entering pdb post-mortem session.\x1b[0m", file=sys.stderr)
                print("   Exception:", e, file=sys.stderr)
                print("   Type 'c' to continue to full traceback, 'bt' for backtrace, 'quit' to exit.\n", file=sys.stderr)
                import traceback
                tb = sys.exc_info()[2]
                pdb.post_mortem(tb)
            else:
                print(str(e), file=sys.stderr)
            return 1

    async def _execute_impl(self, args: Namespace) -> int:
        cli_overrides = self._build_cli_overrides(args)
        self._handle_parallel_warning(args, cli_overrides)

        report, service = await self._run_analysis(args.repo_path, cli_overrides, args)

        self._print_delta_summary(report)
        self._format_and_print_report(report, args)

        report_file_path = None
        if not args.no_write_report:
            report_file_path = await self._write_report(report, args)

        if args.create_pr:
            await self._handle_pr_creation(report, report_file_path, args.repo_path, args)

        self._print_auxiliary_info(report, service, args)
        return 0

    def _build_cli_overrides(self, args: Namespace) -> Dict[str, Any]:
        overrides: Dict[str, Any] = {}
        # AI flags
        if args.use_ai:
            overrides['use_ai'] = True
        elif args.no_ai:
            overrides['use_ai'] = False
        if args.ai_provider:
            overrides['ai_provider'] = args.ai_provider
        if args.ai_model:
            overrides['ai_model'] = args.ai_model
        # Behavior flags
        if args.dry_run:
            overrides['dry_run'] = True
        if args.verbose:
            overrides['verbose'] = True
        if args.patch:
            overrides['patch'] = True
        # Delta mode (v0.1.10)
        if args.delta:
            overrides['delta_mode'] = True
        if args.delta_base_ref is not None:
            overrides['delta_base_ref'] = args.delta_base_ref
        # QMD backend (v0.2.0)
        if args.use_qmd:
            overrides['use_qmd'] = True
        if getattr(args, 'embedding_backend', None):
            overrides['embedding_backend'] = args.embedding_backend
        # Engine integrations
        if args.pyscn:
            overrides['use_pyscn'] = True
        elif args.no_pyscn:
            overrides['use_pyscn'] = False
        if args.ai_codeindex:
            overrides['use_ai_codeindex'] = True
        elif args.no_ai_codeindex:
            overrides['use_ai_codeindex'] = False
        # Performance tuning
        if args.no_parallel:
            overrides['parallel_enabled'] = False
        if args.concurrency_limit is not None:
            overrides['concurrency_limit'] = args.concurrency_limit
        return overrides

    def _handle_parallel_warning(self, args: Namespace, overrides: Dict[str, Any]) -> None:
        if not args.no_parallel:
            return
        LARGE_REPO_THRESHOLD = 5000
        file_count = estimate_repo_file_count(args.repo_path)
        if file_count > LARGE_REPO_THRESHOLD:
            overrides['parallel_enabled'] = True
            print(
                f"⚡ Auto-enabling parallel processing: repository contains ~{file_count} files "
                f"(threshold: {LARGE_REPO_THRESHOLD}).\n"
                "   --no-parallel would be prohibitively slow on a repo of this size.\n"
                "   If you need sequential processing for debugging, analyze a smaller subdirectory "
                "or adjust the threshold in the source.\n",
                file=sys.stderr
            )
        else:
            print(
                "⚠️  WARNING: --no-parallel is ~300× slower and may cause timeouts.\n"
                "   Parallel processing is the default and strongly recommended.\n"
                "   Only use --no-parallel for debugging specific issues.\n"
                "   Remove this flag or set 'parallel_enabled': true in ~/.ghostclaw/ghostclaw.json\n",
                file=sys.stderr
            )

    async def _run_analysis(self, repo_path: str, cli_overrides: Dict[str, Any], args: Namespace):
        service = AnalyzerService(
            repo_path=repo_path,
            config_overrides=cli_overrides,
            use_cache=not args.no_cache,
            cache_dir=args.cache_dir,
            cache_ttl=args.cache_ttl,
            json_output=args.json,
            benchmark=args.benchmark
        )
        report = await service.run()
        return report, service

    def _print_delta_summary(self, report: Dict[str, Any]) -> None:
        if not report.get("metadata", {}).get("delta", {}).get("mode"):
            return
        diff_text = report["metadata"]["delta"].get("diff", "")
        if not diff_text:
            return
        files_changed = len(report["metadata"]["delta"].get("files_changed", []))
        insertions = deletions = 0
        for line in diff_text.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                insertions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1
        print("\n=== Delta Summary ===", file=sys.stderr)
        print(f"Files changed: {files_changed}", file=sys.stderr)
        print(f"Insertions: +{insertions}", file=sys.stderr)
        print(f"Deletions: -{deletions}", file=sys.stderr)

    def _format_and_print_report(self, report: Dict[str, Any], args: Namespace) -> None:
        if args.json:
            print(JSONFormatter().format(report))
        else:
            TerminalFormatter().print_to_terminal(report)

    async def _write_report(self, report: Dict[str, Any], args: Namespace) -> Optional[Path]:
        now = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        repo_path = Path(args.repo_path)
        is_delta = report.get("metadata", {}).get("delta", {}).get("mode", False)
        filename = f"ARCHITECTURE-DELTA-{now}.md" if is_delta else f"ARCHITECTURE-REPORT-{now}.md"

        if args.create_pr:
            report_dir = repo_path
        else:
            report_dir = repo_path / ".ghostclaw" / "storage" / "reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            gitignore_path = repo_path / ".gitignore"
            if gitignore_path.exists():
                content = gitignore_path.read_text(encoding='utf-8')
                if ".ghostclaw" not in content and ".ghostclaw/" not in content:
                    newline = "\n" if not content.endswith("\n") else ""
                    with open(gitignore_path, "a", encoding="utf-8") as f:
                        f.write(f"{newline}# Added by Ghostclaw\n.ghostclaw/\n")

        report_file_path = report_dir / filename
        try:
            report_file_path.write_text(MarkdownFormatter().format(report), encoding='utf-8')
            print(f"📝 Report written to: {report_file_path.absolute()}", file=sys.stderr)
            json_path = report_file_path.with_suffix('.json')
            json_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
            return report_file_path
        except Exception as e:
            print(f"Error writing report: {e}", file=sys.stderr)
            return None

    async def _handle_pr_creation(self, report: Dict[str, Any], report_path: Optional[Path], repo_path: str, args: Namespace) -> None:
        if not report_path:
            print("Error: Report file missing.", file=sys.stderr)
            return
        title = args.pr_title or f"🏰 Architecture Report - {datetime.datetime.now().strftime('%Y-%m-%d')}"
        default_body = f"Ghostclaw has completed an architectural review of the codebase.\n\n**Vibe Score: {report['vibe_score']}/100**\n\nPlease review the attached report for details."
        body = args.pr_body or default_body
        pr_service = PRService(repo_path)
        try:
            await pr_service.create_pr(report_path, title, body)
        except Exception:
            pass
        finally:
            try:
                report_path.unlink(missing_ok=True)
                json_path = report_path.with_suffix('.json')
                json_path.unlink(missing_ok=True)
            except Exception as e:
                print(f"Warning: could not delete temporary PR report: {e}", file=sys.stderr)

    def _print_auxiliary_info(self, report: Dict[str, Any], service, args: Namespace) -> None:
        info_file = sys.stderr if args.json else sys.stdout
        # Benchmark results
        if args.benchmark and getattr(service, 'timings', None):
            print("\n=== Benchmark Results (seconds) ===", file=sys.stderr)
            for phase, duration in sorted(service.timings.items()):
                print(f"{phase:20} {duration:>8.3f}s", file=sys.stderr)
            if not args.no_cache and getattr(service, 'cache', None):
                try:
                    info = service.cache.info()
                    print(f"Cache entries: {info['entries']}, size: {info['total_size_bytes']} bytes", file=sys.stderr)
                except Exception:
                    pass
        # Token usage
        if getattr(args, 'show_tokens', False):
            tokens = report.get('metadata', {}).get('tokens')
            if tokens:
                print("\n=== Token Usage ===", file=sys.stderr)
                print(f"Prompt tokens:     {tokens.get('prompt', 0):>10}", file=sys.stderr)
                print(f"Completion tokens: {tokens.get('completion', 0):>10}", file=sys.stderr)
                print(f"Total tokens:      {tokens.get('total', 0):>10}", file=sys.stderr)
            else:
                print("\n⚠️  No token data available (AI synthesis may have been disabled or failed).", file=sys.stderr)
        # Cache hit indicator
        if not args.json and report.get('metadata', {}).get('cache_hit'):
            print("⚡ Cache hit!", file=sys.stderr)
        # Cache stats
        if args.cache_stats and not args.no_cache and getattr(service, 'cache', None):
            try:
                info = service.cache.info()
                print(f"📊 Cache: {info['entries']} entries, {info['total_size_bytes']} bytes total ({info['cache_dir']})", file=info_file)
            except Exception:
                pass
        # GitHub tip
        remote_url = detect_github_remote(args.repo_path)
        if remote_url and not args.create_pr:
            print(f"💡 Tip: This repository has a GitHub remote.", file=info_file)
            print(f"   To create a PR with this report, run:", file=info_file)
            print(f"   ghostclaw analyze \"{args.repo_path}\" --create-pr", file=info_file)
        # Strict mode check
        if args.strict and report.get('errors'):
            print(f"❌ {len(report['errors'])} adapter error(s) occurred (--strict).", file=sys.stderr)
