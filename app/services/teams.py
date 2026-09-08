"""팀 서비스."""

import sqlite3

from app.leagues import League
from app.schemas.teams import TeamDetail, TeamsResponse


def list_teams(conn: sqlite3.Connection, league: League) -> TeamsResponse:
    raise NotImplementedError  # TODO: 현재 시즌 순위표에 등장하는 팀 목록


def get_team(conn: sqlite3.Connection, team_id: int) -> TeamDetail:
    raise NotImplementedError  # TODO: teams 조회 + (선택) 폼 가이드 첨부
