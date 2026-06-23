# 운영 매뉴얼

## 배포 전

1. public CSV와 PNG 수가 일치하는지 확인한다.
2. `verify_deployment_bundle.py`를 실행한다.
3. Supabase schema를 생성하고 SSL 연결 URL을 확보한다.
4. reviewer별 접근코드를 만들고 bcrypt hash만 Secrets에 입력한다.
5. 전문가 앱과 관리자 앱을 각각 배포한다.
6. A/B 계정은 `primary`, C는 `adjudicator`, admin은 `admin`인지 확인한다.

## 판정 중

- 관리자는 관리자 앱에서 reviewer별 배정·완료·미완료 수만 확인한다.
- reviewer는 자신의 사례, 판정, 진행률만 볼 수 있다.
- 정기적으로 `scripts/export_reviews.py` 또는 관리자 다운로드를 사용해
  암호화된 연구자 저장소에 백업한다.
- reviewer 비활성화는 Streamlit Secrets에서 해당 reviewer hash와 role을
  제거한다. Secrets에 없는 계정은 로그인할 수 없다.
- 접근코드 변경은 새 hash를 생성해 Streamlit Secrets의 해당 값만 교체한다.

## A/B 판정 후

관리자 앱의 배정 버튼 또는 다음 스크립트를 실행한다.

```powershell
python scripts\create_adjudication_assignments.py `
  --reviewer-a reviewer_a `
  --reviewer-b reviewer_b `
  --adjudicator reviewer_c `
  --output-dir exports\adjudication
```

A/B가 모두 판정했고 라벨이 다른 사례만 C에게 활성 배정된다. C의 기존 판정은
덮어쓰지 않는다.

## Consensus와 신뢰도 export

```powershell
python scripts\export_reviews.py --output-dir exports
```

reviewer 완료율, 라벨 분포, 평균 confidence, pairwise Cohen's kappa, 완전
일치율, Fleiss' kappa, consensus CSV가 생성된다.

private mapping과 알고리즘 결과 병합은 이 배포 repository에서 하지 않는다.
연구자 로컬의 별도 비공개 분석 환경에서만 수행한다.

## 연구 종료 후

1. PostgreSQL 결과와 audit log를 export하고 무결성을 확인한다.
2. 기관 보존정책에 따라 DB를 보관하거나 삭제한다.
3. Streamlit 앱 배포를 중지하거나 삭제한다.
4. reviewer 접근코드와 DB password를 폐기 또는 회전한다.
5. GitHub private repository 접근권한을 정리한다.
