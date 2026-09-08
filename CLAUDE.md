# ⚽ Pitchside API

유럽 5대 리그의 순위 / 일정·결과 / 팀 / 상대전적 대시보드용 백엔드.
FastAPI + SQLite. football-data.org에서 배치로 수집해 저장하고, API는 DB만 조회한다.

---

## 🧭 아키텍처 원칙

- **요청 경로에서 외부 호출 금지** — 라우터/서비스는 DB만 읽는다.
  응답이 비어 있다면 그건 "아직 수집 안 된 것"이지 프록시할 대상이 아니다.
- **competition 단위 분리** — 모든 도메인 데이터는 competition으로 구분하고, 시즌으로 한 번 더 나뉜다.
- **리그 레지스트리** — 리그 추가는 코드 수정이 아니라 `app/leagues.py` 항목 추가로 끝나야 한다.
  `if code == "PL"` 같은 리그별 분기 금지.
- **계층 분리** — `routers/`(HTTP) → `services/`(도메인·계산) → `repositories/`(SQL).
  라우터에 SQL, 리포지토리에 HTTP 금지. 이 경계는 `tests/test_layering.py`가 강제한다.
- **읽기 SQL과 쓰기 SQL 분리** — `repositories/`는 읽기 전용, upsert는 `ingest/writers.py`.
- **수집기 독립** — `ingest/`는 FastAPI 없이 실행된다. 공유는 `app.db.connection`과 `app.leagues`까지.
  그래서 `leagues.py`는 프레임워크를 import하지 않고, 404 변환은 `routers/deps.py`가 맡는다.

---

## 🏆 대상 범위

- **리그** — Premier League(PL), La Liga(PD), Ligue 1(FL1), Serie A(SA), Bundesliga(BL1).
- **라우팅 키** — 대회는 숫자 id가 아니라 code로 라우팅한다 (`/competitions/PL/standings`).
  팀은 전역 고유 id를 경로에 그대로 쓴다 (`/teams/81`).
- **현재 시즌만** — 과거 시즌 백필은 하지 않는다.
- **스코프 밖** — 실시간 스코어 / 로그인·유저 / 라인업·카드·점유율 등 상세 스탯 / 배당.
  "나중에 필요할 수도"로 이쪽 테이블이나 필드를 미리 만들지 않는다.

---

## 🔄 수집 배치

- **실행 방식** — 외부 cron이 `python -m ingest`를 부른다. 앱 내 스케줄러를 두지 않는다.
- **분당 10회 제한** — 리그별 순차 수집, 호출 사이 6~7초. 병렬 금지.
  전체 1회 = 5리그 x (standings + matches) = 10콜이라 딱 한도에 붙는다.
- **재시도는 429만** — 지수 백오프, `Retry-After`가 더 길면 그쪽을 따른다.
  타임아웃·5xx는 재시도하지 않는다. 한 리그를 붙잡으면 남은 리그가 한도 안에 못 들어온다.
- **실패 격리** — 트랜잭션 단위는 (리그 x 리소스)다. 단위마다 커밋해 부분 진행을 남기고,
  실패한 리그는 실패로 기록한 뒤 다음 리그로 넘어간다. 실패한 단위는 롤백하되
  수집 이력은 그 뒤에 따로 커밋한다. 같이 쓸려 나가면 실패를 볼 수 없다.
- **전체 재수집** — 매 실행마다 현재 시즌 전체를 다시 가져온다.
  증분 수집은 하지 않는다 (`matches.lastUpdated`가 오지만 지금은 쓰지 않는다).
- **멱등성** — 쓰기는 전부 upsert. 삭제하지 않는다. 몇 번을 돌려도 결과가 같아야 한다.
- **기본 리소스** — `standings,matches`. `competitions`는 거의 안 변하므로 별도의 긴 주기로.
- **종료 코드** — 0 전부·일부 성공 / 1 전부 실패 / 2 인자 오류. 부분 실패로 cron을 깨우지 않는다.
- **수집 이력** — 테이블에 남기고, 리그별 마지막 성공 시각을 헬스 엔드포인트로 노출한다.

---

## ⚠️ 외부 응답의 함정

- **`form`은 항상 null** — 못 쓰고, 저장하지도 않는다. 폼 가이드는 matches에서 직접 계산한다.
- **`standings[]`는 배열** — `stage` / `type`(TOTAL·HOME·AWAY) / `group` 조합 블록이 온다.
  5대 리그는 REGULAR_SEASON + TOTAL 단일 블록이지만, 첫 원소를 무조건 쓰지 말고 조건으로 골라낸다.
- **`group`은 null이 아니다** — `"Matchday"` 같은 문자열이고 리그마다 다르다.
  블록 선별 조건에 넣지 말 것. 순위표 PK의 일부라 없으면 빈 문자열로 둔다.
- **점수는 null 가능** — `score.fullTime` / `halfTime` / `winner`는 경기 전이면 null. NOT NULL 금지.
- **집계는 FINISHED만** — SCHEDULED·TIMED·IN_PLAY·PAUSED·POSTPONED·SUSPENDED·CANCELLED는
  폼·상대전적 집계에서 제외한다.
- **인라인 객체는 슬림하다** — standings·matches의 competition에는 `area`와 `currentSeason`이 없고,
  matches에는 최상위 season이 아예 없어 경기 인라인에서 뽑아야 한다.
