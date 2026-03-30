"""CLI command: ghostclaw storage migrate — Migrate data between storage backends."""

import argparse
import json
import sqlite3
from pathlib import Path

from ghostclaw.cli.commander import Command


class StorageMigrateCommand(Command):
    """Migrate architectural reports from one storage backend to another."""

    @property
    def name(self) -> str:
        """
        Command name for the storage migration CLI.
        
        Returns:
            str: The command name "storage-migrate".
        """
        return "storage migrate"

    @property
    def description(self) -> str:
        """
        Command description for the storage-migrate CLI command.
        
        Returns:
            A short description string used in CLI help and command listings.
        """
        return "Migrate reports from SQLite to Supabase (or other storage backends)"

    def configure_parser(self, parser: argparse.ArgumentParser):
        """
        Register CLI arguments for the `storage-migrate` command.
        
        Adds options to select source and target backends, provide SQLite and Supabase connection info,
        and control migration behavior (dry run, batch size, omit IDs, upsert, and repository path).
        
        Parameters:
            parser (argparse.ArgumentParser): The argument parser to configure with command options.
        """
        parser.add_argument(
            "--from",
            dest="source",
            choices=["sqlite"],
            default="sqlite",
            help="Source storage backend (currently only sqlite supported)",
        )
        parser.add_argument(
            "--to",
            dest="target",
            choices=["supabase"],
            default="supabase",
            help="Target storage backend (currently only supabase supported)",
        )
        parser.add_argument(
            "--sqlite-db",
            type=Path,
            default=None,
            help="Path to SQLite database (default: .ghostclaw/storage/ghostclaw.db)",
        )
        parser.add_argument(
            "--supabase-url",
            type=str,
            default=None,
            help="Supabase project URL (overrides env SUPABASE_URL)",
        )
        parser.add_argument(
            "--supabase-key",
            type=str,
            default=None,
            help="Supabase service role key (overrides env SUPABASE_SERVICE_KEY)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview migration without making changes",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of records to insert per batch (default: 100)",
        )
        parser.add_argument(
            "--omit-id",
            action="store_true",
            help="Omit record IDs to let target generate new ones",
        )
        parser.add_argument(
            "--upsert",
            action="store_true",
            help="Update existing records if IDs conflict (requires same IDs)",
        )
        parser.add_argument(
            "--repo",
            type=Path,
            default=Path.cwd(),
            help="Repository path (default: current directory)",
        )

    async def execute(self, args) -> int:
        """
        Run the storage-migrate command to migrate report records from a local SQLite database to a Supabase project.
        
        Parameters:
            args (argparse.Namespace): Parsed CLI arguments with the following relevant attributes:
                - source (str): Source backend name (must be "sqlite").
                - target (str): Target backend name (must be "supabase").
                - sqlite_db (Path | str | None): Path to the SQLite database file; if None a default path under the repository is used.
                - supabase_url (str | None): Supabase project URL; may be provided via SUPABASE_URL env var.
                - supabase_key (str | None): Supabase service key; may be provided via SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY env var.
                - dry_run (bool): If true, prints a preview and makes no changes.
                - batch_size (int): Number of records to send to Supabase per batch.
                - omit_id (bool): If true, removes the `id` field from records before inserting/upserting.
                - upsert (bool): If true, use upsert instead of insert when sending data to Supabase.
                - repo (Path | str | None): Repository path used to resolve the default SQLite location.
        
        Returns:
            int: Exit code where `0` indicates success and any non-zero value indicates a failure.
        """
        repo_path = args.repo or Path.cwd()

        if args.source != "sqlite":
            print(f"❌ Source '{args.source}' not supported yet.")
            return 1
        if args.target != "supabase":
            print(f"❌ Target '{args.target}' not supported yet.")
            return 1

        # Determine SQLite DB path
        if args.sqlite_db:
            sqlite_path = args.sqlite_db
        else:
            sqlite_path = repo_path / ".ghostclaw" / "storage" / "ghostclaw.db"

        if not sqlite_path.exists():
            print(f"❌ SQLite database not found at {sqlite_path}")
            return 1

        # Get Supabase credentials
        import os
        supabase_url = args.supabase_url or os.getenv("SUPABASE_URL")
        supabase_key = args.supabase_key or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

        if not supabase_url:
            print("❌ Supabase URL not provided. Set SUPABASE_URL env var or use --supabase-url.")
            return 1
        if not supabase_key:
            print("❌ Supabase key not provided. Set SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY env var, or use --supabase-key.")
            return 1

        if "your-project" in supabase_url.lower():
            print("❌ Please set a real Supabase URL (not the placeholder).")
            return 1

        print(f"🔍 Source: SQLite DB at {sqlite_path}")
        print(f"🎯 Target: Supabase at {supabase_url}")

        # Fetch reports from SQLite
        try:
            reports = self._fetch_sqlite_reports(sqlite_path)
        except Exception as e:
            print(f"❌ Failed to read SQLite: {e}")
            return 1

        print(f"📦 Found {len(reports)} reports to migrate")

        if args.dry_run:
            print("🧪 Dry-run mode: no changes will be made.")
            print("Would have migrated the following reports:")
            for r in reports[:5]:
                print(f"  - {r.get('id')}: {r.get('stack')} ({r.get('vibe_score')} vibe) at {r.get('timestamp')}")
            if len(reports) > 5:
                print(f"  ... and {len(reports)-5} more")
            return 0

        # Initialize Supabase client
        try:
            from supabase import create_client
            supabase = create_client(supabase_url, supabase_key)
        except ImportError:
            print("❌ supabase package not installed. Run: pip install supabase")
            return 1
        except Exception as e:
            print(f"❌ Failed to create Supabase client: {e}")
            return 1

        # Perform migration
        try:
            self._migrate_reports(supabase, reports, batch_size=args.batch_size, omit_id=args.omit_id, upsert=args.upsert)
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return 1

        print("✅ Migration completed successfully!")
        return 0

    def _fetch_sqlite_reports(self, sqlite_path: Path) -> list:
        """
        Load and normalize all records from the SQLite "reports" table.
        
        Each database row is converted to a dict. If a row's `timestamp` is a string in the format "YYYY-MM-DD HH:MM:SS", it is converted to an ISO 8601 string with a trailing "Z". If `report_json` is stored as a JSON string it is parsed to a Python object.
        
        Parameters:
            sqlite_path (Path): Path to the SQLite database file containing the `reports` table.
        
        Returns:
            list: A list of report dictionaries with normalized `timestamp` and `report_json` fields when applicable.
        """
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM reports ORDER BY id")
        rows = cur.fetchall()
        conn.close()

        reports = []
        for row in rows:
            r = dict(row)
            # Convert timestamp to ISO if needed
            if isinstance(r.get("timestamp"), str):
                try:
                    # SQLite default CURRENT_TIMESTAMP format: 'YYYY-MM-DD HH:MM:SS'
                    from datetime import datetime
                    dt = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
                    r["timestamp"] = dt.isoformat() + "Z"
                except Exception:
                    pass
            # Ensure report_json is dict (JSONB)
            if isinstance(r.get("report_json"), str):
                r["report_json"] = json.loads(r["report_json"])
            reports.append(r)
        return reports

    def _migrate_reports(self, supabase, reports: list, batch_size: int = 100, omit_id: bool = False, upsert: bool = False):
        """
        Migrate a list of report records into the Supabase "reports" table using batched inserts or upserts.
        
        Per-batch behavior: slices `reports` into batches of size `batch_size`, optionally removes the `"id"` key from each record when `omit_id` is True, and performs either `insert` or `upsert` against the Supabase client. Prints a progress line for each successful batch; on failure prints an error line for the batch and re-raises the exception.
        
        Parameters:
            supabase: Supabase client instance with a `.table("reports")` interface exposing `insert(...).execute()` and `upsert(...).execute()` methods.
            reports (list): List of report dictionaries to migrate.
            batch_size (int): Number of records to send per request.
            omit_id (bool): If True, remove the `"id"` key from records before sending.
            upsert (bool): If True use upsert operations; otherwise use insert.
        """
        total = len(reports)
        for i in range(0, total, batch_size):
            batch = reports[i:i+batch_size]

            if omit_id:
                for r in batch:
                    r.pop("id", None)

            try:
                if upsert:
                    supabase.table("reports").upsert(batch).execute()
                else:
                    supabase.table("reports").insert(batch).execute()
                print(f"✅ Batch {i//batch_size + 1}/{(total+batch_size-1)//batch_size} ({len(batch)} rows)")
            except Exception as e:
                print(f"❌ Error on batch {i//batch_size + 1}: {e}")
                raise
