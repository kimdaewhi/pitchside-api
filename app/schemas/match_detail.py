"""경기 상세 응답.

경기 하나와 그 경기를 읽는 데 필요한 맥락을 함께 담는다.
끝난 경기와 예정 경기가 같은 스키마를 쓰고, 예정 경기는 score 가 전부 null 이다.
"""

from pydantic import BaseModel

from app.schemas.common import CompetitionBrief, SeasonBrief, TeamBrief
from app.schemas.head_to_head import HeadToHeadSummary
from app.schemas.matches import MatchSummary


class TeamStanding(BaseModel):
    """순위표에서 뽑은 그 팀의 자리.

    ``StandingRow`` 를 재사용하지 않는 이유는 그쪽이 ``team`` 을 품고 있어서다.
    이 응답에는 팀 브리프가 이미 두 군데 있어 세 번째가 되면 잡음이다.

    **경기 시점의 스냅샷이 아니라 현재 값이다.** 순위표는 수집 때마다 덮어써서
    과거 시점 순위를 복원할 수 없다. 끝난 경기에서는 form / head_to_head 와
    기준 시점이 어긋난다.
    """

    position: int
    played_games: int
    won: int
    draw: int
    lost: int
    points: int
    goals_for: int
    goals_against: int
    goal_difference: int


class TeamMatchContext(BaseModel):
    """한 팀을 이 경기의 맥락에서 본 것."""

    team: TeamBrief
    # 현재 시즌 순위표에 없는 팀이면 null.
    standing: TeamStanding | None = None
    # 이 경기 이전 기준의 최신순 W/D/L. 패딩하지 않으므로 빈 배열일 수 있다.
    form: list[str] = []


class MatchDetail(BaseModel):
    """경기 상세.

    form 과 head_to_head 는 **이 경기 이전** 기준이라 경기 자신을 포함하지 않는다.
    standing 만 현재 값이다 (위 참고).
    """

    match: MatchSummary
    competition: CompetitionBrief
    season: SeasonBrief
    home: TeamMatchContext
    away: TeamMatchContext
    # 승/무/패는 홈 팀 관점이다.
    head_to_head: HeadToHeadSummary
    # 최신순. 이 경기는 빠진다.
    recent_meetings: list[MatchSummary]
    # 같은 라운드의 다른 경기들. 킥오프순이고 상태를 가리지 않는다.
    same_matchday: list[MatchSummary]
