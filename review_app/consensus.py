from __future__ import annotations

import json
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

LABELS = ("PASS", "WARN", "FAIL")


def build_consensus(reviews: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for case_id, group in reviews.groupby("review_case_id"):
        labels_by_reviewer = dict(
            zip(group["reviewer_id"].astype(str), group["expert_label"].astype(str))
        )
        counts = pd.Series(list(labels_by_reviewer.values())).value_counts()
        n_reviews = len(labels_by_reviewer)
        label, method = "INSUFFICIENT_REVIEWS", "INSUFFICIENT_REVIEWS"
        if n_reviews == 2:
            if len(counts) == 1:
                label, method = str(counts.index[0]), "TWO_REVIEWER_AGREEMENT"
            else:
                label, method = "DISAGREEMENT", "DISAGREEMENT"
        elif n_reviews >= 3:
            leaders = counts[counts.eq(counts.max())]
            if len(leaders) == 1 and int(leaders.iloc[0]) >= 2:
                label, method = str(leaders.index[0]), "MAJORITY_CONSENSUS"
            else:
                label, method = "DISAGREEMENT", "DISAGREEMENT"
        rows.append(
            {
                "review_case_id": case_id,
                "n_reviews": n_reviews,
                "reviewer_labels": json.dumps(labels_by_reviewer, sort_keys=True),
                "consensus_label": label,
                "consensus_method": method,
                "is_disagreement": label == "DISAGREEMENT",
                "n_pass": int(counts.get("PASS", 0)),
                "n_warn": int(counts.get("WARN", 0)),
                "n_fail": int(counts.get("FAIL", 0)),
            }
        )
    return pd.DataFrame(rows)


def reliability_outputs(reviews: pd.DataFrame) -> dict[str, pd.DataFrame]:
    pairwise: list[dict[str, Any]] = []
    reviewers = sorted(reviews["reviewer_id"].astype(str).unique())
    for left_id, right_id in combinations(reviewers, 2):
        left = reviews[reviews["reviewer_id"].eq(left_id)][
            ["review_case_id", "expert_label"]
        ]
        right = reviews[reviews["reviewer_id"].eq(right_id)][
            ["review_case_id", "expert_label"]
        ]
        paired = left.merge(right, on="review_case_id", suffixes=("_a", "_b"))
        value = np.nan
        note = ""
        if len(paired) >= 2:
            value = cohen_kappa_score(paired["expert_label_a"], paired["expert_label_b"])
            if np.isnan(value):
                note = "undefined_label_distribution"
        else:
            note = "fewer_than_two_common_cases"
        pairwise.append(
            {
                "reviewer_a": left_id,
                "reviewer_b": right_id,
                "n_common_cases": len(paired),
                "cohen_kappa": value,
                "calculation_note": note,
            }
        )

    grouped = reviews.groupby("review_case_id")["expert_label"].agg(list)
    eligible = grouped[grouped.map(len).ge(2)]
    agreement = pd.DataFrame(
        [
            {
                "metric": "overall_complete_agreement",
                "numerator": int(
                    eligible.map(lambda values: len(set(values)) == 1).sum()
                ),
                "denominator": len(eligible),
            }
        ]
    )
    agreement["rate"] = np.where(
        agreement["denominator"].gt(0),
        agreement["numerator"] / agreement["denominator"],
        np.nan,
    )

    distribution = (
        reviews.groupby(["reviewer_id", "expert_label"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=LABELS, fill_value=0)
        .reset_index()
    )
    distribution.columns = ["reviewer_id", "n_pass", "n_warn", "n_fail"]
    confidence = reviews.groupby("reviewer_id", as_index=False)["confidence"].mean()
    confidence = confidence.rename(columns={"confidence": "mean_confidence"})
    reviewer_summary = distribution.merge(confidence, on="reviewer_id", how="left")

    matrix = (
        reviews.groupby(["review_case_id", "expert_label"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=LABELS, fill_value=0)
    )
    matrix = matrix[matrix.sum(axis=1).ge(3)]
    fleiss_value, note = np.nan, ""
    if matrix.empty:
        note = "no_cases_with_at_least_three_reviews"
    elif len(matrix.sum(axis=1).unique()) != 1:
        note = "variable_number_of_raters_per_case"
    else:
        n = int(matrix.sum(axis=1).iloc[0])
        values = matrix.to_numpy(float)
        observed = (((values**2).sum(axis=1) - n) / (n * (n - 1))).mean()
        proportions = values.sum(axis=0) / (len(values) * n)
        expected = float((proportions**2).sum())
        if np.isclose(1 - expected, 0):
            note = "expected_agreement_equals_one"
        else:
            fleiss_value = float((observed - expected) / (1 - expected))
    fleiss = pd.DataFrame(
        [{"fleiss_kappa": fleiss_value, "n_cases": len(matrix), "calculation_note": note}]
    )
    return {
        "pairwise_cohen_kappa": pd.DataFrame(pairwise),
        "agreement_summary": agreement,
        "reviewer_summary": reviewer_summary,
        "fleiss_kappa": fleiss,
    }

