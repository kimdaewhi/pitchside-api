"""일정·결과 응답."""

from pydantic import BaseModel

from app.schemas.common import CompetitionBrief, SeasonBrief, TeamBrief


class MatchScore(BaseModel):
    """경기 전에는 모든 필드가 null 이다."""

    winner: str | None = None
    full_time_home: int | None = None
    full_time_away: int | None = None
    half_time_home: int | None = None
    half_time_away: int | None = None


class MatchSummary(BaseModel):
    id: int
    utc_date: str
    status: str
    matchday: int | None = None
    stage: str | None = None
    group: str | None = None
    home_team: TeamBrief
    away_team: TeamBrief
    score: MatchScore


class MatchesResponse(BaseModel):
    competition: CompetitionBrief
    season: SeasonBrief
    count: int
    matches: list[MatchSummary]
