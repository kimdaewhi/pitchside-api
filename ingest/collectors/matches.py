"""경기 수집.

증분 수집은 하지 않는다. 매 실행마다 현재 시즌 전체를 다시 가져와 upsert 한다.
(``matches.lastUpdated`` 가 오지만 지금은 쓰지 않는다.)
"""

import sqlite3

from app.leagues import League
from ingest.client import FootballDataClient


def collect(client: FootballDataClient, conn: sqlite3.Connection, league: League) -> int:
    """현재 시즌 경기 전체를 upsert 하고 쓴 행 수를 반환한다."""
    raise NotImplementedError  # TODO: get_matches → 팀 스냅샷 upsert → upsert_matches
