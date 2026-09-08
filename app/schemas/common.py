"""여러 응답에서 공유하는 조각들."""

from pydantic import BaseModel


class TeamBrief(BaseModel):
    """팀 요약. standings 행과 matches 양쪽에 같은 모양으로 실린다."""

    id: int
    name: str
    short_name: str | None = None
    tla: str | None = None
    crest: str | None = None


class CompetitionBrief(BaseModel):
    """대회 요약. 라우팅 키는 숫자 id 가 아니라 code 다."""

    id: int
    code: str
    name: str
    emblem: str | None = None


class SeasonBrief(BaseModel):
    id: int
    start_date: str | None = None
    end_date: str | None = None
    current_matchday: int | None = None
