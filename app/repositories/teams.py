"""팀 조회."""

import sqlite3

_COLUMNS = "id, name, short_name, tla, crest, updated_at"


def get_team(conn: sqlite3.Connection, team_id: int) -> sqlite3.Row | None:
    return conn.execute(f"SELECT {_COLUMNS} FROM teams WHERE id = ?", (team_id,)).fetchone()


def list_teams_in_competition(
    conn: sqlite3.Connection, competition_id: int, season_id: int
) -> list[sqlite3.Row]:
    """해당 시즌 순위표에 등장하는 팀들을 반환한다."""
    return conn.execute(
        """
        SELECT DISTINCT t.id, t.name, t.short_name, t.tla, t.crest, t.updated_at
        FROM standings s
        JOIN teams t ON t.id = s.team_id
        WHERE s.competition_id = ? AND s.season_id = ?
        ORDER BY t.name
        """,
        (competition_id, season_id),
    ).fetchall()


def get_current_competition_for_team(
    conn: sqlite3.Connection, team_id: int
) -> sqlite3.Row | None:
    """이 팀이 현재 시즌에 뛰고 있는 대회를 찾는다.

    ``/teams/{id}`` 처럼 리그를 지정하지 않은 경로에서 폼 가이드를 붙이는 데 쓴다.
    현재 시즌 순위표에 없으면 None.
    """
    return conn.execute(
        """
        SELECT c.id, c.code, c.name, c.emblem, s.id AS season_id
        FROM standings st
        JOIN competitions c ON c.id = st.competition_id
        JOIN seasons s ON s.id = st.season_id
        WHERE st.team_id = ? AND c.current_season_id = s.id
        LIMIT 1
        """,
        (team_id,),
    ).fetchone()
