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


def recent_results(
    conn: sqlite3.Connection,
    team_id: int,
    competition_id: int,
    season_id: int,
    *,
    limit: int = FORM_LENGTH,
    before_utc_date: str | None = None,
) -> list[str]:
    """최신순 W/D/L 문자열 목록.

    폼을 쓰는 곳이 둘(``/teams/{id}/form``, 경기 상세)이라 조립 규칙을 여기 모은다.
    행에 붙어 오는 ``result`` 가 null 인 경우(점수 없는 경기)는 걸러낸다.

    ``before_utc_date`` 를 주면 그 시각 이전까지의 폼이 된다.
    """
    rows = matches_repo.list_recent_finished_for_team(
        conn,
        team_id,
        competition_id,
        season_id,
        limit=limit,
        before_utc_date=before_utc_date,
    )
    return [row["result"] for row in rows if row["result"] is not None]


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

    return FormGuide(
        team=to_team_brief(team),
        results=recent_results(conn, team_id, competition["id"], season["id"], limit=limit),
    )
