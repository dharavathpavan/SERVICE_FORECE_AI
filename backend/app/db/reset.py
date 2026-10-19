"""Reset the platform to a clean, empty state.

Every row of business data is removed - organizations, users and memberships,
agents, knowledge bases, telephony connections and gateways, calls, contacts,
campaigns, billing records and the audit trail. The schema is preserved, so the
app boots straight into its empty states; pass ``--drop`` to rebuild the schema
from the models instead.

This is the counterpart to ``app.db.seed``: seed creates the optional demo
workspace, reset removes everything.

    python -m app.db.reset --dry-run      # show what would be removed
    python -m app.db.reset --yes          # remove it
    python -m app.db.reset --yes --drop   # rebuild the schema too
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine

# Owned by Alembic, not by the product. Wiping it would lose migration state.
PROTECTED_TABLES = frozenset({"alembic_version"})


def _deletable_tables(session: Session) -> List:
    """Tables to clear, children first, so foreign keys never block a delete."""
    present = set(inspect(session.get_bind()).get_table_names())
    return [
        table
        for table in reversed(Base.metadata.sorted_tables)
        if table.name in present and table.name not in PROTECTED_TABLES
    ]


def count_rows(session: Session) -> Dict[str, int]:
    """Row count for every table that a reset would clear."""
    return {
        table.name: session.execute(
            select(func.count()).select_from(table)
        ).scalar_one()
        for table in _deletable_tables(session)
    }


def clear_business_data(session: Session) -> Dict[str, int]:
    """Delete every row from every business table.

    Returns the counts that were present, so callers can report exactly what was
    removed rather than just asserting success.
    """
    counts = count_rows(session)
    for table in _deletable_tables(session):
        if counts[table.name]:
            session.execute(table.delete())
    session.commit()
    return counts


def _storage_root() -> Optional[Path]:
    """Local object-storage directory, when one is configured and present."""
    if settings.STORAGE_BACKEND != "local":
        return None
    root = Path(settings.STORAGE_LOCAL_PATH).resolve()
    if not root.is_dir():
        return None
    # A misconfigured path must never take the source tree with it.
    if (root / "app").is_dir() or (root / ".git").is_dir():
        raise RuntimeError(f"refusing to purge {root}: it looks like a repository root")
    return root


def purge_object_storage(root: Path) -> Tuple[int, int]:
    """Delete stored recordings and documents. Returns (file count, bytes)."""
    files = [path for path in root.rglob("*") if path.is_file()]
    size = sum(path.stat().st_size for path in files)
    for path in files:
        path.unlink()
    directories = [path for path in root.rglob("*") if path.is_dir()]
    for directory in sorted(directories, key=lambda p: len(p.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass  # non-empty for some other reason; harmless to leave
    return len(files), size


def reset_database(
    *, drop_schema: bool = False, purge_storage: bool = True
) -> Dict[str, object]:
    """Clear the database and, optionally, local object storage."""
    with SessionLocal() as session:
        before = count_rows(session)

    if drop_schema:
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        if not drop_schema:
            clear_business_data(session)
        remaining = count_rows(session)

    stored_files = 0
    stored_bytes = 0
    storage_root = _storage_root() if purge_storage else None
    if storage_root is not None:
        stored_files, stored_bytes = purge_object_storage(storage_root)

    return {
        "removed_tables": {name: n for name, n in before.items() if n},
        "removed_rows": sum(before.values()),
        "remaining_rows": sum(remaining.values()),
        "storage_path": str(storage_root) if storage_root else None,
        "storage_files": stored_files,
        "storage_bytes": stored_bytes,
    }


def _count_all() -> Dict[str, int]:
    with SessionLocal() as session:
        return count_rows(session)


def _print_table(title: str, counts: Dict[str, int]) -> None:
    print(title)
    if not any(counts.values()):
        print("  (empty)")
        return
    width = max(len(name) for name in counts)
    for name, count in sorted(counts.items()):
        if count:
            print(f"  {name:<{width}}  {count}")
    print(f"  {'TOTAL':<{width}}  {sum(counts.values())}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.db.reset",
        description="Remove all business data so testing starts from a clean slate.",
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="skip the confirmation prompt"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="report what would be removed, then exit"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="drop and recreate the schema instead of deleting rows",
    )
    parser.add_argument(
        "--keep-storage",
        action="store_true",
        help="keep uploaded documents and recordings on disk",
    )
    args = parser.parse_args(argv)

    print(f"Database: {settings.DATABASE_URL}")
    counts = _count_all()
    _print_table("Rows currently stored:", counts)

    if args.dry_run:
        print("\nDry run - nothing was changed.")
        return 0

    total = sum(counts.values())
    if total == 0 and not args.drop:
        print("\nAlready clean. Nothing to remove.")
        return 0

    if not args.yes:
        if not sys.stdin.isatty():
            print(
                "\nRefusing to wipe without confirmation. Re-run with --yes.",
                file=sys.stderr,
            )
            return 2
        answer = input("\nDelete all of this data? Type 'yes' to continue: ")
        if answer.strip().lower() != "yes":
            print("Aborted. Nothing was changed.")
            return 1

    result = reset_database(
        drop_schema=args.drop, purge_storage=not args.keep_storage
    )

    print("")
    if args.drop:
        print("Dropped and recreated the schema.")
    else:
        _print_table("Rows removed:", {k: v for k, v in counts.items()})
    if result["storage_path"]:
        print(
            f"Object storage cleared: {result['storage_files']} file(s), "
            f"{result['storage_bytes']} bytes from {result['storage_path']}"
        )
    if result["remaining_rows"]:
        print(f"WARNING: {result['remaining_rows']} row(s) still present.")
        return 1

    print("\nClean slate. Database and storage contain no business data.")
    print("Create an account at /signup, or run 'python -m app.db.seed' for demo data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
