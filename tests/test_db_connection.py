"""SQLite 연결 규약 검증."""

import sqlite3
from pathlib import Path

import pytest

from app.db.connection import read_connection, write_connection


def test_wal_mode_enabled(temp_db: Path) -> None:
    with write_connection() as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_pragmas_applied(temp_db: Path) -> None:
    with read_connection() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] > 0


def test_read_connection_rejects_writes(temp_db: Path) -> None:
    """요청 경로에서 쓰기가 나가면 구조적으로 막힌다."""
    with read_connection() as conn, pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO teams (id, name, updated_at) VALUES (1, 'x', 'x')")


def test_schema_tables_exist(temp_db: Path) -> None:
    expected = {"teams", "competitions", "seasons", "standings", "matches", "ingest_runs"}
    with read_connection() as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    assert expected <= {row["name"] for row in rows}
