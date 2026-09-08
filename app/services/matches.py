"""일정·결과 서비스."""

import sqlite3

from app.leagues import League
from app.schemas.matches import MatchesResponse


def list_matches(
    conn: sqlite3.Connection,
    league: League,
    *,
    matchday: int | None = None,
    status: str | None = None,
) -> MatchesResponse:
    # TODO: 현재 시즌 확인 → repositories.matches.list_matches → 스키마 조립
    raise NotImplementedError
