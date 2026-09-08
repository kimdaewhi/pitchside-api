"""스키마 초기화.

``python -m app.db.init_db`` 로 단독 실행한다. 앱 기동 시 자동으로 돌리지 않는다.
"""

import sqlite3
from pathlib import Path

from app.config import get_settings
from app.db.connection import write_connection

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def apply_schema(conn: sqlite3.Connection) -> None:
    """schema.sql 을 통째로 적용한다. 멱등하다."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def init_db() -> Path:
    """DB 파일을 만들고 스키마를 적용한 뒤 경로를 반환한다."""
    settings = get_settings()
    with write_connection() as conn:
        apply_schema(conn)
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    if journal_mode.lower() != "wal":
        raise RuntimeError(f"WAL 모드 설정 실패: journal_mode={journal_mode}")
    return settings.database_path


def main() -> None:
    path = init_db()
    print(f"schema applied: {path} (journal_mode=wal)")


if __name__ == "__main__":
    main()
