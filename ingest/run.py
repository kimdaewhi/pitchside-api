"""배치 러너.

리그를 순차로 돈다. 병렬 금지 — 분당 10회 제한에 딱 붙어 있다.
한 리그가 실패해도 이력에 실패로 남기고 다음 리그로 넘어간다.

**트랜잭션 단위는 (리그 x 리소스) 하나다.** 배치 전체를 한 트랜잭션으로 묶으면
후반부 실패가 앞서 성공한 리그까지 되돌린다. 단위마다 커밋해 부분 진행을 남긴다.
"""

import logging
import sqlite3
from collections.abc import Sequence
from contextlib import ExitStack
from dataclasses import dataclass, field

from app.db.connection import write_connection
from app.leagues import LEAGUES, League
from ingest import mappers, writers
from ingest.client import FootballDataClient
from ingest.collectors import COLLECTORS

logger = logging.getLogger(__name__)

DEFAULT_RESOURCES: tuple[str, ...] = ("standings", "matches")

SUCCESS = "success"
FAILURE = "failure"


@dataclass
class LeagueResult:
    competition_code: str
    resource: str
    status: str
    rows_written: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == SUCCESS


@dataclass
class BatchReport:
    results: list[LeagueResult] = field(default_factory=list)

    @property
    def failed(self) -> list[LeagueResult]:
        return [r for r in self.results if not r.ok]

    @property
    def rows_written(self) -> int:
        return sum(r.rows_written for r in self.results)

    @property
    def exit_code(self) -> int:
        """전부 실패했을 때만 0 이 아닌 코드를 낸다. 부분 실패는 cron 을 깨우지 않는다."""
        if not self.results:
            return 1
        return 1 if len(self.failed) == len(self.results) else 0


def validate_resources(resources: Sequence[str]) -> None:
    """호출을 한 건이라도 내보내기 전에 리소스 이름을 검증한다."""
    unknown = [r for r in resources if r not in COLLECTORS]
    if unknown:
        known = ", ".join(COLLECTORS)
        raise ValueError(f"알 수 없는 리소스: {', '.join(unknown)} (가능: {known})")
    if not resources:
        raise ValueError("수집할 리소스가 없다")


def collect_one(
    client: FootballDataClient,
    conn: sqlite3.Connection,
    league: League,
    resource: str,
) -> LeagueResult:
    """리그 하나 x 리소스 하나.

    예외를 잡아 실패 결과로 바꾸고 이력을 남긴다. 여기서 예외가 새어 나가면
    배치 전체가 죽으므로 Exception 을 통째로 잡는다. KeyboardInterrupt 는
    BaseException 이라 그대로 통과해 Ctrl+C 가 먹는다.
    """
    collect = COLLECTORS[resource]
    started_at = mappers.utc_now_iso()

    try:
        rows_written = collect(client, conn, league)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        result = LeagueResult(
            competition_code=league.code,
            resource=resource,
            status=FAILURE,
            error=f"{type(exc).__name__}: {exc}",
        )
        http_status = getattr(exc, "status_code", None)
        logger.warning("%s %s 실패: %s", league.code, resource, result.error)
    else:
        result = LeagueResult(
            competition_code=league.code,
            resource=resource,
            status=SUCCESS,
            rows_written=rows_written,
        )
        http_status = None
        logger.info("%s %s 성공: %d 행", league.code, resource, rows_written)

    # 이력은 성공/실패와 무관하게 남긴다. 위에서 롤백했더라도 이건 살아야 한다.
    writers.record_ingest_run(
        conn,
        competition_code=league.code,
        resource=resource,
        status=result.status,
        started_at=started_at,
        finished_at=mappers.utc_now_iso(),
        rows_written=result.rows_written if result.ok else None,
        http_status=http_status,
        error=result.error,
    )
    conn.commit()
    return result


def run_batch(
    *,
    resources: Sequence[str] = DEFAULT_RESOURCES,
    leagues: Sequence[League] = LEAGUES,
    client: FootballDataClient | None = None,
) -> BatchReport:
    """전체 배치.

    리그 바깥 루프 / 리소스 안쪽 루프로 순차 실행한다.
    호출 간격은 클라이언트의 RateLimiter 가 책임진다.

    ``client`` 를 넘기면 그걸 쓰고 닫지 않는다. 넘기지 않으면 설정으로 만들어 쓰고 닫는다.
    """
    validate_resources(resources)
    report = BatchReport()

    with ExitStack() as stack:
        if client is None:
            client = stack.enter_context(FootballDataClient.from_settings())
        conn = stack.enter_context(write_connection())

        for league in leagues:
            for resource in resources:
                report.results.append(collect_one(client, conn, league, resource))

    logger.info(
        "배치 종료: %d/%d 성공, %d 행",
        len(report.results) - len(report.failed),
        len(report.results),
        report.rows_written,
    )
    return report