- **시각은 UTC** — `utcDate`를 DB에 UTC 그대로 저장하고, 변환은 표현 계층에서만.
- **전역 고유 id** — match id와 team id는 리그·시즌과 무관하게 고유하다. 그대로 PK로 쓴다.
- **팀 정보 인라인** — standings 행과 matches 양쪽에 팀 스냅샷이 들어온다. 팀 마스터 갱신에 활용한다.
- **버리는 필드** — `odds`는 잠김 메시지만 오고, `referees`는 저장하지 않는다.
- **시즌 전환** — `competitions.currentSeason.id` 비교로 감지한다.

---

## 🧮 파생 계산

DB에 없어서 계산해야 하는 값들. SQL 우선, 파이썬 후처리는 SQL이 어려울 때만.

- **폼 가이드** — 그 시즌·리그 FINISHED 경기 중 최근 5경기를 최신순으로. 홈/원정 모두 포함,
  관점은 해당 팀 기준. 5경기 미만이면 있는 만큼만 반환한다 (패딩 금지).
- **상대전적** — 두 팀의 FINISHED 경기. 리그 필터는 선택 인자, 기본은 전 대회.
  홈/원정이 뒤집히므로 `(home, away)` 단방향 조회로는 절반을 놓친다. 양방향으로 조회할 것.
  승/무/패와 득실 합계도 SQL에서 끝낸다.
- **승패 판정은 한 곳에만** — 팀 관점 W/D/L은 `repositories/matches.py`의 SQL CASE가 만든다.
  폼 가이드와 상대전적이 같은 규칙을 공유해야 하므로 파이썬으로 다시 쓰지 않는다.

---

## 🗄️ SQLite

- **WAL 모드 필수** — 배치 쓰기와 API 읽기가 동시에 일어난다.
- **PRAGMA** — `foreign_keys=ON`, `busy_timeout` 설정.
- **읽기/쓰기 커넥션 분리** — 읽기 커넥션은 `query_only=ON`으로 요청 경로의 쓰기를 런타임에서 막는다.
  쓰기 커넥션은 수집 배치에서만 연다.
- **커넥션은 한 스레드 안에서** — `check_same_thread`는 기본값(True)을 유지한다.
  끄면 스레드를 넘나드는 사용이 에러 대신 조용한 데이터 경합으로 바뀐다.
  커넥션을 스레드 사이로 넘기는 대신 요청마다 새로 여는 것이 전제다.
- **커넥션을 `Depends`로 주입하지 않는다** — 아래 함정 항목을 볼 것.
- **쓰기 순서** — FK 때문에 `competitions → seasons → teams → standings / matches`를 지킨다.
- **덮어쓰기 정책** — 슬림한 인라인 스냅샷에서 빠지는 값(엠블럼, area, 팀 약칭·크레스트)은
  `COALESCE`로 지키고, 순위·점수·상태처럼 매번 새로 받는 값은 그대로 덮어쓴다.
- **`seasons`는 현재 시즌만** — `winner_team_id`가 참조하는 과거 우승팀이 팀 마스터에 없어 FK가 깨진다.
- **스키마 관리** — `app/db/schema.sql`을 `CREATE ... IF NOT EXISTS`로 멱등 적용. 마이그레이션 도구 없음.

---

## 🕳️ 스레드 함정

FastAPI는 동기 핸들러를 워커 스레드 풀에서 돌린다. SQLite 커넥션은 만든 스레드에서만
쓸 수 있어서, 요청 하나가 스레드를 넘어가면 `sqlite3.ProgrammingError`로 500이 난다.

- **커넥션 주입 금지** — 커넥션을 넘겨주는 FastAPI 의존성(`Depends(get_db)`)을 두지 않는다.
  동기 제너레이터 의존성은 진입 / 핸들러 본문 / 정리를 FastAPI가 각각 별도의
  `anyio.to_thread.run_sync`로 돌린다. 요청이 몰려 워커가 재배치되면 커넥션을 연 스레드와
  쓰는 스레드가 갈린다. 정리(`close`)도 또 다른 스레드에서 돌아 같은 이유로 터진다.
- **핸들러 본문에서 연다** — 동기 핸들러 본문은 통째로 한 워커 스레드에서 실행된다.
  `with read_connection() as conn:`을 라우터 함수 안에 두면 열기·조회·닫기가 한 스레드에 묶인다.
- **`check_same_thread=False`는 해법이 아니다** — 가드만 끌 뿐 공유는 그대로 남는다.
  터지는 대신 조용히 깨진다.
- **동시 요청으로만 드러난다** — 단발 요청은 워커가 재배치되지 않아 항상 통과한다.
  회귀는 `tests/test_thread_safety.py`가 동시 요청과 정적 검사 양쪽으로 막는다.

---

## 🌐 API 응답 규약

- **응답 스키마 재정의** — 외부 응답을 그대로 흘려보내지 않는다.
  Pydantic 모델로 재정의하고 snake_case로 통일한다 (외부는 camelCase).
- **404는 두 종류** — "없는 코드"와 "아직 수집 안 됨"은 메시지를 구분한다. 후자를 외부 호출로 메우지 않는다.
- **잘못된 필터는 400** — 알 수 없는 `status` 같은 값을 빈 목록으로 돌려주지 않는다.
- **서비스는 HTTP를 모른다** — 도메인 예외로 올리고, 상태 코드 변환은 `app/main.py`의 핸들러가 한다.
- **헬스는 빈 리그도 드러낸다** — 이력이 없는 리그를 목록에서 빼면 실패가 보이지 않는다.

---

## 🔧 그 외

- **도구** — 패키지는 uv, DB는 stdlib `sqlite3` + 손으로 쓴 SQL. ORM은 쓰지 않는다.
- **API 키** — 환경변수(`FOOTBALL_DATA_API_KEY`). 커밋 금지.
  터미널이나 로그에 값을 출력하지 않는다. 확인이 필요하면 존재 여부만 표시한다.
