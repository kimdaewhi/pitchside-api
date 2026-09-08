"""팀 라우터."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db.connection import get_db
from app.routers.deps import require_league
from app.schemas.teams import FormGuide, TeamDetail, TeamsResponse

router = APIRouter(tags=["teams"])


@router.get("/competitions/{code}/teams", response_model=TeamsResponse)
def list_teams(code: str, conn: sqlite3.Connection = Depends(get_db)) -> TeamsResponse:
    require_league(code)  # 404 검증
    # TODO: services.teams.list_teams
    raise HTTPException(status_code=501, detail="not implemented")


@router.get("/teams/{team_id}", response_model=TeamDetail)
def get_team(team_id: int, conn: sqlite3.Connection = Depends(get_db)) -> TeamDetail:
    raise HTTPException(status_code=501, detail="not implemented")  # TODO: services.teams.get_team


@router.get("/competitions/{code}/teams/{team_id}/form", response_model=FormGuide)
def get_form(code: str, team_id: int, conn: sqlite3.Connection = Depends(get_db)) -> FormGuide:
    """최근 5경기 폼. 5경기 미만이면 있는 만큼만 나간다."""
    require_league(code)  # 404 검증
    # TODO: services.form.get_form_guide
    raise HTTPException(status_code=501, detail="not implemented")
