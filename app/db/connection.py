"""SQLite 커넥션 수명주기.

배치 쓰기와 API 읽기가 동시에 일어나므로 WAL 이 필수다.
읽기/쓰기 커넥션을 분리해 "요청 경로에서 쓰기 금지"를 구조로 못 박는다.

커넥션은 연 스레드 안에서만 쓰고 그 스레드에서 닫는다. FastAPI 의존성으로
주입하지 않는 이유는 :func:`read_connection` 아래 주석에 적어 두었다.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.config import get_settings


def _connect(db_path: Path) -> sqlite3.Connection:
    """커넥션 하나를 연다.

    ``check_same_thread`` 는 기본값(True)을 유지한다. 커넥션을 스레드 사이로
    넘기지 않고 요청마다 새로 여는 것이 이 설계의 전제다. 이 가드를 끄면
    스레드를 넘나드는 사용이 에러 대신 조용한 데이터 경합으로 바뀐다.
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
    """API 요청용 읽기 전용 커넥션. 커밋하지 않는다.

    반드시 핸들러 본문 안에서 열고 닫는다. FastAPI 의존성(``Depends``)으로
    주입하면 안 된다 — 동기 제너레이터 의존성의 진입/본문/정리를 FastAPI 가
    각각 별도의 ``anyio.to_thread.run_sync`` 로 돌리기 때문에, 동시 요청이
    몰리면 커넥션을 연 스레드와 쓰는 스레드가 갈린다. 반대로 동기 핸들러
    본문은 통째로 한 워커 스레드에서 실행되므로 열기·조회·닫기가 한 스레드에
    묶인다.
    """
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
