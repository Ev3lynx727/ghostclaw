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
        parser.add_argument("--base", dest="delta_base_ref", default="HEAD~1", help="Git reference to diff against (branch, tag, commit). Default: HEAD~1")

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

        repo_path = args.repo_path
        use_cache = not args.no_cache

        # Build overrides
        cli_overrides = {}
        if args.use_ai: cli_overrides['use_ai'] = True
        elif args.no_ai: cli_overrides['use_ai'] = False
        if args.ai_provider: cli_overrides['ai_provider'] = args.ai_provider
        if args.ai_model: cli_overrides['ai_model'] = args.ai_model
        if args.dry_run: cli_overrides['dry_run'] = True
        if args.verbose: cli_overrides['verbose'] = True
        if args.patch: cli_overrides['patch'] = True
        # Delta mode (v0.1.10)
        if args.delta: cli_overrides['delta_mode'] = True
        if args.delta_base_ref: cli_overrides['delta_base_ref'] = args.delta_base_ref
        if args.pyscn: cli_overrides['use_pyscn'] = True
        elif args.no_pyscn: cli_overrides['use_pyscn'] = False
        if args.ai_codeindex: cli_overrides['use_ai_codeindex'] = True
        elif args.no_ai_codeindex: cli_overrides['use_ai_codeindex'] = False
        if args.no_parallel: cli_overrides['parallel_enabled'] = False
        if args.concurrency_limit is not None: cli_overrides['concurrency_limit'] = args.concurrency_limit

        # Handle --no-parallel with smart warnings and auto-correction for large repos
        if args.no_parallel:
            LARGE_REPO_THRESHOLD = 5000
            file_count = estimate_repo_file_count(repo_path)
            if file_count > LARGE_REPO_THRESHOLD:
                # Auto-correct: force parallel for large repos
                cli_overrides['parallel_enabled'] = True
                print(
                    f"⚡ Auto-enabling parallel processing: repository contains ~{file_count} files "
                    f"(threshold: {LARGE_REPO_THRESHOLD}).\n"
                    "   --no-parallel would be prohibitively slow on a repo of this size.\n"
                    "   If you need sequential processing for debugging, analyze a smaller subdirectory "
                    "or adjust the threshold in the source.\n",
                    file=sys.stderr
                )
            else:
                # Standard warning for smaller repos
                print(
                    "⚠️  WARNING: --no-parallel is ~300× slower and may cause timeouts.\n"
                    "   Parallel processing is the default and strongly recommended.\n"
                    "   Only use --no-parallel for debugging specific issues.\n"
                    "   Remove this flag or set 'parallel_enabled': true in ~/.ghostclaw/ghostclaw.json\n",
                    file=sys.stderr
                )

        try:
            service = AnalyzerService(
                repo_path=repo_path,
                config_overrides=cli_overrides,
                use_cache=use_cache,
                cache_dir=args.cache_dir,
                cache_ttl=args.cache_ttl,
                json_output=args.json,
                benchmark=args.benchmark
            )
            report = await service.run()
        except Exception as e:
            if args.pdb:
                print("\n\x1b[31m⚠️  Debugger enabled. Entering pdb post-mortem session.\x1b[0m", file=sys.stderr)
                print("   Exception:", e, file=sys.stderr)
                print("   Type 'c' to continue to full traceback, 'bt' for backtrace, 'quit' to exit.\n", file=sys.stderr)
                # Provide locals/globals for inspection
                import traceback
                tb = sys.exc_info()[2]
                pdb.post_mortem(tb)
            else:
                print(str(e), file=sys.stderr)
            return 1

        # Formatters
        if args.json:
            print(JSONFormatter().format(report))
        else:
            TerminalFormatter().print_to_terminal(report)

        # Output extra info
        info_file = sys.stderr if args.json else sys.stdout

        if args.benchmark and service.timings:
            print("\n=== Benchmark Results (seconds) ===", file=sys.stderr)
            for phase, duration in sorted(service.timings.items()):
                print(f"{phase:20} {duration:>8.3f}s", file=sys.stderr)
            if use_cache and service.cache:
                info = service.cache.info()
                print(f"Cache entries: {info['entries']}, size: {info['total_size_bytes']} bytes", file=sys.stderr)

        # Show token usage if requested
        if getattr(args, 'show_tokens', False):
            tokens = report.get('metadata', {}).get('tokens')
            if tokens:
                print("\n=== Token Usage ===", file=sys.stderr)
                print(f"Prompt tokens:     {tokens.get('prompt', 0):>10}", file=sys.stderr)
                print(f"Completion tokens: {tokens.get('completion', 0):>10}", file=sys.stderr)
                print(f"Total tokens:      {tokens.get('total', 0):>10}", file=sys.stderr)
            else:
                print("\n⚠️  No token data available (AI synthesis may have been disabled or failed).", file=sys.stderr)

        report_file_path = None
        if not args.no_write_report:
            now = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            # Determine if delta mode from report metadata (set by analyzer)
            is_delta = report.get("metadata", {}).get("delta", {}).get("mode", False)
            if is_delta:
                filename = f"ARCHITECTURE-DELTA-{now}.md"
            else:
                filename = f"ARCHITECTURE-REPORT-{now}.md"

            if args.create_pr:
                report_dir = Path(repo_path)
            else:
                report_dir = Path(repo_path) / ".ghostclaw"
                report_dir.mkdir(parents=True, exist_ok=True)
                gitignore_path = Path(repo_path) / ".gitignore"
                if gitignore_path.exists():
                    content = gitignore_path.read_text(encoding='utf-8')
                    if ".ghostclaw" not in content and ".ghostclaw/" not in content:
                        newline = "\n" if not content.endswith("\n") else ""
                        with open(gitignore_path, "a", encoding="utf-8") as f:
                            f.write(f"{newline}# Added by Ghostclaw\n.ghostclaw/\n")

            report_file_path = report_dir / filename
            try:
                report_file_path.write_text(MarkdownFormatter().format(report), encoding='utf-8')
                print(f"📝 Report written to: {report_file_path.absolute()}", file=info_file)
                # Write JSON for machine-readable access (used by delta mode)
                json_path = report_file_path.with_suffix('.json')
                json_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
            except Exception as e:
                print(f"Error writing report: {e}", file=sys.stderr)

        remote_url = detect_github_remote(repo_path)
        if remote_url and not args.create_pr:
            print(f"💡 Tip: This repository has a GitHub remote.", file=info_file)
            print(f"   To create a PR with this report, run:", file=info_file)
            print(f"   ghostclaw analyze \"{repo_path}\" --create-pr", file=info_file)

        if args.create_pr:
            if not report_file_path:
                print("Error: Report file missing.", file=sys.stderr)
            else:
                title = args.pr_title or f"🏰 Architecture Report - {datetime.datetime.now().strftime('%Y-%m-%d')}"
                body = args.pr_body or f"Ghostclaw has completed an architectural review of the codebase.\n\n**Vibe Score: {report['vibe_score']}/100**\n\nPlease review the attached report for details."
                pr_service = PRService(repo_path)
                try:
                    await pr_service.create_pr(report_file_path, title, body)
                except Exception:
                    pass
                finally:
                    try:
                        report_file_path.unlink(missing_ok=True)
                    except Exception as e:
                        print(f"Warning: could not delete temporary PR report: {e}", file=sys.stderr)

        if args.cache_stats and use_cache and service.cache:
            info = service.cache.info()
            print(f"📊 Cache: {info['entries']} entries, {info['total_size_bytes']} bytes total ({info['cache_dir']})", file=info_file)

        if not args.json and report.get('metadata', {}).get('cache_hit'):
            print("⚡ Cache hit!", file=sys.stderr)

        if args.strict and report.get('errors'):
            print(f"❌ {len(report['errors'])} adapter error(s) occurred (--strict). Exiting with failure.", file=sys.stderr)
            return 1

        return 0
