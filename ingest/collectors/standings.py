"""순위표 수집."""

import sqlite3

from app.leagues import League
from ingest.client import FootballDataClient


def collect(client: FootballDataClient, conn: sqlite3.Connection, league: League) -> int:
    """현재 시즌 순위표를 upsert 하고 쓴 행 수를 반환한다.

    standings[] 에서 블록을 조건으로 골라내고, 행에 실린 팀 스냅샷으로 팀 마스터도 갱신한다.
    """
    # TODO: get_standings → pick_standings_block → upsert_teams + upsert_standings
    raise NotImplementedError
