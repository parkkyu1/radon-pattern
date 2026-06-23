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
from review_app.db_postgres import DatabaseUnavailable, ReviewDatabase
from review_app.package_loader import load_public_cases

ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "review_package" / "public"
REASONS = {
    "reason_sealed_decline": "밀폐구간 비정상 감소",
    "reason_spike": "밀폐 중 급격한 변동 또는 스파이크",
    "reason_transition_issue": "환기 전환이 불명확하거나 반복됨",
    "reason_vent_response": "환기 후 농도 감소가 불충분함",
    "reason_data_quality": "기록 품질 또는 장비 이상 의심",
    "reason_other": "기타",
}


@st.cache_resource
def database(database_url: str) -> ReviewDatabase:
    return ReviewDatabase(database_url)


def initialize(db: ReviewDatabase):
    cases = load_public_cases(PUBLIC_DIR)
    db.create_schema()
    db.seed_cases(cases)
    db.sync_reviewers(reviewer_definitions(st.secrets))
    return cases


def login() -> None:
    st.title("라돈 72시간 전문가 블라인드 판정")
    with st.form("login"):
        reviewer_id = st.text_input("Reviewer ID")
        code = st.text_input("개별 접근코드", type="password")
        submitted = st.form_submit_button("로그인")
    if submitted and validate_access(reviewer_id.strip(), code, st.secrets):
        role = get_reviewer_role(reviewer_id.strip(), st.secrets)
        if role == "admin":
            st.error("관리자는 별도 admin_dashboard.py를 사용하십시오.")
            return
        st.session_state["reviewer_id"] = reviewer_id.strip()
        st.session_state["role"] = role
        config = load_config(st.secrets)
        st.session_state["session_token"] = issue_session_token(
            reviewer_id.strip(), role, config.session_secret
        )
        st.rerun()
    elif submitted:
        st.error("Reviewer ID 또는 접근코드가 올바르지 않습니다.")


def main() -> None:
    st.set_page_config(page_title="Radon Expert Review", layout="centered")
    if "reviewer_id" not in st.session_state:
        login()
        return
    try:
        config = load_config(st.secrets)
        if not validate_session_token(
            str(st.session_state["reviewer_id"]),
            str(st.session_state["role"]),
            str(st.session_state.get("session_token", "")),
            config.session_secret,
        ):
            st.session_state.clear()
            st.error("로그인 세션이 유효하지 않습니다. 다시 로그인해 주세요.")
            return
        db = database(config.database_url)
        cases = initialize(db)
        reviewer_id = str(st.session_state["reviewer_id"])
        role = str(st.session_state["role"])
        public_ids = cases["review_case_id"].tolist()
        if role == "primary":
            ordered_ids = db.ensure_primary_assignments(
                reviewer_id, public_ids, config.order_seed
            )
        else:
            ordered_ids = db.assigned_case_ids(reviewer_id)
    except DatabaseUnavailable as error:
        st.error(str(error))
        return
    except Exception as error:
        st.error(f"앱 초기화에 실패했습니다: {error}")
        return

    if not ordered_ids:
        st.info("현재 배정된 사례가 없습니다.")
        return
    if "case_index" not in st.session_state:
        reviewed = {
            case_id for case_id in ordered_ids if db.get_review(reviewer_id, case_id)
        }
        st.session_state["case_index"] = next(
            (index for index, case in enumerate(ordered_ids) if case not in reviewed), 0
        )
    index = min(max(int(st.session_state["case_index"]), 0), len(ordered_ids) - 1)
    case_id = ordered_ids[index]
    image_name = cases.set_index("review_case_id").loc[case_id, "image_filename"]
    saved = db.get_review(reviewer_id, case_id) or {}
    completed, total = db.progress(reviewer_id)

    st.caption(f"Reviewer: {reviewer_id}")
    st.header(f"Case {case_id}")
    st.write(f"현재 사례: {index + 1} / {total} · 완료: {completed} / {total}")
    st.progress(completed / total if total else 0)
    st.image(PUBLIC_DIR / "images" / image_name, use_container_width=True)

    options = ["선택", "PASS", "WARN", "FAIL"]
    selected = str(saved.get("expert_label", "선택"))
    label = st.radio(
        "최종 판정 (필수)",
        options,
        index=options.index(selected) if selected in options else 0,
        horizontal=True,
    )
    reasons = {
        field: st.checkbox(
            text, value=bool(saved.get(field, False)), key=f"{case_id}_{field}"
        )
        for field, text in REASONS.items()
    }
    confidence = st.select_slider(
        "확신도 (필수)",
        options=[0, 1, 2, 3, 4, 5],
        value=int(saved.get("confidence", 0)),
        format_func=lambda value: "선택" if value == 0 else f"{value}점",
    )
    comment = st.text_area("자유 의견", value=str(saved.get("comment", "")))
    save_col, previous_col, pending_col = st.columns(3)
    with save_col:
        if st.button("저장 후 다음", type="primary", use_container_width=True):
            if label == "선택" or confidence == 0:
                st.error("판정과 확신도를 입력하십시오.")
            else:
                db.save_review(
                    reviewer_id, case_id, label, confidence, reasons, comment
                )
                st.session_state["case_index"] = min(index + 1, total - 1)
                st.rerun()
    with previous_col:
        if st.button("이전 사례", use_container_width=True):
            st.session_state["case_index"] = max(index - 1, 0)
            st.rerun()
    with pending_col:
        if st.button("미판정 이동", use_container_width=True):
            target = next(
                (
                    idx
                    for idx, item in enumerate(ordered_ids)
                    if db.get_review(reviewer_id, item) is None
                ),
                None,
            )
            if target is None:
                st.success("모든 배정 사례를 완료했습니다.")
            else:
                st.session_state["case_index"] = target
                st.rerun()
    if st.button("로그아웃"):
        st.session_state.clear()
        st.rerun()


if __name__ == "__main__":
    main()
