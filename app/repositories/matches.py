"""경기 조회.

폼 가이드와 상대전적은 홈/원정이 뒤집히므로 단방향 조회로는 절반을 놓친다.
아래 함수들은 전부 양방향(home_team_id OR away_team_id)으로 조회한다.

승패 판정은 SQL 의 CASE 로 처리한다. 파이썬으로 후처리하면 같은 규칙을
폼 가이드와 상대전적 두 곳에 따로 쓰게 된다.
"""

import sqlite3

FINISHED = "FINISHED"

_COLUMNS = """
    m.id, m.competition_id, m.season_id, m.utc_date, m.status,
    m.matchday, m.stage, m.group_name,
    m.winner, m.duration,
    m.full_time_home, m.full_time_away, m.half_time_home, m.half_time_away,
    h.id AS home_id, h.name AS home_name, h.short_name AS home_short_name,
    h.tla AS home_tla, h.crest AS home_crest,
    a.id AS away_id, a.name AS away_name, a.short_name AS away_short_name,
    a.tla AS away_tla, a.crest AS away_crest
"""

_FROM = """
FROM matches m
JOIN teams h ON h.id = m.home_team_id
JOIN teams a ON a.id = m.away_team_id
"""

# 해당 팀 관점의 W/D/L. 점수가 없으면(경기 전) NULL.
_RESULT_CASE = """
    CASE
        WHEN m.full_time_home IS NULL OR m.full_time_away IS NULL THEN NULL
        WHEN m.home_team_id = :team_id THEN
            CASE WHEN m.full_time_home > m.full_time_away THEN 'W'
                 WHEN m.full_time_home = m.full_time_away THEN 'D'
                 ELSE 'L' END
        ELSE
            CASE WHEN m.full_time_away > m.full_time_home THEN 'W'
                 WHEN m.full_time_away = m.full_time_home THEN 'D'
                 ELSE 'L' END
    END AS result
"""


def _select(*, with_result: bool = False) -> str:
    """SELECT 목록과 FROM 을 조립한다.

    ``result`` 는 SELECT 목록 안에 들어가야 하므로 FROM 뒤에 이어 붙이면 안 된다.
    """
    columns = f"{_COLUMNS.rstrip()},\n{_RESULT_CASE}" if with_result else _COLUMNS
    return f"SELECT {columns}{_FROM}"


def get_match(conn: sqlite3.Connection, match_id: int) -> sqlite3.Row | None:
    """경기 하나. match id 는 리그·시즌과 무관하게 전역 고유하다.

    ``list_matches`` 와 같은 ``_select()`` 를 쓰므로 컬럼 모양이 같다.
    서비스 쪽에서 같은 변환 함수로 받을 수 있다.
    """
    return conn.execute(f"{_select()} WHERE m.id = :match_id", {"match_id": match_id}).fetchone()


def list_matches(
    conn: sqlite3.Connection,
    competition_id: int,
    season_id: int,
    *,
    matchday: int | None = None,
    status: str | None = None,
) -> list[sqlite3.Row]:
    """해당 시즌의 경기를 utc_date 순으로 반환한다."""
    clauses = ["m.competition_id = :competition_id", "m.season_id = :season_id"]
    params: dict[str, object] = {"competition_id": competition_id, "season_id": season_id}
    if matchday is not None:
        clauses.append("m.matchday = :matchday")
        params["matchday"] = matchday
    if status is not None:
        clauses.append("m.status = :status")
        params["status"] = status

    return conn.execute(
        f"{_select()} WHERE {' AND '.join(clauses)} ORDER BY m.utc_date, m.id", params
    ).fetchall()


def list_recent_finished_for_team(
    conn: sqlite3.Connection,
    team_id: int,
    competition_id: int,
    season_id: int,
    *,
    limit: int = 5,
    before_utc_date: str | None = None,
) -> list[sqlite3.Row]:
    """폼 가이드용. 해당 팀의 그 시즌·리그 FINISHED 경기를 최신순으로 최대 limit 개.

    홈/원정을 모두 포함한다. limit 에 못 미치면 있는 만큼만 반환하고 패딩하지 않는다.
    각 행에 해당 팀 관점의 ``result`` (W/D/L) 가 붙어 나온다.

    ``before_utc_date`` 를 주면 그 시각 **미만**의 경기만 본다. 경기 상세에서
    "그 경기에 들어갈 때의 폼"을 만드는 데 쓴다. 미만이라 기준 경기 자신은 물론,
    같은 시각에 열린 다른 경기도 빠진다 — 킥오프 시점에 아직 끝나지 않았으므로 맞다.
    """
    clauses = [
        "m.status = :finished",
        "m.competition_id = :competition_id",
        "m.season_id = :season_id",
        "(m.home_team_id = :team_id OR m.away_team_id = :team_id)",
    ]
    params: dict[str, object] = {
        "finished": FINISHED,
        "competition_id": competition_id,
        "season_id": season_id,
        "team_id": team_id,
        "limit": limit,
    }
    if before_utc_date is not None:
        clauses.append("m.utc_date < :before_utc_date")
        params["before_utc_date"] = before_utc_date

    return conn.execute(
        f"""
        {_select(with_result=True)}
        WHERE {" AND ".join(clauses)}
        ORDER BY m.utc_date DESC, m.id DESC
        LIMIT :limit
        """,
        params,
    ).fetchall()


