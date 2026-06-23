# GitHub 업로드 점검표

## 업로드 전

- [ ] GitHub repository가 **Private**이다.
- [ ] `python scripts/verify_deployment_bundle.py`가 통과한다.
- [ ] `.streamlit/secrets.toml`이 없다.
- [ ] `.env` 실제 파일이 없다.
- [ ] `review_package/private/`가 없다.
- [ ] `expert_review_key_private.csv`가 없다.
- [ ] 원자료 CSV와 `qc_assessment_all.csv`가 없다.
- [ ] SQLite 파일이 없다.
- [ ] export, log, offline 병합 결과가 없다.
- [ ] public CSV 컬럼은 `review_case_id,image_filename`뿐이다.
- [ ] public images에는 사례코드 외 식별정보가 없다.
- [ ] ZIP 파일 자체를 repository에 넣지 않는다.

## 업로드 후

- [ ] GitHub 웹 화면에서 repository visibility가 Private인지 재확인한다.
- [ ] GitHub 검색으로 `DATABASE_URL`, `password`, `pattern_id`,
  `algorithm_label`을 점검한다.
- [ ] Streamlit Secrets는 Community Cloud settings에만 입력했다.
- [ ] GitHub commit history에도 secret이 없음을 확인한다.
- [ ] secret을 실수로 commit했다면 삭제만 하지 말고 즉시 DB password와
  reviewer 접근코드를 회전한다.

