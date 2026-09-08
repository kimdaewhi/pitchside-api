-- Pitchside API 스키마.
-- 전부 CREATE ... IF NOT EXISTS 로 멱등하게 적용된다.
-- 샘플 응답에서 실제로 확인된 필드만 만든다. "나중에 쓸지도 모를" 컬럼은 두지 않는다.

-- 팀 마스터.
-- standings 행과 matches 양쪽에 인라인으로 오는 팀 스냅샷으로 갱신한다.
-- team id 는 리그·시즌과 무관하게 전역 고유하므로 그대로 PK 로 쓴다.
CREATE TABLE IF NOT EXISTS teams (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    short_name  TEXT,
    tla         TEXT,
    crest       TEXT,
    updated_at  TEXT NOT NULL
);

-- 대회. 5대 리그 레지스트리와 1:1 로 대응한다.
CREATE TABLE IF NOT EXISTS competitions (
    id                INTEGER PRIMARY KEY,
    code              TEXT NOT NULL UNIQUE,
    name              TEXT NOT NULL,
    type              TEXT,
    emblem            TEXT,
    area_id           INTEGER,
    area_name         TEXT,
    area_code         TEXT,
    area_flag         TEXT,
    current_season_id INTEGER,
    last_updated      TEXT
);

-- 시즌. currentSeason.id 비교로 시즌 전환을 감지한다.
CREATE TABLE IF NOT EXISTS seasons (
    id               INTEGER PRIMARY KEY,
    competition_id   INTEGER NOT NULL REFERENCES competitions(id),
    start_date       TEXT,
    end_date         TEXT,
    current_matchday INTEGER,
    -- 시즌 종료 전에는 null 로 온다.
    winner_team_id   INTEGER REFERENCES teams(id)
);

-- 순위표.
-- standings[] 는 (stage, type, group) 조합 블록의 배열이라 PK 에 셋 다 넣는다.
-- 5대 리그는 REGULAR_SEASON + TOTAL 단일 블록이지만 구조로 열어둔다.
-- form 컬럼은 두지 않는다 — 외부 form 은 항상 null 이고 폼 가이드는 matches 에서 계산한다.
CREATE TABLE IF NOT EXISTS standings (
    competition_id  INTEGER NOT NULL REFERENCES competitions(id),
    season_id       INTEGER NOT NULL REFERENCES seasons(id),
    stage           TEXT NOT NULL,
    type            TEXT NOT NULL,   -- TOTAL | HOME | AWAY
    group_name      TEXT NOT NULL DEFAULT '',
    team_id         INTEGER NOT NULL REFERENCES teams(id),
    position        INTEGER NOT NULL,
    played_games    INTEGER NOT NULL,
    won             INTEGER NOT NULL,
    draw            INTEGER NOT NULL,
    lost            INTEGER NOT NULL,
    points          INTEGER NOT NULL,
    goals_for       INTEGER NOT NULL,
    goals_against   INTEGER NOT NULL,
    goal_difference INTEGER NOT NULL,
    PRIMARY KEY (competition_id, season_id, stage, type, group_name, team_id)
);

-- 경기.
-- 점수 관련 컬럼은 경기 전이면 전부 null 이므로 NOT NULL 을 걸지 않는다.
-- utc_date 는 UTC 문자열 그대로 저장하고 변환은 표현 계층에서만 한다.
CREATE TABLE IF NOT EXISTS matches (
    id              INTEGER PRIMARY KEY,
    competition_id  INTEGER NOT NULL REFERENCES competitions(id),
    season_id       INTEGER NOT NULL REFERENCES seasons(id),
    utc_date        TEXT NOT NULL,
    status          TEXT NOT NULL,
    matchday        INTEGER,
    stage           TEXT,
    group_name      TEXT,
    home_team_id    INTEGER NOT NULL REFERENCES teams(id),
    away_team_id    INTEGER NOT NULL REFERENCES teams(id),
    winner          TEXT,            -- HOME_TEAM | AWAY_TEAM | DRAW | null
    duration        TEXT,
    full_time_home  INTEGER,
    full_time_away  INTEGER,
    half_time_home  INTEGER,
    half_time_away  INTEGER,
    last_updated    TEXT
);

-- 일정·결과 목록 조회.
CREATE INDEX IF NOT EXISTS idx_matches_competition_season_date
    ON matches (competition_id, season_id, utc_date);

-- 폼 가이드와 상대전적은 홈/원정 양방향으로 조회해야 해서 인덱스도 양쪽에 건다.
CREATE INDEX IF NOT EXISTS idx_matches_home_status ON matches (home_team_id, status, utc_date);
CREATE INDEX IF NOT EXISTS idx_matches_away_status ON matches (away_team_id, status, utc_date);

-- 수집 이력. 리그별 마지막 성공 시각을 헬스 엔드포인트로 노출하는 데 쓴다.
-- 실패한 리그도 행을 남긴다. 한 리그 실패가 배치 전체를 죽이면 안 된다.
CREATE TABLE IF NOT EXISTS ingest_runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_code TEXT NOT NULL,
    resource         TEXT NOT NULL,   -- competitions | standings | matches
    status           TEXT NOT NULL,   -- success | failure
    started_at       TEXT NOT NULL,
    finished_at      TEXT NOT NULL,
    rows_written     INTEGER,
    http_status      INTEGER,
    error            TEXT
);

CREATE INDEX IF NOT EXISTS idx_ingest_runs_lookup
    ON ingest_runs (competition_code, resource, status, finished_at DESC);
