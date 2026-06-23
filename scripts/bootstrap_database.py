from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from review_app.db_postgres import ReviewDatabase
from review_app.package_loader import load_public_cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Create schema and seed public cases.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL or --database-url is required.")
    cases = load_public_cases(ROOT / "review_package" / "public")
    db = ReviewDatabase(args.database_url)
    db.create_schema()
    affected = db.seed_cases(cases)
    print(f"Schema ready; public cases={len(cases)}; affected rows={affected}")


if __name__ == "__main__":
    main()

