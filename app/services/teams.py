"""팀 서비스."""

import sqlite3

from app.leagues import League, get_league
from app.repositories import teams as teams_repo
from app.schemas.teams import TeamDetail, TeamsResponse
from app.services import form as form_service
from app.services.common import (
    NotIngestedError,
    resolve_current_season,
    to_competition_brief,
    to_team_brief,
)


def list_teams(conn: sqlite3.Connection, league: League) -> TeamsResponse:
    """현재 시즌 순위표에 등장하는 팀 목록."""
    competition, season = resolve_current_season(conn, league)
    rows = teams_repo.list_teams_in_competition(conn, competition["id"], season["id"])
    return TeamsResponse(
        competition=to_competition_brief(competition),
        count=len(rows),
        teams=[to_team_brief(row) for row in rows],
    )


def get_team(conn: sqlite3.Connection, team_id: int) -> TeamDetail:
    """팀 하나. 현재 시즌에 뛰고 있는 리그를 찾아 폼 가이드를 함께 붙인다.

    어느 리그 소속인지 경로에 없으므로 순위표에서 역으로 찾는다.
    찾지 못하면 폼 없이 팀 정보만 돌려준다.
    """
    team = teams_repo.get_team(conn, team_id)
    if team is None:
        raise NotIngestedError(f"team {team_id}: 저장된 팀이 아닙니다")

    competition = teams_repo.get_current_competition_for_team(conn, team_id)
    if competition is None:
        return TeamDetail(team=to_team_brief(team), form=None)

    league = get_league(competition["code"])
    return TeamDetail(
        team=to_team_brief(team),
        form=form_service.get_form_guide(conn, league, team_id),
    )
