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
