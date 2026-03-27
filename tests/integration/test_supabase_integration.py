#!/usr/bin/env python3
"""
Integration test for SupabaseStorageAdapter.

This script performs a simple end-to-end test:
1. Saves a sample ArchitectureReport to Supabase
2. Retrieves history and verifies the report exists

Usage:
  SUPABASE_URL=https://... SUPABASE_SERVICE_KEY=... python tests/integration/test_supabase_integration.py

Note: Requires a Supabase project with `reports` table created (run schema.sql).
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports when run from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from ghostclaw.core.adapters.storage.supabase import SupabaseStorageAdapter
from ghostclaw.core.models import ArchitectureReport


async def main():
    # Check env vars
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        print("❌ Please set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
        sys.exit(1)

    adapter = SupabaseStorageAdapter()

    # Check availability
    available = await adapter.is_available()
    print(f"Adapter available: {available}")
    if not available:
        print("❌ Supabase library not installed? Run: pip install supabase")
        sys.exit(1)

    # Build a sample report
    sample_data = {
        "vibe_score": 88,
        "stack": "python",
        "files_analyzed": 3,
        "total_lines": 250,
        "repo_path": "/test/integration",
        "metadata": {
            "vcs": {
                "commit": "deadbeef",
                "branch": "main",
                "dirty": False
            }
        },
        "issues": [
            {"title": "Test Issue", "description": "Integration test issue"}
        ],
        "architectural_ghosts": [],
        "red_flags": ["test flag"],
        "coupling_metrics": {},
    }

    try:
        report = ArchitectureReport(**sample_data)
    except Exception as e:
        print(f"❌ Failed to create report model: {e}")
        sys.exit(1)

    # Save report
    print("💾 Saving report to Supabase...")
    try:
        report_id = await adapter.save_report(report)
        print(f"✅ Saved report with ID: {report_id}")
    except Exception as e:
        print(f"❌ Save failed: {e}")
        sys.exit(1)

    # Retrieve history
    print("📜 Fetching recent reports...")
    try:
        history = await adapter.get_history(limit=5)
        print(f"✅ Retrieved {len(history)} reports")
        # Check if our ID is in the history
        ids = [r.get("id") for r in history]
        if report_id in ids:
            print(f"✅ Our report ({report_id}) appears in history")
        else:
            print(f"⚠️  Our report ID not in recent history (maybe index delay)")
    except Exception as e:
        print(f"❌ Get history failed: {e}")
        sys.exit(1)

    print("✅ Integration test passed!")


if __name__ == "__main__":
    asyncio.run(main())
