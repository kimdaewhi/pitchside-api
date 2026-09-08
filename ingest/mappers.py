"""외부 응답(camelCase) → DB row(snake_case) 변환.

외부 스키마를 그대로 저장하지 않는다. 여기서 한 번 걸러낸다.
``odds`` 는 잠김 메시지만 오고 ``referees`` 는 저장하지 않으므로 둘 다 버린다.
``form`` 도 버린다 — 항상 null 이라 쓸 수 없고, 폼 가이드는 matches 에서 계산한다.

여기서는 DB 를 건드리지 않는다. 순수 변환만 한다.
"""

from datetime import UTC, datetime
from typing import Any

# 집계에 쓰는 상태. 나머지는 폼·상대전적에서 제외한다.
FINISHED = "FINISHED"


def utc_now_iso() -> str:
    """팀 마스터 갱신 시각. DB 에는 UTC 그대로 넣는다."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def pick_standings_block(
    payload: dict[str, Any],
    *,
    stage: str = "REGULAR_SEASON",
    type_: str = "TOTAL",
    group: str | None = None,
) -> dict[str, Any] | None:
    """standings[] 에서 조건에 맞는 블록 하나를 골라낸다.

    5대 리그는 REGULAR_SEASON + TOTAL 단일 블록이지만
    첫 원소를 무조건 쓰지 않고 조건으로 찾는다. ``group`` 이 None 이면 group 은 보지 않는다
    (실제 응답의 group 은 "Matchday" 처럼 리그마다 다른 문자열이 온다).
    """
    for block in payload.get("standings") or []:
        if block.get("stage") != stage or block.get("type") != type_:
            continue
        if group is not None and block.get("group") != group:
            continue
        return block
    return None


def to_team_row(team: dict[str, Any], *, updated_at: str | None = None) -> dict[str, Any]:
    """standings 행과 matches 양쪽에 인라인으로 실리는 팀 스냅샷을 팀 마스터 row 로."""
    return {
        "id": team["id"],
        "name": team["name"],
        "short_name": team.get("shortName"),
        "tla": team.get("tla"),
        "crest": team.get("crest"),
        "updated_at": updated_at or utc_now_iso(),
    }


def _dedupe_teams(teams: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """같은 팀이 여러 번 실려 오므로 id 기준으로 마지막 것만 남긴다."""
    by_id: dict[int, dict[str, Any]] = {}
    for team in teams:
        if team.get("id") is not None:
            by_id[team["id"]] = team
    return list(by_id.values())


def to_team_rows_from_standings(block: dict[str, Any]) -> list[dict[str, Any]]:
    """순위표 블록에 실린 팀 스냅샷들."""
    updated_at = utc_now_iso()
    teams = _dedupe_teams([row["team"] for row in block.get("table") or []])
    return [to_team_row(team, updated_at=updated_at) for team in teams]


def to_team_rows_from_matches(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """경기 목록에 실린 홈·원정 팀 스냅샷들. 팀 하나가 여러 경기에 나오므로 중복을 제거한다."""
    updated_at = utc_now_iso()
    teams: list[dict[str, Any]] = []
    for match in payload.get("matches") or []:
        for side in ("homeTeam", "awayTeam"):
            team = match.get(side)
            if team:
                teams.append(team)
    return [to_team_row(team, updated_at=updated_at) for team in _dedupe_teams(teams)]


def to_competition_row(
    competition: dict[str, Any], *, current_season_id: int | None = None
) -> dict[str, Any]:
    """대회 row.

    /competitions/{id} 의 최상위 객체와, standings·matches 에 인라인으로 실리는
    슬림한 competition 객체를 모두 받는다. 슬림 쪽에는 area 와 currentSeason 이 없어
    해당 컬럼이 None 이 되는데, upsert 가 COALESCE 로 기존 값을 지키므로 덮어쓰지 않는다.
    """
    area = competition.get("area") or {}
    season = competition.get("currentSeason") or {}
    return {
        "id": competition["id"],
        "code": competition["code"],
        "name": competition["name"],
        "type": competition.get("type"),
        "emblem": competition.get("emblem"),
        "area_id": area.get("id"),
        "area_name": area.get("name"),
        "area_code": area.get("code"),
        "area_flag": area.get("flag"),
        "current_season_id": (
            current_season_id if current_season_id is not None else season.get("id")
        ),
        "last_updated": competition.get("lastUpdated"),
    }


def to_season_row(season: dict[str, Any], competition_id: int) -> dict[str, Any]:
    """시즌 row.

    현재 시즌에만 쓴다. 과거 시즌은 백필하지 않는다 — seasons.winner_team_id 가
    teams 를 참조하는데, 과거 우승팀이 팀 마스터에 없으면 FK 가 깨진다.
    """
    winner = season.get("winner") or {}
    return {
        "id": season["id"],
        "competition_id": competition_id,
        "start_date": season.get("startDate"),
        "end_date": season.get("endDate"),
        "current_matchday": season.get("currentMatchday"),
        "winner_team_id": winner.get("id"),
    }


def to_standing_rows(payload: dict[str, Any], block: dict[str, Any]) -> list[dict[str, Any]]:
    """순위표 블록을 행 목록으로. form 은 버린다."""
    competition_id = payload["competition"]["id"]
    season_id = payload["season"]["id"]
    stage = block["stage"]
    type_ = block["type"]
    # group 은 PK 의 일부라 null 을 허용하지 않는다. 없으면 빈 문자열로 둔다.
    group_name = block.get("group") or ""

    rows = []
    for row in block.get("table") or []:
        rows.append(
            {
                "competition_id": competition_id,
                "season_id": season_id,
                "stage": stage,
                "type": type_,
                "group_name": group_name,
                "team_id": row["team"]["id"],
                "position": row["position"],
                "played_games": row["playedGames"],
                "won": row["won"],
                "draw": row["draw"],
                "lost": row["lost"],
                "points": row["points"],
                "goals_for": row["goalsFor"],
                "goals_against": row["goalsAgainst"],
                "goal_difference": row["goalDifference"],
            }
        )
    return rows


def to_match_row(match: dict[str, Any]) -> dict[str, Any]:
    """경기 row.

    score.fullTime / halfTime / winner 는 경기 전이면 null 이다. 그대로 null 로 넘긴다.
    competition 과 season 은 경기마다 인라인으로 실려 오므로 따로 받지 않는다.
    """
    score = match.get("score") or {}
    full_time = score.get("fullTime") or {}
    half_time = score.get("halfTime") or {}
    return {
        "id": match["id"],
        "competition_id": match["competition"]["id"],
        "season_id": match["season"]["id"],
        "utc_date": match["utcDate"],
        "status": match["status"],
        "matchday": match.get("matchday"),
        "stage": match.get("stage"),
        "group_name": match.get("group"),
        "home_team_id": match["homeTeam"]["id"],
        "away_team_id": match["awayTeam"]["id"],
        "winner": score.get("winner"),
        "duration": score.get("duration"),
        "full_time_home": full_time.get("home"),
        "full_time_away": full_time.get("away"),
        "half_time_home": half_time.get("home"),
        "half_time_away": half_time.get("away"),
        "last_updated": match.get("lastUpdated"),
    }


def to_match_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [to_match_row(match) for match in payload.get("matches") or []]
