"""competitions / seasons 조회."""

import sqlite3

_COLUMNS = """
    id, code, name, type, emblem,
    area_id, area_name, area_code, area_flag,
    current_season_id, last_updated
"""


def list_competitions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """저장된 대회 전체를 반환한다."""
    return conn.execute(f"SELECT {_COLUMNS} FROM competitions ORDER BY code").fetchall()


def get_competition_by_code(conn: sqlite3.Connection, code: str) -> sqlite3.Row | None:
    return conn.execute(
        f"SELECT {_COLUMNS} FROM competitions WHERE code = ?", (code,)
    ).fetchone()


def get_competition_by_id(conn: sqlite3.Connection, competition_id: int) -> sqlite3.Row | None:
    """숫자 id 로 대회를 찾는다.

    라우팅 키는 code 지만, 경기 행처럼 competition_id 만 들고 있는 곳에서 쓴다.
    """
    return conn.execute(
        f"SELECT {_COLUMNS} FROM competitions WHERE id = ?", (competition_id,)
    ).fetchone()


_SEASON_COLUMNS = """
    id, competition_id, start_date, end_date, current_matchday, winner_team_id
"""


def get_season(conn: sqlite3.Connection, season_id: int) -> sqlite3.Row | None:
    """시즌 하나를 id 로 찾는다.

    ``get_current_season`` 은 competitions.current_season_id 를 따라가므로
    "이 경기가 속한 시즌"을 읽는 데는 쓸 수 없다. 그쪽은 대회의 현재 시즌이고,
    이쪽은 지목된 시즌이다.
    """
    return conn.execute(
        f"SELECT {_SEASON_COLUMNS} FROM seasons WHERE id = ?", (season_id,)
    ).fetchone()


def get_current_season(conn: sqlite3.Connection, competition_id: int) -> sqlite3.Row | None:
    """competitions.current_season_id 가 가리키는 시즌을 반환한다."""
    return conn.execute(
        """
        SELECT s.id, s.competition_id, s.start_date, s.end_date,
               s.current_matchday, s.winner_team_id
        FROM competitions c
        JOIN seasons s ON s.id = c.current_season_id
        WHERE c.id = ?
        """,
        (competition_id,),
    ).fetchone()
