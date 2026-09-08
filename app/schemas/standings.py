"""순위표 응답."""

from pydantic import BaseModel

from app.schemas.common import CompetitionBrief, SeasonBrief, TeamBrief


class StandingRow(BaseModel):
    """순위표 한 줄.

    form 은 여기 없다. 외부 standings 의 form 은 항상 null 이라 쓸 수 없고,
    폼 가이드는 matches 에서 따로 계산해 별도 응답으로 내보낸다.
    """

    position: int
    team: TeamBrief
    played_games: int
    won: int
    draw: int
    lost: int
    points: int
    goals_for: int
    goals_against: int
    goal_difference: int


class StandingsResponse(BaseModel):
    competition: CompetitionBrief
    season: SeasonBrief
    stage: str
    type: str
    group: str | None = None
    table: list[StandingRow]
