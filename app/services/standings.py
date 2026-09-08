"""순위표 서비스."""

import sqlite3

from app.leagues import League
from app.repositories import standings as standings_repo
from app.schemas.standings import StandingRow, StandingsResponse
from app.services.common import (
    resolve_current_season,
    to_competition_brief,
    to_season_brief,
    to_team_brief,
)

DEFAULT_STAGE = "REGULAR_SEASON"
DEFAULT_TYPE = "TOTAL"


def get_standings(
    conn: sqlite3.Connection,
    league: League,
    *,
    stage: str = DEFAULT_STAGE,
    type_: str = DEFAULT_TYPE,
) -> StandingsResponse:
    """해당 리그 현재 시즌의 순위표를 반환한다."""
    competition, season = resolve_current_season(conn, league)
    rows = standings_repo.get_standings(
        conn, competition["id"], season["id"], stage=stage, type_=type_
    )

    table = [
        StandingRow(
            position=row["position"],
            team=to_team_brief(row, "team_"),
            played_games=row["played_games"],
            won=row["won"],
            draw=row["draw"],
            lost=row["lost"],
            points=row["points"],
            goals_for=row["goals_for"],
            goals_against=row["goals_against"],
            goal_difference=row["goal_difference"],
        )
        for row in rows
    ]
    return StandingsResponse(
        competition=to_competition_brief(competition),
        season=to_season_brief(season),
        stage=stage,
        type=type_,
        # 블록이 비어 있으면 group 을 알 수 없다. 행이 있으면 저장된 값을 쓴다.
        group=rows[0]["group_name"] if rows else None,
        table=table,
    )
