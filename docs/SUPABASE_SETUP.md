# Supabase 설정

## 1. 계정과 프로젝트 생성

1. <https://supabase.com>에서 계정을 만든다.
2. 새 Project를 생성하고 강한 Database password를 설정한다.
3. 프로젝트 region은 전문가와 가까운 위치를 선택한다.

## 2. Schema 생성

Supabase Dashboard의 **SQL Editor**를 열고 `sql/001_initial_schema.sql` 전체를
실행한다. SQL은 `IF NOT EXISTS`를 사용하므로 다시 실행해도 기존 판정을
삭제하지 않는다. SQL은 모든 운영 테이블에 RLS를 활성화하고 anon/authenticated
정책을 만들지 않으므로 Supabase Data API에서는 읽을 수 없다. 앱은 service role
key가 아니라 PostgreSQL 연결문자열을 사용한다.

## 3. PostgreSQL 연결문자열 확보

Dashboard의 **Connect**에서 connection string을 복사한다.

- Direct connection은 장기 실행 backend에 적합하지만 프로젝트 endpoint가
  IPv6일 수 있다.
- IPv4 환경에서는 Shared Pooler session mode를 사용할 수 있다.
- transaction mode도 사용할 수 있으며 앱은 psycopg prepared statement를
  비활성화하도록 설정돼 있다.

공식 연결 방식 설명:
<https://supabase.com/docs/guides/database/connecting-to-postgres>

URL 끝에 `sslmode=require`가 없으면 추가한다. 앱은 `postgres://`,
`postgresql://`, `postgresql+psycopg://` 형식을 모두 받는다.

```text
postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=require
```

비밀번호에 `@`, `:`, `/`, `#` 같은 문자가 있으면 URL encoding해야 한다.

## 4. DATABASE_URL 보관

`DATABASE_URL`은 GitHub에 저장하지 않는다. Streamlit Community Cloud의
Secrets에만 입력한다. Supabase service role key는 사용하지 않는다. 이 앱은
PostgreSQL 연결문자열로만 DB에 접속한다.

## 5. Reviewer hash 생성

각 reviewer마다 다른 접근코드를 만들고 로컬에서 hash를 생성한다.

```powershell
python scripts\hash_access_code.py
```

출력된 bcrypt hash만 Streamlit Secrets에 넣는다.

## 6. 연결 확인 및 seed

로컬 환경변수를 임시 설정한 후 실행할 수 있다.

```powershell
$env:DATABASE_URL="postgresql+psycopg://..."
python scripts\bootstrap_database.py
```

이 명령은 schema를 확인하고 `review_cases_public.csv`의 public case를
`review_cases`에 idempotent하게 seed한다. 앱 시작 시에도 같은 작업을 수행한다.

## 7. 백업과 export

Supabase Dashboard의 backup 기능은 plan에 따라 다르므로 사용 중인 plan의
Database Backups 설정을 확인한다. 연구 중에는 애플리케이션 export도 정기적으로
실행한다.

```powershell
python scripts\export_reviews.py --output-dir exports
```

`exports/`는 `.gitignore` 대상이며 GitHub에 올리지 않는다.
