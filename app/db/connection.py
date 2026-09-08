"""SQLite 커넥션 수명주기.

배치 쓰기와 API 읽기가 동시에 일어나므로 WAL 이 필수다.
읽기/쓰기 커넥션을 분리해 "요청 경로에서 쓰기 금지"를 구조로 못 박는다.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.config import get_settings


def _connect(db_path: Path) -> sqlite3.Connection:
    """커넥션 하나를 연다.

    ``check_same_thread`` 는 기본값(True)을 유지한다. 커넥션을 스레드 사이로
    넘기지 않고 요청마다 새로 여는 것이 이 설계의 전제다.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=get_settings().sqlite_busy_timeout_ms / 1000)
    conn.row_factory = sqlite3.Row
    return conn


def _apply_common_pragmas(conn: sqlite3.Connection) -> None:
    """읽기·쓰기 공통 PRAGMA."""
    settings = get_settings()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {settings.sqlite_busy_timeout_ms}")


def apply_writer_pragmas(conn: sqlite3.Connection) -> None:
    """쓰기 커넥션 PRAGMA.

    journal_mode 는 DB 파일에 한 번 새겨지면 유지되는 영속 속성이지만,
    매번 멱등하게 설정해 "누가 먼저 열었는가"에 의존하지 않게 한다.
    """
    _apply_common_pragmas(conn)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")


def apply_reader_pragmas(conn: sqlite3.Connection) -> None:
    """읽기 커넥션 PRAGMA.

    ``query_only`` 를 켜서 요청 경로에서 실수로 쓰기가 나가면 즉시 에러가 나게 한다.
    journal_mode 는 건드리지 않는다 — query_only 상태에서는 바꿀 수도 없고,
    WAL 설정은 init_db 와 쓰기 커넥션의 책임이다.
    """
    _apply_common_pragmas(conn)
    conn.execute("PRAGMA query_only = ON")


@contextmanager
def read_connection() -> Iterator[sqlite3.Connection]:
    """API 요청용 읽기 전용 커넥션. 커밋하지 않는다."""
    conn = _connect(get_settings().database_path)
    try:
        apply_reader_pragmas(conn)
        yield conn
    finally:
        conn.close()


@contextmanager
def write_connection() -> Iterator[sqlite3.Connection]:
    """배치 전용 쓰기 커넥션.

    쓰기는 수집 배치 프로세스 하나로 직렬화한다. FastAPI 쪽에서는 쓰지 않는다.
    정상 종료 시 커밋, 예외 시 롤백.
    """
    conn = _connect(get_settings().database_path)
    try:
        apply_writer_pragmas(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI 의존성. 요청 하나당 읽기 커넥션 하나."""
    with read_connection() as conn:
        yield conn
