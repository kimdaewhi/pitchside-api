# ⚽ Pitchside API

유럽 5대 리그의 순위 / 일정·결과 / 팀 / 상대전적 대시보드용 백엔드.
FastAPI + SQLite. football-data.org 에서 배치로 수집해 저장하고, API 는 DB 만 조회한다.

> 현재는 **구조 스캐폴딩 단계**다. SQLite 연결과 스키마는 동작하지만
> 라우터 핸들러와 수집 로직 본문은 `NotImplementedError` + TODO 로 비어 있다.

---

## 🚀 시작하기

```bash
uv sync                       # 의존성 설치
cp .env.example .env          # FOOTBALL_DATA_API_KEY 채우기
uv run python -m app.db.init_db   # DB 파일 생성 + 스키마 적용 (WAL)
uv run uvicorn app.main:app --reload
```

`http://127.0.0.1:8000/docs` 에서 API 표면 전체를 볼 수 있다.

---

## 🗂️ 구조

| 디렉터리 | 역할 |
| --- | --- |
| `app/routers/` | HTTP 계층. 파라미터 검증과 응답 모델 선언까지. SQL 금지 |
| `app/services/` | 도메인·파생 계산 (폼 가이드, 상대전적) |
| `app/repositories/` | 조회 SQL 전용. HTTP 금지 |
| `app/schemas/` | Pydantic 응답 모델. 외부 camelCase 를 snake_case 로 재정의 |
| `app/db/` | SQLite 연결(WAL/PRAGMA)과 `schema.sql` |
| `app/leagues.py` | 리그 레지스트리 |
| `ingest/` | 수집 배치. FastAPI 와 독립 실행 |

**의존 방향** — `routers → services → repositories → db`. 역방향 import 는 없다.
`ingest` 는 `app.db.connection` 과 `app.leagues` 만 공유하고 FastAPI 를 로드하지 않는다.

**읽기/쓰기 분리** — 읽기 커넥션은 `PRAGMA query_only=ON` 이라 요청 경로에서 쓰기가
나가면 즉시 에러가 난다. 쓰기는 수집 배치 하나로 직렬화된다.

---

## 🔄 수집 배치

앱 안에 스케줄러를 두지 않는다. 외부 cron 이 아래 명령을 부른다.

```bash
uv run python -m ingest --resource standings,matches
uv run python -m ingest --resource competitions        # 주기를 훨씬 길게
uv run python -m ingest --resource standings --league PL
```

분당 10회 제한이라 리그별 순차 수집에 호출 사이 6~7초를 둔다. 병렬 금지.
한 리그가 실패해도 `ingest_runs` 에 실패로 남기고 다음 리그를 계속 수집한다.

cron 예시:

```cron
*/15 * * * *  cd /srv/pitchside-api && uv run python -m ingest --resource standings,matches
0    4 * * *  cd /srv/pitchside-api && uv run python -m ingest --resource competitions
```

---

## 🏆 리그 추가

`app/leagues.py` 의 `LEAGUES` 에 항목 하나를 더한다. 다른 파일은 건드리지 않는다.

```python
League("DED", 2003, "Eredivisie", "Netherlands"),
```

---

## ✅ 테스트

```bash
uv run pytest
uv run ruff check .
```
