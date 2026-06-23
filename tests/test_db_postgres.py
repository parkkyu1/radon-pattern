from __future__ import annotations

import pandas as pd

from review_app.db_postgres import ReviewDatabase


def test_primary_assignment_is_complete_and_fixed(
    db: ReviewDatabase, cases: pd.DataFrame
) -> None:
    case_ids = cases["review_case_id"].tolist()
    first = db.ensure_primary_assignments("reviewer_a", case_ids, "seed")
    second = db.ensure_primary_assignments("reviewer_a", case_ids, "different-seed")
    assert set(first) == set(case_ids)
    assert first == second


def test_reviewer_reviews_do_not_overwrite_each_other(
    db: ReviewDatabase, cases: pd.DataFrame
) -> None:
    case_ids = cases["review_case_id"].tolist()
    for reviewer in ("reviewer_a", "reviewer_b"):
        db.ensure_primary_assignments(reviewer, case_ids, "seed")
    db.save_review("reviewer_a", "R001", "PASS", 4, {}, "A")
    db.save_review("reviewer_b", "R001", "FAIL", 5, {}, "B")
    db.save_review("reviewer_a", "R001", "WARN", 3, {}, "A updated")
    assert db.get_review("reviewer_a", "R001")["expert_label"] == "WARN"
    assert db.get_review("reviewer_b", "R001")["expert_label"] == "FAIL"


def test_adjudicator_sees_only_disagreements(
    db: ReviewDatabase, cases: pd.DataFrame
) -> None:
    case_ids = cases["review_case_id"].tolist()
    for reviewer in ("reviewer_a", "reviewer_b"):
        db.ensure_primary_assignments(reviewer, case_ids, "seed")
    labels_a = ["PASS", "WARN", "FAIL", "PASS", "WARN", "FAIL"]
    labels_b = ["PASS", "FAIL", "WARN", "PASS", "WARN", "FAIL"]
    for case_id, label_a, label_b in zip(case_ids, labels_a, labels_b):
        db.save_review("reviewer_a", case_id, label_a, 4, {}, "")
        db.save_review("reviewer_b", case_id, label_b, 4, {}, "")
    disagreements, _, new = db.assign_adjudication(
        "reviewer_a", "reviewer_b", "reviewer_c", "admin", "seed"
    )
    assert set(disagreements["review_case_id"]) == {"R002", "R003"}
    assert set(db.assigned_case_ids("reviewer_c")) == {"R002", "R003"}
    assert new == 2

