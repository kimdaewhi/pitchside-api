"""수집 이력 조회.

헬스 엔드포인트가 읽는 유일한 테이블이다.
쓰기(이력 기록)는 ``ingest/writers.py`` 가 한다.
"""

import sqlite3

# (리그, 리소스) 그룹마다 최신 1건. 윈도우 함수로 한 번에 끝낸다.
_LATEST_PER_GROUP = """
SELECT competition_code, resource, status, started_at, finished_at,
       rows_written, http_status, error
FROM (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY competition_code, resource
               ORDER BY finished_at DESC, id DESC
           ) AS rn
    FROM ingest_runs
    {where}
)
WHERE rn = 1
ORDER BY competition_code, resource
"""


def last_success_per_league(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """리그·리소스별 마지막 성공 시각을 반환한다."""
    return conn.execute(_LATEST_PER_GROUP.format(where="WHERE status = 'success'")).fetchall()


def last_run_per_league(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """성공/실패를 가리지 않은 마지막 실행. 실패가 이어지는 리그를 드러내는 데 쓴다."""
    return conn.execute(_LATEST_PER_GROUP.format(where="")).fetchall()
