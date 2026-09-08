"""순위표 수집.

응답 하나에 대회·시즌·팀·순위가 모두 들어 있어서, 이 수집기만 돌려도
FK 를 만족하는 최소 집합이 채워진다.
"""

import sqlite3

from app.leagues import League
from ingest import mappers, writers
from ingest.client import FootballDataClient, FootballDataError


def collect(client: FootballDataClient, conn: sqlite3.Connection, league: League) -> int:
    """현재 시즌 순위표를 upsert 하고 쓴 행 수를 반환한다.

    standings[] 에서 블록을 조건으로 골라내고, 행에 실린 팀 스냅샷으로 팀 마스터도 갱신한다.
    쓰기 순서는 FK 를 따른다 — competitions → seasons → teams → standings.
    """
    payload = client.get_standings(league.external_id)

    block = mappers.pick_standings_block(payload)
    if block is None:
        raise FootballDataError(f"{league.code}: REGULAR_SEASON/TOTAL 블록이 없다")

    season = payload["season"]
    competition = mappers.to_competition_row(
        payload["competition"], current_season_id=season["id"]
    )
    writers.upsert_competition(conn, competition)
    writers.upsert_seasons(conn, [mappers.to_season_row(season, competition["id"])])
    writers.upsert_teams(conn, mappers.to_team_rows_from_standings(block))
    return writers.upsert_standings(conn, mappers.to_standing_rows(payload, block))
