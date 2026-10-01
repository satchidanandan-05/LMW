"""Rebuild the traceability database from the Excel dataset (replaces the demo sample data).

Usage:  python scripts/import_dataset.py [--source PATH]

PATH may be the .xlsx file or the .zip package that contains it.
Default: data/Yarn_Traceability_Dataset_Package.zip
"""
import argparse
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import config  # noqa: E402
from database.database import get_engine, init_database, sqlite_path  # noqa: E402
from services.import_service import import_dataset  # noqa: E402

DEFAULT_SOURCE = config.BASE_DIR / "data" / "Yarn_Traceability_Dataset_Package.zip"
REPORT_PATH = config.BASE_DIR / "data" / "import_report.txt"


def read_sheets(source: Path) -> dict[str, pd.DataFrame]:
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as package:
            name = next(n for n in package.namelist() if n.lower().endswith(".xlsx"))
            with package.open(name) as xlsx:
                return pd.read_excel(xlsx, sheet_name=None, dtype=str)
    return pd.read_excel(source, sheet_name=None, dtype=str)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help=".xlsx file or .zip package")
    args = parser.parse_args(argv)
    if not args.source.exists():
        print(f"Dataset not found: {args.source}")
        return 1

    sheets = read_sheets(args.source)
    path = sqlite_path(config.DATABASE_URL)
    if path is not None and path.exists():
        path.unlink()  # fresh database; close any viewer that has the file open
    engine = get_engine()
    init_database(engine, sample_data=False)
    report = import_dataset(engine, sheets)

    REPORT_PATH.write_text(report.as_text(), encoding="utf-8")
    print(report.as_text())
    print(f"\nDatabase ready: {config.DATABASE_URL}\nReport saved: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
