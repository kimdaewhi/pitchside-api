"""순위표 조회."""

import sqlite3


def get_standings(
    conn: sqlite3.Connection,
    competition_id: int,
    season_id: int,
    *,
    stage: str = "REGULAR_SEASON",
    type_: str = "TOTAL",
) -> list[sqlite3.Row]:
    """(stage, type) 블록의 순위표를 position 순으로 반환한다.

    standings 는 (stage, type, group) 조합으로 여러 블록이 저장될 수 있으므로
    첫 블록을 무조건 집지 말고 조건으로 골라낸다.
    """
    raise NotImplementedError  # TODO: standings JOIN teams, WHERE 4개 조건, ORDER BY position