def _head_to_head_where(
    competition_id: int | None, before_utc_date: str | None = None
) -> tuple[str, dict[str, object]]:
    """양방향 조건. 리그 필터는 선택이고 기본은 전 대회다.

    ``before_utc_date`` 도 선택이다. 주면 그 시각 미만의 맞대결만 센다 —
    경기 상세에서 "이 경기 이전까지의 상대전적"을 낼 때 쓴다.
    조건을 여기 한 곳에 모아 두므로 요약과 목록이 같은 집합을 본다.
    """
    clause = (
        "m.status = :finished AND ("
        "  (m.home_team_id = :team_id AND m.away_team_id = :opponent_id)"
        "  OR (m.home_team_id = :opponent_id AND m.away_team_id = :team_id)"
        ")"
    )
    params: dict[str, object] = {"finished": FINISHED}
    if competition_id is not None:
        clause += " AND m.competition_id = :competition_id"
        params["competition_id"] = competition_id
    if before_utc_date is not None:
        clause += " AND m.utc_date < :before_utc_date"
        params["before_utc_date"] = before_utc_date
    return clause, params


def list_head_to_head(
    conn: sqlite3.Connection,
    team_id: int,
    opponent_id: int,
    *,
    competition_id: int | None = None,
    limit: int | None = None,
    before_utc_date: str | None = None,
) -> list[sqlite3.Row]:
    """두 팀의 FINISHED 경기를 최신순으로 반환한다.

    competition_id 는 선택 인자다. None 이면 전 대회를 대상으로 한다.
    """
    where, params = _head_to_head_where(competition_id, before_utc_date)
    params |= {"team_id": team_id, "opponent_id": opponent_id}
    sql = (
        f"{_select(with_result=True)} WHERE {where} ORDER BY m.utc_date DESC, m.id DESC"
    )
    if limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = limit
    return conn.execute(sql, params).fetchall()


def head_to_head_summary(
    conn: sqlite3.Connection,
    team_id: int,
    opponent_id: int,
    *,
    competition_id: int | None = None,
    before_utc_date: str | None = None,
) -> sqlite3.Row:
    """team_id 관점의 승/무/패와 득실 합계.

    집계를 SQL 로 끝낸다. 경기가 없으면 played=0 인 행 하나가 나온다.
    """
    where, params = _head_to_head_where(competition_id, before_utc_date)
    params |= {"team_id": team_id, "opponent_id": opponent_id}
    return conn.execute(
        f"""
        SELECT
            COUNT(*) AS played,
            COALESCE(SUM(CASE
                WHEN m.home_team_id = :team_id AND m.full_time_home > m.full_time_away THEN 1
                WHEN m.away_team_id = :team_id AND m.full_time_away > m.full_time_home THEN 1
                ELSE 0 END), 0) AS won,
            COALESCE(SUM(CASE
                WHEN m.full_time_home = m.full_time_away THEN 1
                ELSE 0 END), 0) AS draw,
            COALESCE(SUM(CASE
                WHEN m.home_team_id = :team_id AND m.full_time_home < m.full_time_away THEN 1
                WHEN m.away_team_id = :team_id AND m.full_time_away < m.full_time_home THEN 1
                ELSE 0 END), 0) AS lost,
            COALESCE(SUM(CASE
                WHEN m.home_team_id = :team_id THEN m.full_time_home
                ELSE m.full_time_away END), 0) AS goals_for,
            COALESCE(SUM(CASE
                WHEN m.home_team_id = :team_id THEN m.full_time_away
                ELSE m.full_time_home END), 0) AS goals_against
        FROM matches m
        WHERE {where}
        """,
        params,
    ).fetchone()
