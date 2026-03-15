"""Storage layout migration utilities."""

import shutil
from pathlib import Path


def migrate_legacy_storage(repo_path: Path) -> bool:
    """
    Migrate old .ghostclaw/{reports,cache,ghostclaw.db} layout to new .ghostclaw/storage/ layout.
    Returns True if migration was performed, False otherwise.
    """
    gc_dir = repo_path / ".ghostclaw"
    old_reports = gc_dir / "reports"
    old_cache = gc_dir / "cache"
    old_db = gc_dir / "ghostclaw.db"

    new_storage = gc_dir / "storage"
    new_reports = new_storage / "reports"
    new_cache = new_storage / "cache"
    new_db = new_storage / "ghostclaw.db"

    moved_any = False

    # Migrate reports directory
    if old_reports.exists() and old_reports.is_dir():
        if not new_reports.exists():
            shutil.move(str(old_reports), str(new_reports))
            print(f"  Migrated reports: {old_reports} → {new_reports}")
            moved_any = True
        else:
            # Merge: move contents if new exists
            for item in old_reports.iterdir():
                dest = new_reports / item.name
                if not dest.exists():
                    shutil.move(str(item), str(dest))
            try:
                old_reports.rmdir()
            except OSError:
                pass
            print(f"  Merged reports into {new_reports}")
            moved_any = True

    # Migrate cache directory
    if old_cache.exists() and old_cache.is_dir():
        if not new_cache.exists():
            shutil.move(str(old_cache), str(new_cache))
            print(f"  Migrated cache: {old_cache} → {new_cache}")
            moved_any = True
        else:
            for item in old_cache.iterdir():
                dest = new_cache / item.name
                if not dest.exists():
                    shutil.move(str(item), str(dest))
            old_cache.rmdir()
            print(f"  Merged cache into {new_cache}")
            moved_any = True

    # Migrate SQLite database
    if old_db.exists() and old_db.is_file():
        if not new_db.exists():
            shutil.move(str(old_db), str(new_db))
            print(f"  Migrated database: {old_db} → {new_db}")
            moved_any = True
        else:
            # Both exist: keep new, leave old as backup (don't delete)
            pass

    return moved_any
