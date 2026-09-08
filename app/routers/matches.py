"""일정·결과 라우터."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.connection import get_db
from app.routers.deps import require_league
from app.schemas.matches import MatchesResponse

router = APIRouter(prefix="/competitions", tags=["matches"])


@router.get("/{code}/matches", response_model=MatchesResponse)
def list_matches(
    code: str,
    matchday: int | None = Query(default=None, ge=1),
    status: str | None = Query(default=None, description="SCHEDULED / FINISHED 등"),
    conn: sqlite3.Connection = Depends(get_db),
) -> MatchesResponse:
    """현재 시즌 경기 목록."""
    require_league(code)  # 404 검증
    # TODO: services.matches.list_matches
    raise HTTPException(status_code=501, detail="not implemented")
