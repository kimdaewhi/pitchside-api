"""서비스 계층 공통 조각.

행 → 스키마 변환과, 네 서비스가 똑같이 반복하는 "현재 시즌 찾기"를 모아둔다.
여기서도 HTTP 는 모른다. 아래 예외들을 상태 코드로 옮기는 건 ``app/main.py`` 의 일이다.
"""

import sqlite3

from app.leagues import League
from app.repositories import competitions as competitions_repo
from app.schemas.common import CompetitionBrief, SeasonBrief, TeamBrief
from app.schemas.matches import MatchScore, MatchSummary


class NotIngestedError(LookupError):
    """레지스트리에는 있으나 아직 수집되지 않은 대상.

    "코드가 틀렸다"와 "아직 안 받아왔다"는 다른 상황이라 구분해서 올린다.
    요청 경로에서 외부를 호출해 메우지 않는다.
    """


class InvalidFilterError(ValueError):
    """받아들일 수 없는 쿼리 파라미터."""


def resolve_current_season(
    conn: sqlite3.Connection, league: League
) -> tuple[sqlite3.Row, sqlite3.Row]:
    """리그의 대회 행과 현재 시즌 행을 함께 가져온다."""
    competition = competitions_repo.get_competition_by_code(conn, league.code)
    if competition is None:
        raise NotIngestedError(f"{league.code}: 아직 수집되지 않았습니다")
    season = competitions_repo.get_current_season(conn, competition["id"])
    if season is None:
        raise NotIngestedError(f"{league.code}: 현재 시즌 정보가 아직 없습니다")
    return competition, season


def to_competition_brief(row: sqlite3.Row) -> CompetitionBrief:
    return CompetitionBrief(
        id=row["id"], code=row["code"], name=row["name"], emblem=row["emblem"]
    )


def to_season_brief(row: sqlite3.Row) -> SeasonBrief:
    return SeasonBrief(
        id=row["id"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        current_matchday=row["current_matchday"],
    )


def to_team_brief(row: sqlite3.Row, prefix: str = "") -> TeamBrief:
    """팀 컬럼을 TeamBrief 로.

    한 행에 홈·원정 팀이 함께 실려 오므로 ``home_`` / ``away_`` 접두사로 골라낸다.
    """
    return TeamBrief(
        id=row[f"{prefix}id"],
        name=row[f"{prefix}name"],
        short_name=row[f"{prefix}short_name"],
        tla=row[f"{prefix}tla"],
        crest=row[f"{prefix}crest"],
    )


def to_match_summary(row: sqlite3.Row) -> MatchSummary:
    return MatchSummary(
        id=row["id"],
        utc_date=row["utc_date"],
        status=row["status"],
        matchday=row["matchday"],
        stage=row["stage"],
        group=row["group_name"],
        home_team=to_team_brief(row, "home_"),
        away_team=to_team_brief(row, "away_"),
        score=MatchScore(
            winner=row["winner"],
            full_time_home=row["full_time_home"],
            full_time_away=row["full_time_away"],
            half_time_home=row["half_time_home"],
            half_time_away=row["half_time_away"],
        ),
    )
