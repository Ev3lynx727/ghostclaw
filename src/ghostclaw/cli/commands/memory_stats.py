"""CLI command: ghostclaw memory stats — Show QMD memory store statistics."""

import argparse
import json
from pathlib import Path

from ghostclaw.core.qmd_store import QMDMemoryStore
from ghostclaw.core.config import GhostclawConfig
from ghostclaw.cli.commander import Command


class MemoryStatsCommand(Command):
    """Show performance statistics for QMD memory store."""

    @property
    def name(self) -> str:
        return "memory-stats"

    @property
    def description(self) -> str:
        return "Display QMD memory store statistics (cache hit rates, sizes)"

    def configure_parser(self, parser: argparse.ArgumentParser):
        parser.add_argument(
            "--repo",
            type=Path,
            default=Path.cwd(),
            help="Repository path (default: current directory)",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output in JSON format",
        )

    async def execute(self, args):
        repo_path = args.repo or Path.cwd()
        try:
            cfg = GhostclawConfig.load(repo_path)
        except Exception:
            cfg = None

        if not cfg or not getattr(cfg, 'use_qmd', False):
            print("⚠️  QMD is not enabled in configuration (use_qmd=false)")
            print("Enable with: ghostclaw config set use_qmd true")
            return 0

        db_path = repo_path / ".ghostclaw" / "storage" / "qmd" / "ghostclaw.db"
        if not db_path.exists():
            print(f"⚠️  QMD database not found at {db_path}")
            print("Run an analysis first: ghostclaw analyze . --use-qmd")
            return 1

        store = QMDMemoryStore(
            db_path=db_path,
            use_enhanced=True,
            embedding_backend=getattr(cfg, 'embedding_backend', 'fastembed'),
            ai_buff_enabled=getattr(cfg, 'ai_buff_enabled', False)
        )
        stats = store.get_stats()

        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            self._print_human(stats)
        return 0

    def _print_human(self, stats: dict):
        print("=== QMD Memory Store Statistics ===")
        if 'embedding_cache' in stats and stats['embedding_cache']:
            ec = stats['embedding_cache']
            print(f"\nEmbedding Cache:")
            print(f"  Size: {ec['size']}/{ec['maxsize']}")
            print(f"  Hit rate: {ec['hit_rate']*100:.1f}% ({ec['hits']} hits, {ec['misses']} misses)")
        else:
            print("\nEmbedding Cache: disabled")

        if 'search_cache' in stats and stats['search_cache']:
            sc = stats['search_cache']
            print(f"\nSearch Result Cache:")
            print(f"  Size: {sc['size']}/{sc['maxsize']}")
            print(f"  Hit rate: {sc['hit_rate']*100:.1f}% ({sc['hits']} hits, {sc['misses']} misses)")
        else:
            print("\nSearch Result Cache: disabled")

        print("\nNote: Caches are per-process and reset on restart.")
