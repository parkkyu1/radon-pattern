import pandas as pd

from review_app.consensus import build_consensus, reliability_outputs


def test_consensus_rules() -> None:
    reviews = pd.DataFrame(
        [
            ["R001", "a", "PASS", 4],
            ["R001", "b", "PASS", 4],
            ["R002", "a", "WARN", 4],
            ["R002", "b", "FAIL", 4],
            ["R003", "a", "FAIL", 4],
            ["R003", "b", "WARN", 4],
            ["R003", "c", "FAIL", 5],
            ["R004", "a", "PASS", 4],
            ["R004", "b", "WARN", 4],
            ["R004", "c", "FAIL", 5],
        ],
        columns=["review_case_id", "reviewer_id", "expert_label", "confidence"],
    )
    result = build_consensus(reviews).set_index("review_case_id")
    assert result.loc["R001", "consensus_method"] == "TWO_REVIEWER_AGREEMENT"
    assert result.loc["R002", "consensus_label"] == "DISAGREEMENT"
    assert result.loc["R003", "consensus_method"] == "MAJORITY_CONSENSUS"
    assert result.loc["R004", "consensus_label"] == "DISAGREEMENT"
    outputs = reliability_outputs(reviews)
    assert {
        "pairwise_cohen_kappa",
        "agreement_summary",
        "reviewer_summary",
        "fleiss_kappa",
    } == set(outputs)

