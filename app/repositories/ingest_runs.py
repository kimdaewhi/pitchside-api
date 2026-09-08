"""수집 이력 조회.

헬스 엔드포인트가 읽는 유일한 테이블이다.
쓰기(이력 기록)는 ``ingest/writers.py`` 가 한다.
"""

import sqlite3


def last_success_per_league(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """리그·리소스별 마지막 성공 시각을 반환한다."""
    # TODO: 윈도우 함수로 (competition_code, resource) 그룹의 최신 성공 1건
    raise NotImplementedError


def last_run_per_league(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """성공/실패를 가리지 않은 마지막 실행. 실패가 이어지는 리그를 드러내는 데 쓴다."""
    raise NotImplementedError  # TODO: 윈도우 함수로 (competition_code, resource) 그룹의 최신 1건
