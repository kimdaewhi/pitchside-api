"""리소스별 수집기.

전부 같은 시그니처를 갖는다 — ``collect(client, conn, league) -> int``.
리그별 분기는 어디에도 없다. 새 리그는 레지스트리 항목 추가로 끝난다.
"""

from ingest.collectors import competitions, matches, standings

# run.py 가 --resource 인자로 골라 쓴다.
COLLECTORS = {
    "competitions": competitions.collect,
    "standings": standings.collect,
    "matches": matches.collect,
}

__all__ = ["COLLECTORS", "competitions", "matches", "standings"]
