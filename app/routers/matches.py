"""일정·결과 라우터."""

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.db.connection import get_db
from app.routers.deps import require_league
from app.schemas.matches import MatchesResponse
from app.services import matches as matches_service

router = APIRouter(prefix="/competitions", tags=["matches"])


@router.get("/{code}/matches", response_model=MatchesResponse)
def list_matches(
    code: str,
    matchday: int | None = Query(default=None, ge=1),
    status: str | None = Query(default=None, description="SCHEDULED / FINISHED 등"),
    conn: sqlite3.Connection = Depends(get_db),
) -> MatchesResponse:
    """현재 시즌 경기 목록."""
    return matches_service.list_matches(
        conn, require_league(code), matchday=matchday, status=status
    )
