"""대회 목록 서비스."""

import sqlite3

from app.leagues import LEAGUES
from app.repositories import competitions as competitions_repo
from app.schemas.common import CompetitionBrief
from app.services.common import to_competition_brief


def list_competitions(conn: sqlite3.Connection) -> list[CompetitionBrief]:
    """대상 리그 목록.

    레지스트리 순서를 따르고, 레지스트리에 없는 대회가 DB 에 남아 있어도 노출하지 않는다.
    아직 수집되지 않은 리그는 목록에서 빠진다 — 빈 껍데기를 지어내지 않는다.
    """
    stored = {row["code"]: row for row in competitions_repo.list_competitions(conn)}
    return [
        to_competition_brief(stored[league.code]) for league in LEAGUES if league.code in stored
    ]
