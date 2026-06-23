from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from review_app.db_postgres import ReviewDatabase
from review_app.models import ExpertReview, Reviewer, ReviewerAssignment
from review_app.package_loader import load_public_cases


def read_table(connection: sqlite3.Connection, table: str) -> pd.DataFrame:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return pd.read_sql_query(f"SELECT * FROM {table}", connection) if exists else pd.DataFrame()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate blinded SQLite pilot data.")
    parser.add_argument("--sqlite-path", type=Path, required=True)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required.")
    if not args.sqlite_path.exists():
        raise SystemExit(f"SQLite file not found: {args.sqlite_path}")

    with sqlite3.connect(args.sqlite_path) as source:
        reviews = read_table(source, "expert_reviews")
        assignments = read_table(source, "reviewer_assignments")
        if assignments.empty:
            assignments = read_table(source, "reviewer_case_order")

    if not reviews.empty and "updated_at" in reviews:
        reviews = reviews.sort_values("updated_at").drop_duplicates(
            ["reviewer_id", "review_case_id"], keep="last"
        )
    summary = pd.DataFrame(
        [
            {"table": "reviewer_assignments", "source_rows": len(assignments)},
            {"table": "expert_reviews", "source_rows": len(reviews)},
        ]
    )
    print(summary.to_string(index=False))
    if not args.apply:
        print("DRY RUN only. Add --apply to write to PostgreSQL.")
        return

    db = ReviewDatabase(args.database_url)
    db.create_schema()
    db.seed_cases(load_public_cases(ROOT / "review_package" / "public"))
    reviewer_ids = sorted(
        set(assignments.get("reviewer_id", pd.Series(dtype=str)).astype(str))
        | set(reviews.get("reviewer_id", pd.Series(dtype=str)).astype(str))
    )
    with Session(db.engine) as session, session.begin():
        for reviewer_id in reviewer_ids:
            if not session.get(Reviewer, reviewer_id):
                session.add(
                    Reviewer(
                        reviewer_id=reviewer_id,
                        reviewer_role="adjudicator"
                        if reviewer_id.endswith("_c")
                        else "primary",
                    )
                )
        next_orders: dict[str, int] = {}
        for row in assignments.to_dict("records"):
            case_id = str(row["review_case_id"])
            reviewer_id = str(row["reviewer_id"])
            current = session.get(ReviewerAssignment, (reviewer_id, case_id))
            if current is None:
                fallback_order = next_orders.get(reviewer_id, 0) + 1
                next_orders[reviewer_id] = fallback_order
                display_order = row.get("display_order")
                if display_order is None or pd.isna(display_order):
                    display_order = fallback_order
                session.add(
                    ReviewerAssignment(
                        reviewer_id=reviewer_id,
                        review_case_id=case_id,
                        assignment_type=str(row.get("assignment_type", "full")),
                        display_order=int(display_order),
                        assigned_by=str(row.get("assigned_by", "sqlite_migration")),
                        is_active=bool(row.get("is_active", 1)),
                    )
                )
        for row in reviews.to_dict("records"):
            values = {
                column.name: row.get(column.name)
                for column in ExpertReview.__table__.columns
                if column.name in row and not pd.isna(row.get(column.name))
            }
            values["reviewer_id"] = str(row["reviewer_id"])
            values["review_case_id"] = str(row["review_case_id"])
            for field in ("submitted_at", "updated_at"):
                if field in values:
                    values[field] = pd.to_datetime(values[field], utc=True).to_pydatetime()
            for field in (
                "reason_sealed_decline",
                "reason_spike",
                "reason_transition_issue",
                "reason_vent_response",
                "reason_data_quality",
                "reason_other",
            ):
                if field in values:
                    values[field] = bool(values[field])
            session.merge(ExpertReview(**values))
    print(f"APPLIED assignments={len(assignments)} reviews={len(reviews)}")


if __name__ == "__main__":
    main()
