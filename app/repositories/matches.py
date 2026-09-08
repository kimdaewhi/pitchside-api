"""경기 조회.

폼 가이드와 상대전적은 홈/원정이 뒤집히므로 단방향 조회로는 절반을 놓친다.
아래 함수들은 전부 양방향(home_team_id OR away_team_id)으로 조회한다.
"""

import sqlite3

FINISHED = "FINISHED"


def list_matches(
    conn: sqlite3.Connection,
    competition_id: int,
    season_id: int,
    *,
    matchday: int | None = None,
    status: str | None = None,
) -> list[sqlite3.Row]:
    """해당 시즌의 경기를 utc_date 순으로 반환한다."""
    raise NotImplementedError  # TODO: matches JOIN teams x2, 선택 필터, ORDER BY utc_date


def list_recent_finished_for_team(
    conn: sqlite3.Connection,
    team_id: int,
    competition_id: int,
    season_id: int,
    *,
    limit: int = 5,
) -> list[sqlite3.Row]:
    """폼 가이드용. 해당 팀의 그 시즌·리그 FINISHED 경기를 최신순으로 최대 limit 개.

    홈/원정을 모두 포함한다. limit 에 못 미치면 있는 만큼만 반환하고 패딩하지 않는다.
    """
    # TODO: WHERE status='FINISHED' AND (home=? OR away=?) ORDER BY utc_date DESC LIMIT ?
    raise NotImplementedError


def list_head_to_head(
    conn: sqlite3.Connection,
    team_id: int,
    opponent_id: int,
    *,
    competition_id: int | None = None,
) -> list[sqlite3.Row]:
    """두 팀의 FINISHED 경기 전체를 최신순으로 반환한다.

    competition_id 는 선택 인자다. None 이면 전 대회를 대상으로 한다.
    """
    # TODO: (home=a AND away=b) OR (home=b AND away=a), 선택적 competition 필터
    raise NotImplementedError
