"""대회·시즌 수집.

거의 변하지 않으므로 standings/matches 보다 훨씬 긴 주기로 돈다.
``currentSeason.id`` 를 저장해 두고 다음 실행에서 비교해 시즌 전환을 감지한다.
"""

import sqlite3

from app.leagues import League
from ingest.client import FootballDataClient


def collect(client: FootballDataClient, conn: sqlite3.Connection, league: League) -> int:
    """대회 1건과 그 시즌들을 upsert 하고 쓴 행 수를 반환한다."""
    # TODO: client.get_competition → mappers → writers.upsert_competition/seasons
    raise NotImplementedError
