"""상대전적 라우터."""

from fastapi import APIRouter, Query

from app.db.connection import read_connection
from app.routers.deps import require_league
from app.schemas.head_to_head import HeadToHeadResponse
from app.services import head_to_head as head_to_head_service

router = APIRouter(prefix="/teams", tags=["head-to-head"])


@router.get("/{team_id}/vs/{opponent_id}", response_model=HeadToHeadResponse)
def head_to_head(
    team_id: int,
    opponent_id: int,
    competition: str | None = Query(default=None, description="리그 코드. 생략하면 전 대회"),
    recent: int = Query(default=head_to_head_service.RECENT_LIMIT, ge=1, le=50),
) -> HeadToHeadResponse:
    # 없는 리그 코드는 여기서 404 로 걸러 서비스에 넘기지 않는다.
    code = require_league(competition).code if competition else None
    with read_connection() as conn:
        return head_to_head_service.get_head_to_head(
            conn, team_id, opponent_id, competition_code=code, recent_limit=recent
        )
