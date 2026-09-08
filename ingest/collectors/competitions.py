"""대회·시즌 수집.

거의 변하지 않으므로 standings/matches 보다 훨씬 긴 주기로 돈다.
``currentSeason.id`` 를 저장해 두고 다음 실행에서 비교해 시즌 전환을 감지한다.

seasons[] 에 과거 시즌이 딸려 오지만 저장하지 않는다. 과거 시즌 백필은 하지 않고,
과거 우승팀은 팀 마스터에 없어 winner_team_id FK 가 깨진다.
"""

import sqlite3

from app.leagues import League
from ingest import mappers, writers
from ingest.client import FootballDataClient


def collect(client: FootballDataClient, conn: sqlite3.Connection, league: League) -> int:
    """대회 1건과 현재 시즌을 upsert 하고 쓴 행 수를 반환한다."""
    payload = client.get_competition(league.external_id)

    competition = mappers.to_competition_row(payload)
    written = writers.upsert_competition(conn, competition)

    current_season = payload.get("currentSeason")
    if current_season:
        # 시즌이 막 끝나 winner 가 채워졌다면 그 팀이 teams 에 있어야 한다.
        # 신규 DB 에서 이 수집기를 standings 보다 먼저 돌리면 FK 로 실패할 수 있고,
        # 그 경우 실패로 기록된 뒤 다음 실행에서 성공한다.
        written += writers.upsert_seasons(
            conn, [mappers.to_season_row(current_season, competition["id"])]
        )
    return written
