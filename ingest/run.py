"""배치 러너.

리그를 순차로 돈다. 병렬 금지 — 분당 10회 제한에 딱 붙어 있다.
한 리그가 실패해도 이력에 실패로 남기고 다음 리그로 넘어간다.
"""

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.leagues import LEAGUES, League
from ingest.client import FootballDataClient

DEFAULT_RESOURCES: tuple[str, ...] = ("standings", "matches")


@dataclass
class LeagueResult:
    competition_code: str
    resource: str
    status: str
    rows_written: int = 0
    error: str | None = None


@dataclass
class BatchReport:
    results: list[LeagueResult] = field(default_factory=list)

    @property
    def failed(self) -> list[LeagueResult]:
        return [r for r in self.results if r.status != "success"]

    @property
    def exit_code(self) -> int:
        """전부 실패했을 때만 0 이 아닌 코드를 낸다. 부분 실패는 cron 을 깨우지 않는다."""
        if not self.results:
            return 1
        return 1 if len(self.failed) == len(self.results) else 0


def collect_one(
    client: FootballDataClient,
    conn: sqlite3.Connection,
    league: League,
    resource: str,
) -> LeagueResult:
    """리그 하나 x 리소스 하나. 예외를 잡아 실패 결과로 바꾸고 이력을 남긴다."""
    # TODO: COLLECTORS[resource] 실행, try/except, writers.record_ingest_run
    raise NotImplementedError


def run_batch(
    *,
    resources: Sequence[str] = DEFAULT_RESOURCES,
    leagues: Sequence[League] = LEAGUES,
) -> BatchReport:
    """전체 배치.

    리그 바깥 루프 / 리소스 안쪽 루프로 순차 실행한다.
    호출 간격은 클라이언트의 RateLimiter 가 책임진다.
    """
    raise NotImplementedError  # TODO: 클라이언트·커넥션 준비 후 이중 루프, 결과를 BatchReport 로
