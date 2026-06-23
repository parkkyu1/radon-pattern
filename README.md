# Radon Expert Review App — Streamlit Cloud + Supabase

신축 공동주택 72시간 라돈 시계열을 `PASS / WARN / FAIL`로 블라인드 판정하는
온라인 앱이다. 판정 결과는 Supabase PostgreSQL에 저장된다.

## 보안 경계

GitHub와 Streamlit Cloud에는 무작위 `review_case_id`, public PNG, 앱 코드만
배포한다. `pattern_id`, 장비번호, 층수, 측정일시, 알고리즘 결과, QC/AE/ACH,
원자료, private mapping은 이 프로젝트에 넣지 않는다.

## 구조

```text
app.py                     전문가 전용 앱
admin_dashboard.py         관리자 전용 별도 앱
review_app/                인증·DB·배정·합의 로직
scripts/                   초기화·이전·배정·export·보안 검사
sql/001_initial_schema.sql Supabase SQL Editor용 idempotent schema
review_package/public/     배포 가능한 사례 CSV와 PNG
docs/                      설정 및 운영 문서
```

## 로컬 설치와 검사

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
python scripts\verify_deployment_bundle.py
```

실제 PostgreSQL 통합 테스트:

```powershell
$env:TEST_DATABASE_URL="postgresql+psycopg://...?...sslmode=require"
pytest -q tests\test_postgres_integration.py
```

## 배포 순서

1. `docs/SUPABASE_SETUP.md`
2. `docs/GITHUB_UPLOAD_CHECKLIST.md`
3. `docs/STREAMLIT_CLOUD_DEPLOY.md`
4. `docs/OPERATION_MANUAL.md`

전문가에게는 `app.py` 배포 URL, reviewer ID, 개별 접근코드만 전달한다.
관리자 앱은 `admin_dashboard.py`를 같은 private repository에서 별도 앱으로
배포하여 URL을 공개하지 않는다.

## 주요 명령

```powershell
python scripts\hash_access_code.py
python scripts\bootstrap_database.py
python scripts\create_adjudication_assignments.py --output-dir exports\adjudication
python scripts\export_reviews.py --output-dir exports
```

SQLite 파일럿 자료는 기본 dry-run으로 확인한다.

```powershell
python scripts\migrate_sqlite_to_postgres.py `
  --sqlite-path "data\reviews.sqlite" `
  --database-url "$env:DATABASE_URL" `
  --dry-run
```

실제 이전은 `--apply`를 명시해야 한다.

