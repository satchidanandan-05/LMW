"""Create the traceability database with schema, indexes, demo users and sample data.

Usage:  python scripts/init_db.py [--reset]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from database.database import get_engine, init_database, is_initialized, sqlite_path  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="delete the existing SQLite database first")
    args = parser.parse_args(argv)

    path = sqlite_path(config.DATABASE_URL)
    if args.reset and path is not None and path.exists():
        path.unlink()

    engine = get_engine()
    if is_initialized(engine):
        print("Database already initialized. Use --reset to recreate it.")
        return 1
    init_database(engine)
    print(f"Database ready: {config.DATABASE_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
