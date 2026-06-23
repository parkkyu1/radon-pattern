from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class ReviewCase(Base):
    __tablename__ = "review_cases"
    review_case_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    image_filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class Reviewer(Base):
    __tablename__ = "reviewers"
    reviewer_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    reviewer_role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    __table_args__ = (
        CheckConstraint(
            "reviewer_role IN ('primary','adjudicator','admin')",
            name="ck_reviewer_role",
        ),
    )


class ReviewerAssignment(Base):
    __tablename__ = "reviewer_assignments"
    reviewer_id: Mapped[str] = mapped_column(
        ForeignKey("reviewers.reviewer_id"), primary_key=True
    )
    review_case_id: Mapped[str] = mapped_column(
        ForeignKey("review_cases.review_case_id"), primary_key=True
    )
    assignment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    assigned_by: Mapped[str] = mapped_column(String(100), nullable=False)
    __table_args__ = (
        CheckConstraint(
            "assignment_type IN ('full','adjudication','calibration')",
            name="ck_assignment_type",
        ),
        UniqueConstraint("reviewer_id", "display_order", name="uq_reviewer_display_order"),
    )


class ExpertReview(Base):
    __tablename__ = "expert_reviews"
    reviewer_id: Mapped[str] = mapped_column(
        ForeignKey("reviewers.reviewer_id"), primary_key=True
    )
    review_case_id: Mapped[str] = mapped_column(
        ForeignKey("review_cases.review_case_id"), primary_key=True
    )
    expert_label: Mapped[str] = mapped_column(String(10), nullable=False)
    reason_sealed_decline: Mapped[bool] = mapped_column(Boolean, default=False)
    reason_spike: Mapped[bool] = mapped_column(Boolean, default=False)
    reason_transition_issue: Mapped[bool] = mapped_column(Boolean, default=False)
    reason_vent_response: Mapped[bool] = mapped_column(Boolean, default=False)
    reason_data_quality: Mapped[bool] = mapped_column(Boolean, default=False)
    reason_other: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    app_version: Mapped[str] = mapped_column(String(30), nullable=False)
    __table_args__ = (
        CheckConstraint(
            "expert_label IN ('PASS','WARN','FAIL')", name="ck_expert_label"
        ),
        CheckConstraint("confidence BETWEEN 1 AND 5", name="ck_confidence"),
    )


class AssignmentAuditLog(Base):
    __tablename__ = "assignment_audit_log"
    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reviewer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    review_case_id: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

