"""외부 응답(camelCase) → DB row(snake_case) 변환.

외부 스키마를 그대로 저장하지 않는다. 여기서 한 번 걸러낸다.
``odds`` 는 잠김 메시지만 오고 ``referees`` 는 저장하지 않으므로 둘 다 버린다.
"""

from typing import Any

# 집계에 쓰는 상태. 나머지는 폼·상대전적에서 제외한다.
FINISHED = "FINISHED"


def pick_standings_block(
    payload: dict[str, Any],
    *,
    stage: str = "REGULAR_SEASON",
    type_: str = "TOTAL",
    group: str | None = None,
) -> dict[str, Any] | None:
    """standings[] 에서 조건에 맞는 블록 하나를 골라낸다.

    5대 리그는 REGULAR_SEASON + TOTAL 단일 블록이지만
    첫 원소를 무조건 쓰지 않고 조건으로 찾는다.
    """
    raise NotImplementedError  # TODO: payload["standings"] 순회하며 stage/type/group 일치 블록 반환


def to_team_row(team: dict[str, Any]) -> dict[str, Any]:
    """standings 행과 matches 양쪽에 인라인으로 실리는 팀 스냅샷을 팀 마스터 row 로."""
    raise NotImplementedError  # TODO: id / name / shortName / tla / crest + updated_at


def to_competition_row(payload: dict[str, Any]) -> dict[str, Any]:
    raise NotImplementedError  # TODO: id / code / name / type / emblem / area.* / currentSeason.id


def to_season_row(season: dict[str, Any], competition_id: int) -> dict[str, Any]:
    # TODO: id / startDate / endDate / currentMatchday / winner.id (null 가능)
    raise NotImplementedError


def to_standing_rows(
    payload: dict[str, Any], block: dict[str, Any]
) -> list[dict[str, Any]]:
    raise NotImplementedError  # TODO: block["table"] 순회, form 은 버린다 (항상 null)


def to_match_row(match: dict[str, Any]) -> dict[str, Any]:
    """score.fullTime / halfTime / winner 는 경기 전이면 null 이다. 그대로 null 로 넘긴다."""
    raise NotImplementedError  # TODO: score 평탄화, group → group_name, odds/referees 폐기
