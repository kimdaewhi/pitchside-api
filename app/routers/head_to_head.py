"""상대전적 라우터."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.connection import get_db
from app.schemas.head_to_head import HeadToHeadResponse

router = APIRouter(prefix="/teams", tags=["head-to-head"])


@router.get("/{team_id}/vs/{opponent_id}", response_model=HeadToHeadResponse)
def head_to_head(
    team_id: int,
    opponent_id: int,
    competition: str | None = Query(default=None, description="리그 코드. 생략하면 전 대회"),
    conn: sqlite3.Connection = Depends(get_db),
) -> HeadToHeadResponse:
    # TODO: services.head_to_head.get_head_to_head
    raise HTTPException(status_code=501, detail="not implemented")
