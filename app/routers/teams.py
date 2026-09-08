"""팀 라우터."""

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.db.connection import get_db
from app.routers.deps import require_league
from app.schemas.teams import FormGuide, TeamDetail, TeamsResponse
from app.services import form as form_service
from app.services import teams as teams_service

router = APIRouter(tags=["teams"])


@router.get("/competitions/{code}/teams", response_model=TeamsResponse)
def list_teams(code: str, conn: sqlite3.Connection = Depends(get_db)) -> TeamsResponse:
    return teams_service.list_teams(conn, require_league(code))


@router.get("/teams/{team_id}", response_model=TeamDetail)
def get_team(team_id: int, conn: sqlite3.Connection = Depends(get_db)) -> TeamDetail:
    return teams_service.get_team(conn, team_id)


@router.get("/competitions/{code}/teams/{team_id}/form", response_model=FormGuide)
def get_form(
    code: str,
    team_id: int,
    limit: int = Query(default=form_service.FORM_LENGTH, ge=1, le=20),
    conn: sqlite3.Connection = Depends(get_db),
) -> FormGuide:
    """최근 N경기 폼. N경기 미만이면 있는 만큼만 나간다."""
    return form_service.get_form_guide(conn, require_league(code), team_id, limit=limit)
