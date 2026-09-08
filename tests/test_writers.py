"""upsert 저장.

samples/ 응답을 매퍼에 통과시켜 실제 임시 DB 에 쓰고 되읽는다.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from app.db.connection import read_connection, write_connection
from ingest import mappers, writers

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def load(name: str) -> dict[str, Any]:
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


def standing_row(team_id: int) -> dict[str, Any]:
    """순위표 한 줄짜리 최소 페이로드 조각."""
    return {
        "position": 1,
        "team": {"id": team_id, "name": f"team-{team_id}"},
        "playedGames": 0,
        "won": 0,
        "draw": 0,
        "lost": 0,
        "points": 0,
        "goalsFor": 0,
        "goalsAgainst": 0,
        "goalDifference": 0,
    }


def seed_competition_and_season(conn: sqlite3.Connection) -> None:
    """FK 를 만족시키기 위한 최소 선행 쓰기."""
    payload = load("competitions.json")
    writers.upsert_competition(conn, mappers.to_competition_row(payload))
    writers.upsert_seasons(conn, [mappers.to_season_row(payload["currentSeason"], payload["id"])])


def ingest_standings(conn: sqlite3.Connection) -> int:
    payload = load("standings.json")
    block = mappers.pick_standings_block(payload)
    writers.upsert_teams(conn, mappers.to_team_rows_from_standings(block))
    return writers.upsert_standings(conn, mappers.to_standing_rows(payload, block))


def ingest_matches(conn: sqlite3.Connection) -> int:
    payload = load("matches.json")
    writers.upsert_teams(conn, mappers.to_team_rows_from_matches(payload))
    return writers.upsert_matches(conn, mappers.to_match_rows(payload))


# --- 저장 ---


def test_standings_round_trip(temp_db: Path) -> None:
    with write_connection() as conn:
        seed_competition_and_season(conn)
        assert ingest_standings(conn) == 3

    with read_connection() as conn:
        rows = conn.execute("SELECT * FROM standings ORDER BY position").fetchall()
    assert [row["team_id"] for row in rows] == [65, 57, 322]
    assert rows[0]["points"] == 9
    assert rows[0]["group_name"] == "Matchday"


def test_matches_round_trip(temp_db: Path) -> None:
    with write_connection() as conn:
        seed_competition_and_season(conn)
        assert ingest_matches(conn) == 2

    with read_connection() as conn:
        row = conn.execute("SELECT * FROM matches WHERE id = 560542").fetchone()
    assert row["status"] == "FINISHED"
    assert row["utc_date"] == "2026-08-21T19:00:00Z"
    assert (row["full_time_home"], row["full_time_away"]) == (3, 0)
    assert row["winner"] == "HOME_TEAM"


def test_pre_kickoff_scores_are_stored_as_null(temp_db: Path) -> None:
    scheduled = {
        "id": 999999,
        "competition": {"id": 2021},
        "season": {"id": 2502},
        "utcDate": "2027-05-01T14:00:00Z",
        "status": "SCHEDULED",
        # matches.json 에 실제로 등장하는 팀만 쓴다. 65 는 standings 쪽에만 있다.
        "homeTeam": {"id": 57},
        "awayTeam": {"id": 1076},
        "score": {"winner": None, "fullTime": {}, "halfTime": {}},
    }
    with write_connection() as conn:
        seed_competition_and_season(conn)
        ingest_matches(conn)
        writers.upsert_matches(conn, [mappers.to_match_row(scheduled)])

    with read_connection() as conn:
        row = conn.execute("SELECT * FROM matches WHERE id = 999999").fetchone()
    assert row["winner"] is None
    assert row["full_time_home"] is None
    assert row["half_time_home"] is None


# --- 멱등성 ---


def test_repeated_ingest_is_idempotent(temp_db: Path) -> None:
    """몇 번을 돌려도 결과가 같아야 한다."""
    for _ in range(3):
        with write_connection() as conn:
            seed_competition_and_season(conn)
            ingest_standings(conn)
            ingest_matches(conn)

    with read_connection() as conn:
        counts = {
            table: conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
            for table in ("competitions", "seasons", "teams", "standings", "matches")
        }
    assert counts == {
        "competitions": 1,
        "seasons": 1,
        "teams": 5,  # 순위표 3팀 + 경기에만 나온 2팀
        "standings": 3,
        "matches": 2,
    }


def test_standings_update_in_place(temp_db: Path) -> None:
    """같은 팀의 순위가 바뀌면 행이 늘지 않고 갱신된다."""
    payload = load("standings.json")
    block = mappers.pick_standings_block(payload)

    with write_connection() as conn:
        seed_competition_and_season(conn)
        writers.upsert_teams(conn, mappers.to_team_rows_from_standings(block))
        writers.upsert_standings(conn, mappers.to_standing_rows(payload, block))

        rows = mappers.to_standing_rows(payload, block)
        rows[0]["points"] = 12
        rows[0]["played_games"] = 4
        writers.upsert_standings(conn, rows)

    with read_connection() as conn:
        row = conn.execute("SELECT * FROM standings WHERE team_id = 65").fetchone()
        total = conn.execute("SELECT COUNT(*) AS n FROM standings").fetchone()["n"]
    assert (row["points"], row["played_games"]) == (12, 4)
    assert total == 3


# --- 덮어쓰기 정책 ---


def test_slim_competition_does_not_wipe_area(temp_db: Path) -> None:
    """인라인 슬림 객체로 덮어써도 이미 채운 area 가 null 로 날아가면 안 된다."""
    full = load("competitions.json")
    standings = load("standings.json")

    with write_connection() as conn:
        writers.upsert_competition(conn, mappers.to_competition_row(full))
        writers.upsert_competition(conn, mappers.to_competition_row(standings["competition"]))

    with read_connection() as conn:
        row = conn.execute("SELECT * FROM competitions WHERE id = 2021").fetchone()
    assert row["area_name"] == "England"
    assert row["emblem"] is not None
    assert row["current_season_id"] == 2502


def test_team_snapshot_does_not_wipe_optional_fields(temp_db: Path) -> None:
    full = {
        "id": 65,
        "name": "Manchester City FC",
        "short_name": "Man City",
        "tla": "MCI",
        "crest": "https://example.test/65.png",
        "updated_at": "2026-09-08T00:00:00Z",
    }
    slim = {**full, "short_name": None, "tla": None, "crest": None}
    slim["updated_at"] = "2026-09-08T01:00:00Z"

    with write_connection() as conn:
        writers.upsert_teams(conn, [full])
        writers.upsert_teams(conn, [slim])

    with read_connection() as conn:
        row = conn.execute("SELECT * FROM teams WHERE id = 65").fetchone()
    assert row["tla"] == "MCI"
    assert row["crest"] == "https://example.test/65.png"
    assert row["updated_at"] == "2026-09-08T01:00:00Z"


# --- 제약 ---


def test_foreign_keys_reject_unknown_team(temp_db: Path) -> None:
    """팀 마스터를 건너뛰고 순위표부터 쓰면 FK 가 막는다."""
    payload = load("standings.json")
    block = mappers.pick_standings_block(payload)
    with pytest.raises(sqlite3.IntegrityError), write_connection() as conn:
        seed_competition_and_season(conn)
        writers.upsert_standings(conn, mappers.to_standing_rows(payload, block))


def test_failed_write_rolls_back(temp_db: Path) -> None:
    """한 커넥션 안에서 실패하면 앞선 쓰기도 남지 않는다."""
    payload = {"competition": {"id": 2021}, "season": {"id": 2502}}
    block = {
        "stage": "REGULAR_SEASON",
        "type": "TOTAL",
        "group": "Matchday",
        "table": [standing_row(999999)],  # 팀 마스터에 없는 id
    }
    with pytest.raises(sqlite3.IntegrityError), write_connection() as conn:
        seed_competition_and_season(conn)
        writers.upsert_standings(conn, mappers.to_standing_rows(payload, block))

    with read_connection() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM competitions").fetchone()["n"] == 0


def test_empty_row_list_writes_nothing(temp_db: Path) -> None:
    with write_connection() as conn:
        assert writers.upsert_teams(conn, []) == 0
        assert writers.upsert_matches(conn, []) == 0


# --- 수집 이력 ---


def test_record_ingest_run(temp_db: Path) -> None:
    with write_connection() as conn:
        writers.record_ingest_run(
            conn,
            competition_code="PL",
            resource="standings",
            status="success",
            started_at="2026-09-08T00:00:00Z",
            finished_at="2026-09-08T00:00:07Z",
            rows_written=20,
        )
        writers.record_ingest_run(
            conn,
            competition_code="PD",
            resource="standings",
            status="failure",
            started_at="2026-09-08T00:00:07Z",
            finished_at="2026-09-08T00:00:40Z",
            http_status=429,
            error="429 Too Many Requests",
        )

    with read_connection() as conn:
        rows = conn.execute("SELECT * FROM ingest_runs ORDER BY id").fetchall()
    assert [row["competition_code"] for row in rows] == ["PL", "PD"]
    assert rows[0]["rows_written"] == 20
    assert rows[1]["http_status"] == 429
    assert rows[1]["error"].startswith("429")
