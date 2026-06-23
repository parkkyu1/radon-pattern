from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, TypeVar

import pandas as pd
from sqlalchemy import Engine, create_engine, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

from . import APP_VERSION
from .assignments import deterministic_case_order
from .config import normalize_database_url
from .models import (
    AssignmentAuditLog,
    Base,
    ExpertReview,
    ReviewCase,
    Reviewer,
    ReviewerAssignment,
)

T = TypeVar("T")


class DatabaseUnavailable(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReviewDatabase:
    def __init__(self, database_url: str, engine: Engine | None = None) -> None:
        database_url = normalize_database_url(database_url)
        postgres_connect_args = {"connect_timeout": 8, "prepare_threshold": None}
        self.engine = engine or create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={} if database_url.startswith("sqlite") else postgres_connect_args,
        )

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)
        if self.engine.dialect.name == "postgresql":
            with self.engine.begin() as connection:
                for table in (
                    "review_cases",
                    "reviewers",
                    "reviewer_assignments",
                    "expert_reviews",
                    "assignment_audit_log",
                ):
                    connection.execute(
                        text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
                    )

    @contextmanager
    def session(self) -> Iterator[Session]:
        with Session(self.engine) as session:
            with session.begin():
                yield session

    def _retry(self, operation: Callable[[], T], retries: int = 3) -> T:
        for attempt in range(retries):
            try:
                return operation()
            except (OperationalError, DBAPIError) as error:
                if attempt == retries - 1:
                    raise DatabaseUnavailable(
                        "데이터베이스 연결이 일시적으로 불안정합니다. 잠시 후 다시 시도해 주세요."
                    ) from error
                time.sleep(0.4 * (attempt + 1))
        raise DatabaseUnavailable("Database operation failed.")

    def _insert(self, table: Any) -> Any:
        return sqlite_insert(table) if self.engine.dialect.name == "sqlite" else pg_insert(table)

    def seed_cases(self, cases: pd.DataFrame) -> int:
        records = cases[["review_case_id", "image_filename"]].to_dict("records")

        def operation() -> int:
            with self.session() as session:
                statement = self._insert(ReviewCase).values(records)
                statement = statement.on_conflict_do_update(
                    index_elements=[ReviewCase.review_case_id],
                    set_={"image_filename": statement.excluded.image_filename, "is_active": True},
                )
                result = session.execute(statement)
                return int(result.rowcount or 0)

        return self._retry(operation)

    def sync_reviewers(self, definitions: dict[str, tuple[str, str]]) -> None:
        records = [
            {"reviewer_id": reviewer_id, "reviewer_role": role, "is_active": True}
            for reviewer_id, (_, role) in definitions.items()
        ]

        def operation() -> None:
            with self.session() as session:
                statement = self._insert(Reviewer).values(records)
                statement = statement.on_conflict_do_update(
                    index_elements=[Reviewer.reviewer_id],
                    set_={"reviewer_role": statement.excluded.reviewer_role, "is_active": True},
                )
                session.execute(statement)

        self._retry(operation)

    def ensure_primary_assignments(
        self, reviewer_id: str, case_ids: list[str], order_seed: str
    ) -> list[str]:
        def operation() -> list[str]:
            with self.session() as session:
                existing = session.scalars(
                    select(ReviewerAssignment)
                    .where(ReviewerAssignment.reviewer_id == reviewer_id)
                    .order_by(ReviewerAssignment.display_order)
                ).all()
                existing_ids = [row.review_case_id for row in existing]
                missing = [case_id for case_id in case_ids if case_id not in set(existing_ids)]
                ordered_missing = deterministic_case_order(reviewer_id, missing, order_seed)
                next_order = max((row.display_order for row in existing), default=0) + 1
                for offset, case_id in enumerate(ordered_missing):
                    session.add(
                        ReviewerAssignment(
                            reviewer_id=reviewer_id,
                            review_case_id=case_id,
                            assignment_type="full",
                            display_order=next_order + offset,
                            assigned_by="system",
                        )
                    )
                    session.add(
                        AssignmentAuditLog(
                            reviewer_id=reviewer_id,
                            review_case_id=case_id,
                            action="ASSIGNED_FULL",
                            created_by="system",
                        )
                    )
                active_set = set(case_ids)
                for row in existing:
                    row.is_active = row.review_case_id in active_set
                return [
                    row.review_case_id
                    for row in sorted(existing, key=lambda item: item.display_order)
                    if row.review_case_id in active_set
                ] + ordered_missing

        return self._retry(operation)

    def assigned_case_ids(self, reviewer_id: str) -> list[str]:
        def operation() -> list[str]:
            with self.session() as session:
                return list(
                    session.scalars(
                        select(ReviewerAssignment.review_case_id)
                        .where(
                            ReviewerAssignment.reviewer_id == reviewer_id,
                            ReviewerAssignment.is_active.is_(True),
                        )
                        .order_by(ReviewerAssignment.display_order)
                    )
                )

        return self._retry(operation)

    def get_review(self, reviewer_id: str, case_id: str) -> dict[str, Any] | None:
        def operation() -> dict[str, Any] | None:
            with self.session() as session:
                row = session.get(ExpertReview, (reviewer_id, case_id))
                if row is None:
                    return None
                return {column.name: getattr(row, column.name) for column in row.__table__.columns}

        return self._retry(operation)

    def save_review(
        self,
        reviewer_id: str,
        case_id: str,
        expert_label: str,
        confidence: int,
        reasons: dict[str, bool],
        comment: str,
    ) -> None:
        if expert_label not in {"PASS", "WARN", "FAIL"} or confidence not in range(1, 6):
            raise ValueError("Invalid label or confidence.")

        def operation() -> None:
            with self.session() as session:
                assignment = session.get(ReviewerAssignment, (reviewer_id, case_id))
                if assignment is None or not assignment.is_active:
                    raise PermissionError("This case is not assigned to the reviewer.")
                now = utc_now()
                values = {
                    "reviewer_id": reviewer_id,
                    "review_case_id": case_id,
                    "expert_label": expert_label,
                    "confidence": confidence,
                    "comment": comment.strip(),
                    "submitted_at": now,
                    "updated_at": now,
                    "app_version": APP_VERSION,
                    **{key: bool(reasons.get(key, False)) for key in (
                        "reason_sealed_decline", "reason_spike",
                        "reason_transition_issue", "reason_vent_response",
                        "reason_data_quality", "reason_other",
                    )},
                }
                statement = self._insert(ExpertReview).values(values)
                update_values = dict(values)
                update_values.pop("submitted_at")
                statement = statement.on_conflict_do_update(
                    index_elements=[ExpertReview.reviewer_id, ExpertReview.review_case_id],
                    set_=update_values,
                )
                session.execute(statement)

        self._retry(operation)

    def progress(self, reviewer_id: str) -> tuple[int, int]:
        def operation() -> tuple[int, int]:
            with self.session() as session:
                assigned = session.scalar(
                    select(func.count()).select_from(ReviewerAssignment).where(
                        ReviewerAssignment.reviewer_id == reviewer_id,
                        ReviewerAssignment.is_active.is_(True),
                    )
                ) or 0
                completed = session.scalar(
                    select(func.count()).select_from(ExpertReview).join(
                        ReviewerAssignment,
                        (ReviewerAssignment.reviewer_id == ExpertReview.reviewer_id)
                        & (ReviewerAssignment.review_case_id == ExpertReview.review_case_id),
                    ).where(
                        ExpertReview.reviewer_id == reviewer_id,
                        ReviewerAssignment.is_active.is_(True),
                    )
                ) or 0
                return int(completed), int(assigned)

        return self._retry(operation)

    def export_reviews(self) -> pd.DataFrame:
        return self._retry(
            lambda: pd.read_sql(
                select(ExpertReview).order_by(
                    ExpertReview.reviewer_id, ExpertReview.review_case_id
                ),
                self.engine,
            )
        )

    def assignment_status(self) -> pd.DataFrame:
        query = (
            select(
                ReviewerAssignment.reviewer_id,
                ReviewerAssignment.assignment_type,
                func.count().label("assigned_cases"),
                func.count(ExpertReview.review_case_id).label("completed_cases"),
            )
            .outerjoin(
                ExpertReview,
                (ExpertReview.reviewer_id == ReviewerAssignment.reviewer_id)
                & (ExpertReview.review_case_id == ReviewerAssignment.review_case_id),
            )
            .where(ReviewerAssignment.is_active.is_(True))
            .group_by(ReviewerAssignment.reviewer_id, ReviewerAssignment.assignment_type)
        )
        frame = self._retry(lambda: pd.read_sql(query, self.engine))
        if not frame.empty:
            frame["incomplete_cases"] = frame["assigned_cases"] - frame["completed_cases"]
            frame["completion_percent"] = (
                frame["completed_cases"] / frame["assigned_cases"] * 100
            ).round(2)
        return frame

    def compare_reviewers(self, reviewer_a: str, reviewer_b: str) -> pd.DataFrame:
        reviews = self.export_reviews()
        left = reviews.loc[reviews["reviewer_id"].eq(reviewer_a), [
            "review_case_id", "expert_label"
        ]].rename(columns={"expert_label": "reviewer_a_label"})
        right = reviews.loc[reviews["reviewer_id"].eq(reviewer_b), [
            "review_case_id", "expert_label"
        ]].rename(columns={"expert_label": "reviewer_b_label"})
        compared = left.merge(right, on="review_case_id", how="inner")
        compared["is_agreement"] = compared["reviewer_a_label"].eq(
            compared["reviewer_b_label"]
        )
        return compared

    def assign_adjudication(
        self,
        reviewer_a: str,
        reviewer_b: str,
        adjudicator: str,
        created_by: str,
        order_seed: str,
    ) -> tuple[pd.DataFrame, int, int]:
        disagreements = self.compare_reviewers(reviewer_a, reviewer_b)
        disagreements = disagreements.loc[~disagreements["is_agreement"]].copy()
        case_ids = disagreements["review_case_id"].astype(str).tolist()

        def operation() -> tuple[int, int]:
            with self.session() as session:
                existing = {
                    row.review_case_id: row
                    for row in session.scalars(
                        select(ReviewerAssignment).where(
                            ReviewerAssignment.reviewer_id == adjudicator
                        )
                    )
                }
                current_max = max((row.display_order for row in existing.values()), default=0)
                new_ids = deterministic_case_order(
                    adjudicator,
                    [case for case in case_ids if case not in existing],
                    order_seed,
                )
                for offset, case_id in enumerate(new_ids):
                    session.add(
                        ReviewerAssignment(
                            reviewer_id=adjudicator,
                            review_case_id=case_id,
                            assignment_type="adjudication",
                            display_order=current_max + offset + 1,
                            assigned_by=created_by,
                        )
                    )
                    session.add(
                        AssignmentAuditLog(
                            reviewer_id=adjudicator,
                            review_case_id=case_id,
                            action="ASSIGNED_ADJUDICATION",
                            created_by=created_by,
                        )
                    )
                active = set(case_ids)
                for case_id, row in existing.items():
                    if row.assignment_type == "adjudication":
                        desired = case_id in active
                        if row.is_active != desired:
                            row.is_active = desired
                            session.add(
                                AssignmentAuditLog(
                                    reviewer_id=adjudicator,
                                    review_case_id=case_id,
                                    action=(
                                        "REACTIVATED_ADJUDICATION"
                                        if desired
                                        else "DEACTIVATED_ADJUDICATION"
                                    ),
                                    created_by=created_by,
                                )
                            )
                existing_relevant = sum(case_id in existing for case_id in case_ids)
                return existing_relevant, len(new_ids)

        existing_count, new_count = self._retry(operation)
        return disagreements, existing_count, new_count
