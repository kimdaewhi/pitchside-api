"""순위표 조회."""

import sqlite3

_SELECT = """
SELECT s.stage, s.type, s.group_name, s.position,
       s.played_games, s.won, s.draw, s.lost, s.points,
       s.goals_for, s.goals_against, s.goal_difference,
       t.id AS team_id, t.name AS team_name, t.short_name AS team_short_name,
       t.tla AS team_tla, t.crest AS team_crest
FROM standings s
JOIN teams t ON t.id = s.team_id
"""


def get_standings(
    conn: sqlite3.Connection,
    competition_id: int,
    season_id: int,
    *,
    stage: str = "REGULAR_SEASON",
    type_: str = "TOTAL",
) -> list[sqlite3.Row]:
    """(stage, type) 블록의 순위표를 position 순으로 반환한다.

    standings 는 (stage, type, group) 조합으로 여러 블록이 저장될 수 있으므로
    첫 블록을 무조건 집지 말고 조건으로 골라낸다.
    """
    return conn.execute(
        f"""
        {_SELECT}
        WHERE s.competition_id = :competition_id
          AND s.season_id = :season_id
          AND s.stage = :stage
          AND s.type = :type
        ORDER BY s.position
        """,
        {
            "competition_id": competition_id,
            "season_id": season_id,
            "stage": stage,
            "type": type_,
        },
    ).fetchall()
