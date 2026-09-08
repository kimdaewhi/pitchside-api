"""순위표 서비스."""

import sqlite3

from app.leagues import League
from app.schemas.standings import StandingsResponse


def get_standings(conn: sqlite3.Connection, league: League) -> StandingsResponse:
    """해당 리그 현재 시즌의 순위표를 반환한다."""
    raise NotImplementedError  # TODO: competitions/seasons 조회 → standings 조회 → 스키마 조립
