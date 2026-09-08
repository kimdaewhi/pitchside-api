"""수집 배치 엔트리포인트.

앱 내 스케줄러를 두지 않는다. 외부 cron 이 이 명령을 부른다.

    python -m ingest --resource standings,matches
    python -m ingest --resource competitions --league PL

종료 코드 — 0 전부 또는 일부 성공 / 1 전부 실패 / 2 인자 오류.
부분 실패로 cron 을 깨우지 않는 건 의도다. 한 리그가 죽어도 나머지는 최신이다.
"""

import argparse
import logging
import sys

from app.leagues import LEAGUES, get_league
from ingest.run import DEFAULT_RESOURCES, BatchReport, run_batch, validate_resources


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m ingest",
        description="football-data.org 에서 현재 시즌 데이터를 수집해 SQLite 에 저장한다.",
    )
    parser.add_argument(
        "--resource",
        default=",".join(DEFAULT_RESOURCES),
        help="쉼표로 구분. competitions,standings,matches (기본: standings,matches)",
    )
    parser.add_argument(
        "--league",
        default=None,
        help="쉼표로 구분한 리그 코드. 생략하면 레지스트리 전체를 돈다.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="요청 단위 로그까지 출력한다.",
    )
    return parser.parse_args(argv)


def _print_report(report: BatchReport) -> None:
    for result in report.results:
        detail = f"{result.rows_written:>5} 행" if result.ok else (result.error or "")
        print(f"{result.competition_code:>4}  {result.resource:<13} {result.status:<8} {detail}")
    succeeded = len(report.results) - len(report.failed)
    print(f"\n{succeeded}/{len(report.results)} 성공, {report.rows_written} 행")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    resources = [r.strip() for r in args.resource.split(",") if r.strip()]
    try:
        validate_resources(resources)
        leagues = (
            tuple(get_league(c.strip()) for c in args.league.split(",") if c.strip())
            if args.league
            else LEAGUES
        )
    except (ValueError, LookupError) as exc:
        print(f"인자 오류: {exc}", file=sys.stderr)
        return 2

    report = run_batch(resources=resources, leagues=leagues)
    _print_report(report)
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
