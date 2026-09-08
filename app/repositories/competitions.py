"""competitions / seasons 조회."""

import sqlite3


def list_competitions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """저장된 대회 전체를 반환한다."""
    raise NotImplementedError  # TODO: SELECT ... FROM competitions ORDER BY code


def get_competition_by_code(conn: sqlite3.Connection, code: str) -> sqlite3.Row | None:
    raise NotImplementedError  # TODO: SELECT ... FROM competitions WHERE code = ?


def get_current_season(conn: sqlite3.Connection, competition_id: int) -> sqlite3.Row | None:
    """competitions.current_season_id 가 가리키는 시즌을 반환한다."""
    raise NotImplementedError  # TODO: competitions JOIN seasons ON current_season_id
