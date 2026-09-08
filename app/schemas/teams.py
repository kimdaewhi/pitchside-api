"""팀 응답."""

from pydantic import BaseModel

from app.schemas.common import CompetitionBrief, TeamBrief


class TeamsResponse(BaseModel):
    competition: CompetitionBrief
    count: int
    teams: list[TeamBrief]


class FormGuide(BaseModel):
    """최근 5경기 폼.

    5경기 미만이면 있는 만큼만 채운다. 패딩하지 않으므로 길이가 5 미만일 수 있다.
    """

    team: TeamBrief
    # 최신순 W/D/L 문자. 예: ["W", "W", "D"]
    results: list[str]


class TeamDetail(BaseModel):
    team: TeamBrief
    form: FormGuide | None = None
