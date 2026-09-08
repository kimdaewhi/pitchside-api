"""폼 가이드 계산.

DB 에 없는 파생 값이다. 외부 standings 의 form 은 항상 null 이라 못 쓴다.
"""

import sqlite3

from app.leagues import League
from app.schemas.teams import FormGuide

FORM_LENGTH = 5


def get_form_guide(
    conn: sqlite3.Connection, league: League, team_id: int, *, limit: int = FORM_LENGTH
) -> FormGuide:
    """해당 팀의 그 시즌·리그 FINISHED 경기 중 최근 N 경기로 W/D/L 을 만든다.

    홈/원정을 모두 포함하고, 승패 판정은 해당 팀 관점이다.
    N 경기 미만이면 있는 만큼만 반환한다 (패딩 금지).
    """
    # TODO: repositories.matches.list_recent_finished_for_team → 팀 관점 W/D/L 변환
    raise NotImplementedError


def _result_for_team(row, team_id: int) -> str:
    """경기 한 건을 해당 팀 관점의 'W' / 'D' / 'L' 로 변환한다."""
    raise NotImplementedError  # TODO: home/away 판별 후 full_time 점수 비교
