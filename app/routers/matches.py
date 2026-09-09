"""일정·결과 라우터.

대회 하위 경로(목록)와 최상위 경로(상세)가 함께 있어 prefix 를 두지 않는다.
match id 는 전역 고유하므로 상세는 리그 코드 없이 ``/matches/{id}`` 로 연다.
``app/routers/teams.py`` 가 같은 이유로 같은 모양을 하고 있다.
"""

from fastapi import APIRouter, Query

from app.db.connection import read_connection
from app.routers.deps import require_league
from app.schemas.match_detail import MatchDetail
from app.schemas.matches import MatchesResponse
from app.services import match_detail as match_detail_service
from app.services import matches as matches_service

router = APIRouter(tags=["matches"])


@router.get("/competitions/{code}/matches", response_model=MatchesResponse)
def list_matches(
    code: str,
    matchday: int | None = Query(default=None, ge=1),
    status: str | None = Query(default=None, description="SCHEDULED / FINISHED 등"),
) -> MatchesResponse:
    """현재 시즌 경기 목록."""
    league = require_league(code)
    with read_connection() as conn:
        return matches_service.list_matches(conn, league, matchday=matchday, status=status)


@router.get("/matches/{match_id}", response_model=MatchDetail)
def get_match_detail(match_id: int) -> MatchDetail:
    """경기 하나와 그 맥락 — 양 팀 순위·폼, 상대전적, 같은 라운드의 다른 경기.

    예정 경기도 같은 스키마로 나간다. 그때 score 는 전부 null 이다.
    """
    with read_connection() as conn:
        return match_detail_service.get_match_detail(conn, match_id)
