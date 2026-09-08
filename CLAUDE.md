# ⚽ Pitchside API

유럽 5대 리그의 순위 / 일정·결과 / 팀 / 상대전적 대시보드용 백엔드.
FastAPI + SQLite. football-data.org에서 배치로 수집해 저장하고, API는 DB만 조회한다.

---

## 🧭 아키텍처 원칙

- **요청 경로에서 외부 호출 금지** — 라우터/서비스는 DB만 읽는다.
  응답이 비어 있다면 그건 "아직 수집 안 된 것"이지 프록시할 대상이 아니다.
- **competition 단위 분리** — 모든 도메인 데이터는 competition으로 구분하고, 시즌으로 한 번 더 나뉜다.
- **리그 레지스트리** — 리그 추가는 코드 수정이 아니라 레지스트리 항목 추가로 끝나야 한다.
  `if code == "PL"` 같은 리그별 분기 금지.
- **계층 분리** — `routers/`(HTTP) → `services/`(도메인·계산) → `repositories/`(SQL).
  라우터에 SQL, 리포지토리에 HTTP 금지.
- **수집기 독립** — `ingest/` 아래에 두고 FastAPI 앱과 독립 실행 가능해야 한다.
  외부 API 클라이언트는 `ingest/` 한 곳에만 두고 레이트리밋도 그 안에서 처리한다.

---

## 🏆 대상 범위

- **리그** — Premier League(PL), La Liga(PD), Ligue 1(FL1), Serie A(SA), Bundesliga(BL1).
- **라우팅 키** — 숫자 id가 아니라 competition code를 쓴다 (`/competitions/PL/standings`).
- **현재 시즌만** — 과거 시즌 백필은 하지 않는다.
- **스코프 밖** — 실시간 스코어 / 로그인·유저 / 라인업·카드·점유율 등 상세 스탯 / 배당.
  "나중에 필요할 수도"로 이쪽 테이블이나 필드를 미리 만들지 않는다.

---

## 🔄 수집 배치

- **실행 방식** — 외부 cron. 앱 내 스케줄러를 두지 않는다.
- **분당 10회 제한** — 리그별 순차 수집, 호출 사이 6~7초. 병렬 금지.
  전체 1회 = 5리그 x (standings + matches) = 10콜이라 딱 한도에 붙는다.
- **429 대응** — 지수 백오프 후 재시도. 실패한 리그는 실패로 기록하되
  다음 리그 수집은 계속 진행한다. 한 리그 실패가 배치 전체를 죽이면 안 된다.
- **전체 재수집** — 매 실행마다 현재 시즌 전체를 다시 가져온다.
  증분 수집은 하지 않는다 (`matches.lastUpdated`가 오지만 지금은 쓰지 않는다).
- **멱등성** — 쓰기는 전부 upsert. 삭제하지 않는다. 몇 번을 돌려도 결과가 같아야 한다.
- **competitions 주기** — 거의 안 변한다. standings/matches보다 훨씬 길게 잡는다.
- **수집 이력** — 테이블에 남기고, 리그별 마지막 성공 시각을 헬스 엔드포인트로 노출한다.

---

## ⚠️ 외부 응답의 함정

- **`form`은 항상 null** — standings 응답의 form은 못 쓴다. 폼 가이드는 matches에서 직접 계산한다.
- **`standings[]`는 배열** — `stage` / `type`(TOTAL·HOME·AWAY) / `group` 조합 블록이 온다.
  5대 리그는 REGULAR_SEASON + TOTAL 단일 블록이지만, 첫 원소를 무조건 쓰지 말고 조건으로 골라낸다.
- **점수는 null 가능** — `score.fullTime` / `halfTime` / `winner`는 경기 전이면 null.
  NOT NULL 제약 금지.
- **집계는 FINISHED만** — `status`는 SCHEDULED / TIMED / IN_PLAY / PAUSED / FINISHED /
  POSTPONED / SUSPENDED / CANCELLED. 나머지는 폼·상대전적 집계에서 제외한다.
- **시각은 UTC** — `utcDate`를 DB에 UTC 그대로 저장하고, 변환은 표현 계층에서만.
- **전역 고유 id** — match id와 team id는 리그·시즌과 무관하게 고유하다. 그대로 PK로 쓴다.
- **팀 정보 인라인** — standings 행과 matches 양쪽에 팀 스냅샷이 들어온다. 팀 마스터 갱신에 활용한다.
- **버리는 필드** — `odds`는 잠김 메시지만 오고, `referees`는 저장하지 않는다.
- **시즌 전환** — `competitions.currentSeason.id` 비교로 감지한다.

---

## 🧮 파생 계산

DB에 없어서 계산해야 하는 값들. SQL(윈도우 함수) 우선, 파이썬 후처리는 SQL이 어려울 때만.

- **폼 가이드** — 해당 팀의 그 시즌·리그 FINISHED 경기 중 최근 5경기를 최신순으로 가져와
  W/D/L 문자열 생성. 홈/원정 모두 포함, 관점은 해당 팀 기준.
  5경기 미만이면 있는 만큼만 반환한다 (패딩 금지).
- **상대전적** — 두 팀의 FINISHED 경기. 리그 필터는 선택 인자, 기본은 전 대회.
  홈/원정이 뒤집히므로 `(home, away)` 단방향 조회로는 절반을 놓친다. 양방향으로 조회할 것.

---

## 🗄️ SQLite

- **WAL 모드 필수** — 배치 쓰기와 API 읽기가 동시에 일어난다.
- **PRAGMA** — `foreign_keys=ON`, `busy_timeout` 설정.
- **쓰기 단일화** — 쓰기는 배치 프로세스 하나로 직렬화한다. 요청 경로에서 쓰기 금지.

---

## 🔧 그 외

- **응답 스키마 재정의** — 외부 응답을 그대로 흘려보내지 않는다.
  Pydantic 모델로 재정의하고 snake_case로 통일한다 (외부는 camelCase).
- **API 키** — 환경변수(`FOOTBALL_DATA_API_KEY`). 커밋 금지.
