"""응답 → 행 변환.

samples/ 의 실제 응답을 그대로 먹여 검증한다.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from ingest import mappers

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def load(name: str) -> dict[str, Any]:
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


@pytest.fixture
def standings() -> dict[str, Any]:
    return load("standings.json")


@pytest.fixture
def matches() -> dict[str, Any]:
    return load("matches.json")


@pytest.fixture
def competition() -> dict[str, Any]:
    return load("competitions.json")


# --- standings ---


def test_pick_block_matches_on_stage_and_type(standings: dict[str, Any]) -> None:
    block = mappers.pick_standings_block(standings)
    assert block is not None
    assert (block["stage"], block["type"]) == ("REGULAR_SEASON", "TOTAL")


def test_pick_block_returns_none_when_type_absent(standings: dict[str, Any]) -> None:
    """첫 원소를 무조건 집지 않는다는 확인."""
    assert mappers.pick_standings_block(standings, type_="HOME") is None


def test_standing_rows_drop_form(standings: dict[str, Any]) -> None:
    block = mappers.pick_standings_block(standings)
    rows = mappers.to_standing_rows(standings, block)
    assert rows
    assert all("form" not in row for row in rows)


def test_standing_rows_carry_keys_and_group(standings: dict[str, Any]) -> None:
    block = mappers.pick_standings_block(standings)
    row = mappers.to_standing_rows(standings, block)[0]
    assert row["competition_id"] == 2021
    assert row["season_id"] == 2502
    assert row["group_name"] == "Matchday"  # null 이 아니라 문자열로 온다
    assert row["position"] == 1
    assert row["team_id"] == 65
    assert row["points"] == 9
    assert row["goal_difference"] == 5


def test_group_falls_back_to_empty_string() -> None:
    """group 은 PK 의 일부라 null 이면 안 된다."""
    payload = {"competition": {"id": 1}, "season": {"id": 2}}
    block = {"stage": "REGULAR_SEASON", "type": "TOTAL", "group": None, "table": []}
    assert mappers.to_standing_rows(payload, block) == []
    block["table"] = [
        {
            "position": 1,
            "team": {"id": 9, "name": "T"},
            "playedGames": 0,
            "won": 0,
            "draw": 0,
            "lost": 0,
            "points": 0,
            "goalsFor": 0,
            "goalsAgainst": 0,
            "goalDifference": 0,
        }
    ]
    assert mappers.to_standing_rows(payload, block)[0]["group_name"] == ""


# --- matches ---


def test_match_row_flattens_score(matches: dict[str, Any]) -> None:
    row = mappers.to_match_row(matches["matches"][0])
    assert row["id"] == 560542
    assert row["status"] == "FINISHED"
    assert row["utc_date"] == "2026-08-21T19:00:00Z"
    assert (row["home_team_id"], row["away_team_id"]) == (57, 1076)
    assert row["winner"] == "HOME_TEAM"
    assert (row["full_time_home"], row["full_time_away"]) == (3, 0)
    assert (row["half_time_home"], row["half_time_away"]) == (2, 0)


def test_match_row_keeps_pre_kickoff_nulls() -> None:
    """경기 전에는 점수가 전부 null 로 온다. null 그대로 넘긴다."""
    match = {
        "id": 1,
        "competition": {"id": 2021},
        "season": {"id": 2502},
        "utcDate": "2027-01-01T15:00:00Z",
        "status": "SCHEDULED",
        "matchday": 20,
        "stage": "REGULAR_SEASON",
        "group": None,
        "homeTeam": {"id": 57},
        "awayTeam": {"id": 65},
        "score": {"winner": None, "duration": "REGULAR", "fullTime": {}, "halfTime": {}},
    }
    row = mappers.to_match_row(match)
    assert row["winner"] is None
    assert row["full_time_home"] is None
    assert row["half_time_away"] is None
    assert row["group_name"] is None


def test_match_row_survives_missing_score_key() -> None:
    match = {
        "id": 2,
        "competition": {"id": 2021},
        "season": {"id": 2502},
        "utcDate": "2027-01-01T15:00:00Z",
        "status": "POSTPONED",
        "homeTeam": {"id": 57},
        "awayTeam": {"id": 65},
    }
    row = mappers.to_match_row(match)
    assert row["full_time_home"] is None
    assert row["duration"] is None


def test_match_rows_discard_odds_and_referees(matches: dict[str, Any]) -> None:
    row = mappers.to_match_row(matches["matches"][0])
    assert "odds" not in row
    assert "referees" not in row


# --- teams ---


def test_team_rows_from_matches_are_deduped(matches: dict[str, Any]) -> None:
    rows = mappers.to_team_rows_from_matches(matches)
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids))
    assert set(ids) == {57, 1076, 322, 66}


def test_team_rows_from_standings(standings: dict[str, Any]) -> None:
    block = mappers.pick_standings_block(standings)
    rows = mappers.to_team_rows_from_standings(block)
    first = next(row for row in rows if row["id"] == 65)
    assert first["name"] == "Manchester City FC"
    assert first["short_name"] == "Man City"
    assert first["tla"] == "MCI"
    assert first["updated_at"].endswith("Z")


# --- competitions / seasons ---


def test_competition_row_from_full_payload(competition: dict[str, Any]) -> None:
    row = mappers.to_competition_row(competition)
    assert row["id"] == 2021
    assert row["code"] == "PL"
    assert row["area_name"] == "England"
    assert row["current_season_id"] == 2502


def test_competition_row_from_inline_slim_object(standings: dict[str, Any]) -> None:
    """standings·matches 에 실리는 competition 에는 area 도 currentSeason 도 없다."""
    row = mappers.to_competition_row(
        standings["competition"], current_season_id=standings["season"]["id"]
    )
    assert row["area_name"] is None
    assert row["current_season_id"] == 2502


def test_season_row_winner_is_nullable(competition: dict[str, Any]) -> None:
    row = mappers.to_season_row(competition["currentSeason"], competition["id"])
    assert row["id"] == 2502
    assert row["competition_id"] == 2021
    assert row["start_date"] == "2026-08-21"
    assert row["current_matchday"] == 3
    assert row["winner_team_id"] is None
