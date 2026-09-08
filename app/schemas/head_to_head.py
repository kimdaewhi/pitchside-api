"""상대전적 응답."""

from pydantic import BaseModel

from app.schemas.common import TeamBrief
from app.schemas.matches import MatchSummary


class HeadToHeadSummary(BaseModel):
    """FINISHED 경기만 집계한 결과. 승/무/패는 team 관점이다."""

    team: TeamBrief
    opponent: TeamBrief
    played: int
    won: int
    draw: int
    lost: int
    goals_for: int
    goals_against: int


class HeadToHeadResponse(BaseModel):
    summary: HeadToHeadSummary
    # 리그 필터는 선택. 지정하지 않으면 전 대회를 집계한다.
    competition_code: str | None = None
    recent_matches: list[MatchSummary]
