from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from review_app.db_postgres import ReviewDatabase


def main() -> None:
    parser = argparse.ArgumentParser(description="Assign A/B disagreements to reviewer C.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--reviewer-a", default="reviewer_a")
    parser.add_argument("--reviewer-b", default="reviewer_b")
    parser.add_argument("--adjudicator", default="reviewer_c")
    parser.add_argument("--created-by", default="admin")
    parser.add_argument("--order-seed", default=os.getenv("ORDER_SEED"))
    parser.add_argument("--output-dir", type=Path, default=Path("exports/adjudication"))
    args = parser.parse_args()
    if not args.database_url or not args.order_seed:
        raise SystemExit("DATABASE_URL and ORDER_SEED are required.")
    db = ReviewDatabase(args.database_url)
    disagreements, existing, new = db.assign_adjudication(
        args.reviewer_a,
        args.reviewer_b,
        args.adjudicator,
        args.created_by,
        args.order_seed,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "adjudication_assignments.csv"
    disagreements.to_csv(output, index=False)
    print(
        f"disagreements={len(disagreements)} existing_assignments={existing} "
        f"new_assignments={new} output={output}"
    )


if __name__ == "__main__":
    main()

