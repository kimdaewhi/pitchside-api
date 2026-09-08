"""대회 / 순위표 라우터."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db.connection import get_db
from app.routers.deps import require_league
from app.schemas.common import CompetitionBrief
from app.schemas.standings import StandingsResponse

router = APIRouter(prefix="/competitions", tags=["competitions"])


@router.get("", response_model=list[CompetitionBrief])
def list_competitions(conn: sqlite3.Connection = Depends(get_db)) -> list[CompetitionBrief]:
    """대상 리그 목록. 레지스트리 순서를 그대로 따른다."""
    # TODO: repositories.competitions.list_competitions, LEAGUES 와 대조
    raise HTTPException(status_code=501, detail="not implemented")


@router.get("/{code}/standings", response_model=StandingsResponse)
def get_standings(code: str, conn: sqlite3.Connection = Depends(get_db)) -> StandingsResponse:
    """현재 시즌 순위표."""
    require_league(code)  # 404 검증
    # TODO: services.standings.get_standings(conn, league)
    raise HTTPException(status_code=501, detail="not implemented")
