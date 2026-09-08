"""쓰기 전용 SQL.

쓰기는 전부 upsert 다. 삭제하지 않는다. 몇 번을 돌려도 결과가 같아야 한다.
조회 SQL 은 여기가 아니라 ``app/repositories/`` 에 있다.
"""

import sqlite3
from typing import Any


def upsert_teams(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    raise NotImplementedError  # TODO: INSERT ... ON CONFLICT(id) DO UPDATE


def upsert_competition(conn: sqlite3.Connection, row: dict[str, Any]) -> int:
    raise NotImplementedError  # TODO: INSERT ... ON CONFLICT(id) DO UPDATE


def upsert_seasons(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    raise NotImplementedError  # TODO: INSERT ... ON CONFLICT(id) DO UPDATE


def upsert_standings(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    """복합 PK (competition_id, season_id, stage, type, group_name, team_id) 기준 upsert."""
    raise NotImplementedError  # TODO: INSERT ... ON CONFLICT(복합 PK) DO UPDATE


def upsert_matches(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    raise NotImplementedError  # TODO: INSERT ... ON CONFLICT(id) DO UPDATE


def record_ingest_run(
    conn: sqlite3.Connection,
    *,
    competition_code: str,
    resource: str,
    status: str,
    started_at: str,
    finished_at: str,
    rows_written: int | None = None,
    http_status: int | None = None,
    error: str | None = None,
) -> None:
    """수집 이력 한 줄. 성공이든 실패든 남긴다."""
    raise NotImplementedError  # TODO: INSERT INTO ingest_runs
