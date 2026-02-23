#!/usr/bin/env python3
"""
Ghostclaw Compare — show a table of current vs previous vibe scores.

Usage:
  ghostclaw-compare --repos-file repos.txt [--cache-file ~/.cache/ghostclaw/vibe_history.json]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from lib.cache import VibeCache
from core.analyzer import CodebaseAnalyzer

load_dotenv()


def load_repos(repos_file: Path) -> List[str]:
    """Read repository URLs from file."""
    if not repos_file.exists():
        print(f"Error: repos file not found: {repos_file}", file=sys.stderr)
        sys.exit(1)
    return [line.strip() for line in repos_file.read_text().splitlines()
            if line.strip() and not line.startswith('#')]


def main():
    parser = argparse.ArgumentParser(description="Ghostclaw Compare — view vibe score trends")
    parser.add_argument(
        "--repos-file",
        required=True,
        help="Path to file containing repository URLs or paths (one per line)"
    )
    parser.add_argument(
        "--cache-file",
        default=str(Path.home() / ".cache" / "ghostclaw" / "vibe_history.json"),
        help="Path to vibe history JSON cache"
    )
    parser.add_argument(
        "--work-dir",
        help="Directory where repos are cloned (if using URLs); if omitted, repos are assumed to be local paths"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-analyze all repos instead of using cached current scores"
    )

    args = parser.parse_args()

    repos_file = Path(args.repos_file)
    repos = load_repos(repos_file)

    cache = VibeCache(cache_dir=Path(args.cache_file).parent)
    work_dir = Path(args.work_dir) if args.work_dir else None

    rows = []
    for repo_url in repos:
        # Get previous score from cache
        history = cache.get_history(repo_url)
        prev_score = history[-1]["vibe_score"] if history else None

        # Get current score
        if args.refresh:
            # Force re-analysis
            if work_dir:
                repo_name = repo_url.rstrip('/').split('/')[-1]
                repo_path = work_dir / repo_name
                if repo_path.exists():
                    try:
                        report = CodebaseAnalyzer().analyze(str(repo_path))
                        curr_score = report['vibe_score']
                        cache.record_score(repo_url, curr_score)
                    except Exception:
                        curr_score = None
                else:
                    curr_score = None
            else:
                try:
                    report = CodebaseAnalyzer().analyze(repo_url)
                    curr_score = report['vibe_score']
                    cache.record_score(repo_url, curr_score)
                except Exception:
                    curr_score = None
        else:
            # Use latest from cache
            curr_score = cache.get_latest_score(repo_url)

        # Compute delta
        if prev_score is not None and curr_score is not None:
            delta = curr_score - prev_score
        else:
            delta = None

        rows.append((repo_url, curr_score, prev_score, delta))

    print("\n=== Ghostclaw Repository Health Overview ===\n")
    print(f"Repositories: {len(repos)}")
    print(f"Cache: {args.cache_file}")
    print()

    if not rows:
        print("No data.")
        return

    # Header
    header = f"{'Repository':40} {'Current':8} {'Previous':8} {'Delta':6} {'Status'}"
    print(header)
    print("-" * len(header))

    for repo, curr, prev, delta in rows:
        # Determine status emoji
        if curr is None:
            status_emoji = "❓"
            status_text = "N/A"
        elif curr >= 80:
            status_emoji = "🟢"
            status_text = f"{curr}/100"
        elif curr >= 60:
            status_emoji = "🟡"
            status_text = f"{curr}/100"
        elif curr >= 40:
            status_emoji = "🟠"
            status_text = f"{curr}/100"
        else:
            status_emoji = "🔴"
            status_text = f"{curr}/100"

        delta_str = f"{delta:+d}" if delta is not None else "---"
        print(f"{repo[:40]:40} {status_text:8} {str(prev) if prev else '---':8} {delta_str:6} {status_emoji}")

    print()

    # Summary
    scores = [r[1] for r in rows if r[1] is not None]
    if scores:
        avg = sum(scores) / len(scores)
        healthy = sum(1 for s in scores if s >= 60)
        print(f"📊 Average vibe: {avg:.1f}/100 across {len(scores)} repos")
        print(f"✅ Healthy (≥60): {healthy}/{len(scores)}")


if __name__ == "__main__":
    main()
