"""경기 수집.

증분 수집은 하지 않는다. 매 실행마다 현재 시즌 전체를 다시 가져와 upsert 한다.
(``matches.lastUpdated`` 가 오지만 지금은 쓰지 않는다.)
"""

import sqlite3

from app.leagues import League
from ingest import mappers, writers
from ingest.client import FootballDataClient


def collect(client: FootballDataClient, conn: sqlite3.Connection, league: League) -> int:
    """현재 시즌 경기 전체를 upsert 하고 쓴 행 수를 반환한다.

    경기 목록 응답에는 최상위 season 이 없고 경기마다 인라인으로 실려 온다.
    그래서 시즌 행은 경기들에서 뽑아낸다.
    """
    payload = client.get_matches(league.external_id)
    matches = payload.get("matches") or []
    if not matches:
        # 시즌 시작 전이면 빈 목록이 온다. 실패가 아니다.
        return 0

    competition = mappers.to_competition_row(
        payload["competition"], current_season_id=matches[0]["season"]["id"]
    )
    writers.upsert_competition(conn, competition)

    # 보통 한 시즌이지만 응답이 여러 시즌에 걸쳐도 깨지지 않게 id 로 모은다.
    seasons = {match["season"]["id"]: match["season"] for match in matches}
    writers.upsert_seasons(
        conn,
        [mappers.to_season_row(season, competition["id"]) for season in seasons.values()],
    )
    writers.upsert_teams(conn, mappers.to_team_rows_from_matches(payload))
    return writers.upsert_matches(conn, mappers.to_match_rows(payload))
