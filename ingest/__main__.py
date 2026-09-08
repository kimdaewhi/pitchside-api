"""수집 배치 엔트리포인트.

앱 내 스케줄러를 두지 않는다. 외부 cron 이 이 명령을 부른다.

    python -m ingest --resource standings,matches
    python -m ingest --resource competitions --league PL
"""

import argparse
import sys

from app.leagues import LEAGUES, get_league
from ingest.run import DEFAULT_RESOURCES, run_batch


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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    resources = [r.strip() for r in args.resource.split(",") if r.strip()]
    leagues = (
        tuple(get_league(c.strip()) for c in args.league.split(",") if c.strip())
        if args.league
        else LEAGUES
    )
    report = run_batch(resources=resources, leagues=leagues)
    for result in report.results:
        print(f"{result.competition_code:>4} {result.resource:<13} {result.status}")
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
