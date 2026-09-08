"""상대전적 계산."""

import sqlite3

from app.schemas.head_to_head import HeadToHeadResponse

RECENT_LIMIT = 10


def get_head_to_head(
    conn: sqlite3.Connection,
    team_id: int,
    opponent_id: int,
    *,
    competition_code: str | None = None,
    recent_limit: int = RECENT_LIMIT,
) -> HeadToHeadResponse:
    """두 팀의 FINISHED 경기를 집계한다.

    홈/원정이 뒤집히므로 반드시 양방향으로 조회한다.
    competition_code 는 선택 필터이고, 기본은 전 대회다.
    """
    # TODO: repositories.matches.list_head_to_head → team 관점 승/무/패·득실 집계
    raise NotImplementedError
