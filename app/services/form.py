"""폼 가이드 계산.

DB 에 없는 파생 값이다. 외부 standings 의 form 은 항상 null 이라 못 쓴다.
W/D/L 판정 자체는 리포지토리의 SQL CASE 가 한다 — 같은 규칙을 폼 가이드와
상대전적 두 곳에 따로 쓰지 않기 위해서다.
"""

import sqlite3

from app.leagues import League
from app.repositories import matches as matches_repo
from app.repositories import teams as teams_repo
from app.schemas.teams import FormGuide
from app.services.common import NotIngestedError, resolve_current_season, to_team_brief

FORM_LENGTH = 5


def get_form_guide(
    conn: sqlite3.Connection, league: League, team_id: int, *, limit: int = FORM_LENGTH
) -> FormGuide:
    """해당 팀의 그 시즌·리그 FINISHED 경기 중 최근 N 경기로 W/D/L 을 만든다.

    홈/원정을 모두 포함하고, 승패 판정은 해당 팀 관점이다.
    N 경기 미만이면 있는 만큼만 반환한다 (패딩 금지).
    """
    competition, season = resolve_current_season(conn, league)

    team = teams_repo.get_team(conn, team_id)
    if team is None:
        raise NotIngestedError(f"team {team_id}: 저장된 팀이 아닙니다")

    rows = matches_repo.list_recent_finished_for_team(
        conn, team_id, competition["id"], season["id"], limit=limit
    )
    return FormGuide(
        team=to_team_brief(team),
        results=[row["result"] for row in rows if row["result"] is not None],
    )
