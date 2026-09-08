"""SQL 계층.

여기에만 SQL 을 둔다. HTTP 도, 외부 호출도 없다.
조회 전용이다 — 쓰기(upsert)는 수집 배치의 ``ingest/writers.py`` 가 담당한다.
"""
