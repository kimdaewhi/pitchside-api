"""경기 상세 조립.

새로 계산하는 값은 없다. 다른 엔드포인트가 이미 쓰는 조회들을 한 커넥션 안에서
불러 모으는 것이 전부다. 조인 하나로 합치지 않는 이유는 각 조각이 다른 곳에서도
쓰이기 때문이다 — 합치는 순간 그 재사용이 끊긴다.

**기준 시점** — form 과 상대전적은 그 경기의 ``utc_date`` 이전만 본다.
예정 경기면 "지금까지"와 같고, 끝난 경기면 "그 경기에 들어갈 때"가 된다.
순위만은 예외다. 순위표는 덮어써서 과거 시점을 복원할 수 없어 현재 값이 나간다.
"""

import sqlite3

from app.repositories import competitions as competitions_repo
from app.repositories import matches as matches_repo
from app.repositories import standings as standings_repo
from app.schemas.head_to_head import HeadToHeadSummary
from app.schemas.match_detail import MatchDetail, TeamMatchContext, TeamStanding
from app.services import form as form_service
from app.services.common import (
    NotIngestedError,
    to_competition_brief,
    to_match_summary,
    to_season_brief,
    to_team_brief,
)
from app.services.standings import DEFAULT_STAGE, DEFAULT_TYPE

RECENT_MEETINGS_LIMIT = 10


def _to_team_standing(row: sqlite3.Row | None) -> TeamStanding | None:
    if row is None:
        return None
    return TeamStanding(
        position=row["position"],
        played_games=row["played_games"],
        won=row["won"],
        draw=row["draw"],
        lost=row["lost"],
        points=row["points"],
        goals_for=row["goals_for"],
        goals_against=row["goals_against"],
        goal_difference=row["goal_difference"],
    )


def _team_context(
    conn: sqlite3.Connection,
    match: sqlite3.Row,
    prefix: str,
    standings_by_team: dict[int, sqlite3.Row],
) -> TeamMatchContext:
    """홈 또는 원정 한쪽의 맥락.

    팀 브리프는 경기 행에 이미 실려 있으므로 다시 조회하지 않는다.
    """
    team = to_team_brief(match, prefix)
    return TeamMatchContext(
        team=team,
        standing=_to_team_standing(standings_by_team.get(team.id)),
        form=form_service.recent_results(
            conn,
            team.id,
            match["competition_id"],
            match["season_id"],
            before_utc_date=match["utc_date"],
        ),
    )


def get_match_detail(conn: sqlite3.Connection, match_id: int) -> MatchDetail:
    """경기 하나와 그 맥락.

    match id 에는 리그 같은 레지스트리가 없어서 "틀린 id"와 "아직 수집 안 됨"을
    구분할 수 없다. ``/teams/{id}`` 와 마찬가지로 404 는 한 종류다.
    """
    match = matches_repo.get_match(conn, match_id)
    if match is None:
        raise NotIngestedError(f"match {match_id}: 저장된 경기가 아닙니다")

    # 대회의 현재 시즌이 아니라 이 경기가 속한 시즌을 읽는다.
    competition = competitions_repo.get_competition_by_id(conn, match["competition_id"])
    season = competitions_repo.get_season(conn, match["season_id"])
    if competition is None or season is None:
        # FK 가 켜져 있어 정상 경로에서는 도달하지 않는다. 도달했다면 DB 가 깨진 것이다.
        raise NotIngestedError(f"match {match_id}: 대회·시즌 정보가 아직 없습니다")

    # 순위표는 한 번만 읽고 두 팀을 꺼낸다. 20행짜리 표라 전용 SQL 을 만들 이유가 없다.
    standings_by_team = {
        row["team_id"]: row
        for row in standings_repo.get_standings(
            conn,
            match["competition_id"],
            match["season_id"],
            stage=DEFAULT_STAGE,
            type_=DEFAULT_TYPE,
        )
    }

    home_id = match["home_id"]
    away_id = match["away_id"]
    before = match["utc_date"]

    # 리그 필터를 걸지 않는다. 기존 /teams/{id}/vs/{id} 의 기본값과 같은 전 대회다.
    totals = matches_repo.head_to_head_summary(
        conn, home_id, away_id, before_utc_date=before
    )
    meetings = matches_repo.list_head_to_head(
        conn, home_id, away_id, limit=RECENT_MEETINGS_LIMIT, before_utc_date=before
    )

    same_matchday: list[sqlite3.Row] = []
    if match["matchday"] is not None:
        same_matchday = [
            row
            for row in matches_repo.list_matches(
                conn,
                match["competition_id"],
                match["season_id"],
                matchday=match["matchday"],
            )
            if row["id"] != match_id
        ]

    home = _team_context(conn, match, "home_", standings_by_team)
    away = _team_context(conn, match, "away_", standings_by_team)

    return MatchDetail(
        match=to_match_summary(match),
        competition=to_competition_brief(competition),
        season=to_season_brief(season),
        home=home,
        away=away,
        head_to_head=HeadToHeadSummary(
            team=home.team,
            opponent=away.team,
            played=totals["played"],
            won=totals["won"],
            draw=totals["draw"],
            lost=totals["lost"],
            goals_for=totals["goals_for"],
            goals_against=totals["goals_against"],
        ),
        recent_meetings=[to_match_summary(row) for row in meetings],
        same_matchday=[to_match_summary(row) for row in same_matchday],
    )
