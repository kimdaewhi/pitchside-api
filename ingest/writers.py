"""쓰기 전용 SQL.

쓰기는 전부 upsert 다. 삭제하지 않는다. 몇 번을 돌려도 결과가 같아야 한다.
조회 SQL 은 여기가 아니라 ``app/repositories/`` 에 있다.

**호출 순서** — foreign_keys=ON 이므로 참조 대상을 먼저 써야 한다.

    competitions → seasons → teams → standings / matches

teams 는 standings·matches 보다만 앞서면 되고 competitions 와는 무관하다.

**덮어쓰기 정책** — 두 갈래로 나뉜다.

* 장식성 필드(엠블럼, area, 팀 약칭 등)는 ``COALESCE`` 로 기존 값을 지킨다.
  같은 대회·팀이 슬림한 인라인 스냅샷으로도 실려 오기 때문에, 그걸로 덮으면
  이미 채운 값이 null 로 날아간다.
* 순위·점수·상태처럼 매번 새로 받아오는 값은 그대로 덮어쓴다. 외부가 정답이다.
"""

import sqlite3
from typing import Any

_UPSERT_TEAMS = """
INSERT INTO teams (id, name, short_name, tla, crest, updated_at)
VALUES (:id, :name, :short_name, :tla, :crest, :updated_at)
ON CONFLICT(id) DO UPDATE SET
    name       = excluded.name,
    short_name = COALESCE(excluded.short_name, teams.short_name),
    tla        = COALESCE(excluded.tla, teams.tla),
    crest      = COALESCE(excluded.crest, teams.crest),
    updated_at = excluded.updated_at
"""

_UPSERT_COMPETITION = """
INSERT INTO competitions (
    id, code, name, type, emblem,
    area_id, area_name, area_code, area_flag,
    current_season_id, last_updated
)
VALUES (
    :id, :code, :name, :type, :emblem,
    :area_id, :area_name, :area_code, :area_flag,
    :current_season_id, :last_updated
)
ON CONFLICT(id) DO UPDATE SET
    code              = excluded.code,
    name              = excluded.name,
    type              = COALESCE(excluded.type, competitions.type),
    emblem            = COALESCE(excluded.emblem, competitions.emblem),
    area_id           = COALESCE(excluded.area_id, competitions.area_id),
    area_name         = COALESCE(excluded.area_name, competitions.area_name),
    area_code         = COALESCE(excluded.area_code, competitions.area_code),
    area_flag         = COALESCE(excluded.area_flag, competitions.area_flag),
    current_season_id = COALESCE(excluded.current_season_id, competitions.current_season_id),
    last_updated      = COALESCE(excluded.last_updated, competitions.last_updated)
"""

_UPSERT_SEASONS = """
INSERT INTO seasons (id, competition_id, start_date, end_date, current_matchday, winner_team_id)
VALUES (:id, :competition_id, :start_date, :end_date, :current_matchday, :winner_team_id)
ON CONFLICT(id) DO UPDATE SET
    competition_id   = excluded.competition_id,
    start_date       = COALESCE(excluded.start_date, seasons.start_date),
    end_date         = COALESCE(excluded.end_date, seasons.end_date),
    current_matchday = COALESCE(excluded.current_matchday, seasons.current_matchday),
    winner_team_id   = COALESCE(excluded.winner_team_id, seasons.winner_team_id)
"""

_UPSERT_STANDINGS = """
INSERT INTO standings (
    competition_id, season_id, stage, type, group_name, team_id,
    position, played_games, won, draw, lost, points,
    goals_for, goals_against, goal_difference
)
VALUES (
    :competition_id, :season_id, :stage, :type, :group_name, :team_id,
    :position, :played_games, :won, :draw, :lost, :points,
    :goals_for, :goals_against, :goal_difference
)
ON CONFLICT(competition_id, season_id, stage, type, group_name, team_id) DO UPDATE SET
    position        = excluded.position,
    played_games    = excluded.played_games,
    won             = excluded.won,
    draw            = excluded.draw,
    lost            = excluded.lost,
    points          = excluded.points,
    goals_for       = excluded.goals_for,
    goals_against   = excluded.goals_against,
    goal_difference = excluded.goal_difference
"""

_UPSERT_MATCHES = """
INSERT INTO matches (
    id, competition_id, season_id, utc_date, status, matchday, stage, group_name,
    home_team_id, away_team_id, winner, duration,
    full_time_home, full_time_away, half_time_home, half_time_away, last_updated
)
VALUES (
    :id, :competition_id, :season_id, :utc_date, :status, :matchday, :stage, :group_name,
    :home_team_id, :away_team_id, :winner, :duration,
    :full_time_home, :full_time_away, :half_time_home, :half_time_away, :last_updated
)
ON CONFLICT(id) DO UPDATE SET
    competition_id = excluded.competition_id,
    season_id      = excluded.season_id,
    utc_date       = excluded.utc_date,
    status         = excluded.status,
    matchday       = excluded.matchday,
    stage          = excluded.stage,
    group_name     = excluded.group_name,
    home_team_id   = excluded.home_team_id,
    away_team_id   = excluded.away_team_id,
    winner         = excluded.winner,
    duration       = excluded.duration,
    full_time_home = excluded.full_time_home,
    full_time_away = excluded.full_time_away,
    half_time_home = excluded.half_time_home,
    half_time_away = excluded.half_time_away,
    last_updated   = excluded.last_updated
"""

_INSERT_INGEST_RUN = """
INSERT INTO ingest_runs (
    competition_code, resource, status, started_at, finished_at,
    rows_written, http_status, error
)
VALUES (
    :competition_code, :resource, :status, :started_at, :finished_at,
    :rows_written, :http_status, :error
)
"""


def _executemany(conn: sqlite3.Connection, sql: str, rows: list[dict[str, Any]]) -> int:
    """행 목록을 한 번에 쓰고 쓴 행 수를 반환한다."""
    if not rows:
        return 0
    cursor = conn.executemany(sql, rows)
    # 일부 드라이버는 executemany 후 rowcount 를 -1 로 둔다. 그럴 땐 시도한 수로 갈음한다.
    return cursor.rowcount if cursor.rowcount >= 0 else len(rows)


def upsert_teams(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    return _executemany(conn, _UPSERT_TEAMS, rows)


def upsert_competition(conn: sqlite3.Connection, row: dict[str, Any]) -> int:
    return _executemany(conn, _UPSERT_COMPETITION, [row])


def upsert_seasons(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    return _executemany(conn, _UPSERT_SEASONS, rows)


def upsert_standings(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    """복합 PK (competition_id, season_id, stage, type, group_name, team_id) 기준 upsert."""
    return _executemany(conn, _UPSERT_STANDINGS, rows)


def upsert_matches(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    return _executemany(conn, _UPSERT_MATCHES, rows)


def record_ingest_run(
    conn: sqlite3.Connection,
    *,
    competition_code: str,
    resource: str,
    status: str,
    started_at: str,
    finished_at: str,
    rows_written: int | None = None,
    http_status: int | None = None,
    error: str | None = None,
) -> None:
    """수집 이력 한 줄. 성공이든 실패든 남긴다."""
    conn.execute(
        _INSERT_INGEST_RUN,
        {
            "competition_code": competition_code,
            "resource": resource,
            "status": status,
            "started_at": started_at,
            "finished_at": finished_at,
            "rows_written": rows_written,
            "http_status": http_status,
            "error": error,
        },
    )
