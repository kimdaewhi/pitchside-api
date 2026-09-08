"""팀 조회."""

import sqlite3


def get_team(conn: sqlite3.Connection, team_id: int) -> sqlite3.Row | None:
    raise NotImplementedError  # TODO: SELECT ... FROM teams WHERE id = ?


def list_teams_in_competition(
    conn: sqlite3.Connection, competition_id: int, season_id: int
) -> list[sqlite3.Row]:
    """해당 시즌 순위표에 등장하는 팀들을 반환한다."""
    raise NotImplementedError  # TODO: standings JOIN teams, DISTINCT, ORDER BY name
