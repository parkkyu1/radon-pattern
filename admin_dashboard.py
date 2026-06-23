from __future__ import annotations

from pathlib import Path

import streamlit as st

from review_app.auth import (
    get_reviewer_role,
    issue_session_token,
    validate_access,
    validate_session_token,
)
from review_app.config import load_config, reviewer_definitions
from review_app.consensus import build_consensus, reliability_outputs
from review_app.db_postgres import ReviewDatabase
from review_app.package_loader import load_public_cases

ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "review_package" / "public"


@st.cache_resource
def database(database_url: str) -> ReviewDatabase:
    return ReviewDatabase(database_url)


def main() -> None:
    st.set_page_config(page_title="Radon Review Admin", layout="wide")
    if "admin_id" not in st.session_state:
        st.title("라돈 전문가 판정 관리자")
        with st.form("admin_login"):
            admin_id = st.text_input("관리자 ID", value="admin")
            code = st.text_input("관리자 접근코드", type="password")
            submitted = st.form_submit_button("로그인")
        if submitted and validate_access(admin_id, code, st.secrets):
            if get_reviewer_role(admin_id, st.secrets) != "admin":
                st.error("관리자 권한이 없습니다.")
                return
            st.session_state["admin_id"] = admin_id
            config = load_config(st.secrets)
            st.session_state["admin_token"] = issue_session_token(
                admin_id, "admin", config.session_secret
            )
            st.rerun()
        elif submitted:
            st.error("관리자 인증에 실패했습니다.")
        return

    config = load_config(st.secrets)
    if not validate_session_token(
        str(st.session_state["admin_id"]),
        "admin",
        str(st.session_state.get("admin_token", "")),
        config.session_secret,
    ):
        st.session_state.clear()
        st.error("관리자 세션이 유효하지 않습니다. 다시 로그인해 주세요.")
        return
    db = database(config.database_url)
    cases = load_public_cases(PUBLIC_DIR)
    db.create_schema()
    db.seed_cases(cases)
    definitions = reviewer_definitions(st.secrets)
    db.sync_reviewers(definitions)
    public_ids = cases["review_case_id"].tolist()
    for reviewer_id, (_, role) in definitions.items():
        if role == "primary":
            db.ensure_primary_assignments(reviewer_id, public_ids, config.order_seed)
    st.title("전문가 판정 운영 현황")
    st.warning("관리자 화면에도 원래 식별정보와 알고리즘 결과는 포함되지 않습니다.")
    st.dataframe(db.assignment_status(), use_container_width=True, hide_index=True)

    reviewer_a = st.text_input("Primary A", "reviewer_a")
    reviewer_b = st.text_input("Primary B", "reviewer_b")
    adjudicator = st.text_input("Adjudicator", "reviewer_c")
    compared = db.compare_reviewers(reviewer_a, reviewer_b)
    st.metric("A/B 공통 완료", len(compared))
    st.metric("A/B 불일치", int((~compared["is_agreement"]).sum()) if len(compared) else 0)
    if st.button("불일치 사례 배정/갱신"):
        frame, existing, new = db.assign_adjudication(
            reviewer_a,
            reviewer_b,
            adjudicator,
            str(st.session_state["admin_id"]),
            config.order_seed,
        )
        st.success(f"불일치 {len(frame)}건, 기존 배정 {existing}건, 신규 {new}건")

    reviews = db.export_reviews()
    if not reviews.empty:
        consensus = build_consensus(reviews)
        st.download_button(
            "판정 결과 CSV",
            reviews.to_csv(index=False).encode("utf-8-sig"),
            "expert_reviews.csv",
        )
        st.download_button(
            "Consensus CSV",
            consensus.to_csv(index=False).encode("utf-8-sig"),
            "expert_consensus.csv",
        )
        for name, frame in reliability_outputs(reviews).items():
            st.download_button(
                f"{name} CSV", frame.to_csv(index=False).encode("utf-8-sig"), f"{name}.csv"
            )


if __name__ == "__main__":
    main()
