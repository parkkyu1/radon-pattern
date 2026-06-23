from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from review_app.consensus import build_consensus, reliability_outputs
from review_app.db_postgres import ReviewDatabase


def main() -> None:
    parser = argparse.ArgumentParser(description="Export blinded expert review results.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--output-dir", type=Path, default=Path("exports"))
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required.")
    db = ReviewDatabase(args.database_url)
    reviews = db.export_reviews()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reviews.to_csv(args.output_dir / "expert_reviews.csv", index=False)
    db.assignment_status().to_csv(
        args.output_dir / "reviewer_progress.csv", index=False
    )
    if not reviews.empty:
        build_consensus(reviews).to_csv(
            args.output_dir / "expert_consensus.csv", index=False
        )
        for name, frame in reliability_outputs(reviews).items():
            frame.to_csv(args.output_dir / f"{name}.csv", index=False)
    print(f"Exported {len(reviews)} blinded review rows to {args.output_dir}")


if __name__ == "__main__":
    main()

