# Streamlit Community Cloud 배포

공식 배포 문서:
<https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app>

공식 Secrets 문서:
<https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management>

## 1. GitHub private repository

1. GitHub에서 새 **Private** repository를 만든다.
2. ZIP의 `radon_expert_review_app/` 내부 파일만 repository root에 올린다.
3. 업로드 전에 다음을 실행한다.

```powershell
python scripts\verify_deployment_bundle.py
```

## 2. Secrets 준비

`secrets.toml.example`을 참고해 실제 값을 별도 텍스트에 준비한다.

```toml
DATABASE_URL = "postgresql+psycopg://...?...sslmode=require"

[auth]
order_seed = "긴 무작위 문자열"
session_secret = "다른 긴 무작위 문자열"

[reviewers]
reviewer_a = "$2b$..."
reviewer_b = "$2b$..."
reviewer_c = "$2b$..."
admin = "$2b$..."

[reviewer_roles]
reviewer_a = "primary"
reviewer_b = "primary"
reviewer_c = "adjudicator"
admin = "admin"
```

실제 `.streamlit/secrets.toml`은 repository에 만들거나 commit하지 않는다.

## 3. 전문가 앱 배포

1. Streamlit Community Cloud workspace에서 **Create app**을 선택한다.
2. GitHub private repository 접근을 승인하고 repository를 선택한다.
3. Main file path로 `app.py`를 선택한다.
4. Advanced settings의 Secrets에 준비한 TOML을 붙여넣는다.
5. Deploy를 실행한다.
6. 로그에서 dependency 설치와 DB 초기화 성공을 확인한다.
7. 전문가에게 배포 URL, 본인의 reviewer ID, 본인의 평문 접근코드만 전달한다.

Streamlit 공식 문서에 따라 Secrets는 repository가 아니라 app settings에
저장하며, 배포 후에도 settings에서 변경할 수 있다.

## 4. 관리자 앱 별도 배포

같은 repository로 앱을 하나 더 만들고 main file을 `admin_dashboard.py`로
선택한다. 동일한 Secrets를 입력한다. 관리자 URL은 전문가에게 전달하지 않는다.

## 5. 배포 확인

1. admin 계정으로 관리자 앱에 로그인한다.
2. DB 연결 오류가 없는지 확인한다.
3. reviewer A로 전문가 앱에 로그인해 전체 사례 수가 표시되는지 확인한다.
4. 테스트 판정 후 브라우저를 닫고 재접속하여 저장 상태가 유지되는지 확인한다.
5. 연구 시작 전 테스트 행은 필요하면 Supabase SQL Editor에서 명시적으로
   삭제하고, 임의 삭제 전에 반드시 백업한다.

