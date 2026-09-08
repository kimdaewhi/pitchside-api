"""일정·결과 서비스."""

import sqlite3

from app.leagues import League
from app.repositories import matches as matches_repo
from app.schemas.matches import MatchesResponse
from app.services.common import (
    InvalidFilterError,
    resolve_current_season,
    to_competition_brief,
    to_match_summary,
    to_season_brief,
)

# 외부가 주는 status 전체. 오타를 빈 목록으로 돌려주면 디버깅이 어렵다.
VALID_STATUSES = frozenset(
    {
        "SCHEDULED",
        "TIMED",
        "IN_PLAY",
        "PAUSED",
        "FINISHED",
        "POSTPONED",
        "SUSPENDED",
        "CANCELLED",
    }
)


def list_matches(
    conn: sqlite3.Connection,
    league: League,
    *,
    matchday: int | None = None,
    status: str | None = None,
) -> MatchesResponse:
    """현재 시즌의 경기 목록. matchday / status 는 선택 필터다."""
    if status is not None:
        status = status.upper()
        if status not in VALID_STATUSES:
            raise InvalidFilterError(
                f"알 수 없는 status: {status} (가능: {', '.join(sorted(VALID_STATUSES))})"
            )

    competition, season = resolve_current_season(conn, league)
    rows = matches_repo.list_matches(
        conn, competition["id"], season["id"], matchday=matchday, status=status
    )
    matches = [to_match_summary(row) for row in rows]
    return MatchesResponse(
        competition=to_competition_brief(competition),
        season=to_season_brief(season),
        count=len(matches),
        matches=matches,
    )
