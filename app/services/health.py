"""수집 상태 서비스."""

import sqlite3

from app.leagues import LEAGUES
from app.repositories import ingest_runs as ingest_runs_repo
from app.schemas.health import IngestHealthResponse, LeagueIngestStatus

# 수집 이력이 아예 없는 리그도 드러내기 위한 기본 리소스 목록.
# ingest/ 의 DEFAULT_RESOURCES 와 같은 값이지만, app 계층은 ingest 를 import 하지 않는다.
EXPECTED_RESOURCES: tuple[str, ...] = ("standings", "matches")


def get_ingest_health(conn: sqlite3.Connection) -> IngestHealthResponse:
    """리그·리소스별 마지막 수집 성공 시각과 마지막 실행 상태.

    한 번도 수집되지 않은 리그는 이력 테이블에 아예 없다. 그대로 두면 헬스에서
    사라져 버리므로, 레지스트리에 있는데 이력이 없는 리그는 null 로 채워 넣는다.
    """
    successes = {
        (row["competition_code"], row["resource"]): row["finished_at"]
        for row in ingest_runs_repo.last_success_per_league(conn)
    }
    last_runs = {
        (row["competition_code"], row["resource"]): row["status"]
        for row in ingest_runs_repo.last_run_per_league(conn)
    }

    keys = set(successes) | set(last_runs)
    seen_codes = {code for code, _ in keys}
    for league in LEAGUES:
        if league.code not in seen_codes:
            keys.update((league.code, resource) for resource in EXPECTED_RESOURCES)

    return IngestHealthResponse(
        leagues=[
            LeagueIngestStatus(
                competition_code=code,
                resource=resource,
                last_success_at=successes.get((code, resource)),
                last_status=last_runs.get((code, resource)),
            )
            for code, resource in sorted(keys)
        ]
    )
