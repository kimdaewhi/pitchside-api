"""상대전적 계산."""

import sqlite3

from app.leagues import get_league
from app.repositories import competitions as competitions_repo
from app.repositories import matches as matches_repo
from app.repositories import teams as teams_repo
from app.schemas.head_to_head import HeadToHeadResponse, HeadToHeadSummary
from app.services.common import (
    InvalidFilterError,
    NotIngestedError,
    to_match_summary,
    to_team_brief,
)

RECENT_LIMIT = 10


def _require_team(conn: sqlite3.Connection, team_id: int) -> sqlite3.Row:
    team = teams_repo.get_team(conn, team_id)
    if team is None:
        raise NotIngestedError(f"team {team_id}: 저장된 팀이 아닙니다")
    return team


def get_head_to_head(
    conn: sqlite3.Connection,
    team_id: int,
    opponent_id: int,
    *,
    competition_code: str | None = None,
    recent_limit: int = RECENT_LIMIT,
) -> HeadToHeadResponse:
    """두 팀의 FINISHED 경기를 집계한다.

    홈/원정이 뒤집히므로 반드시 양방향으로 조회한다.
    competition_code 는 선택 필터이고, 기본은 전 대회다.
    """
    if team_id == opponent_id:
        raise InvalidFilterError("같은 팀끼리는 상대전적을 낼 수 없습니다")

    team = _require_team(conn, team_id)
    opponent = _require_team(conn, opponent_id)

    competition_id = None
    if competition_code is not None:
        league = get_league(competition_code)  # 없는 코드면 LookupError
        competition = competitions_repo.get_competition_by_code(conn, league.code)
        if competition is None:
            raise NotIngestedError(f"{league.code}: 아직 수집되지 않았습니다")
        competition_id = competition["id"]
        competition_code = league.code

    totals = matches_repo.head_to_head_summary(
        conn, team_id, opponent_id, competition_id=competition_id
    )
    recent = matches_repo.list_head_to_head(
        conn, team_id, opponent_id, competition_id=competition_id, limit=recent_limit
    )

    return HeadToHeadResponse(
        summary=HeadToHeadSummary(
            team=to_team_brief(team),
            opponent=to_team_brief(opponent),
            played=totals["played"],
            won=totals["won"],
            draw=totals["draw"],
            lost=totals["lost"],
            goals_for=totals["goals_for"],
            goals_against=totals["goals_against"],
        ),
        competition_code=competition_code,
        recent_matches=[to_match_summary(row) for row in recent],
    )
