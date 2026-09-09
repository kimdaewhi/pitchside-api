"""테스트 공통 픽스처.

실제 DB 파일을 건드리지 않도록 매 테스트마다 임시 경로로 갈아끼운다.
"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.connection import write_connection
from app.db.init_db import init_db
from app.main import create_app
from ingest import mappers, writers

SAMPLES = Path(__file__).resolve().parent.parent / "samples"

# 샘플에 없는 예정 경기. scheduled_db 가 넣는다.
SCHEDULED_MATCH_ID = 560999


def load_sample(name: str) -> dict[str, Any]:
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


@pytest.fixture
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """임시 DB 를 만들고 스키마를 적용한다."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    get_settings.cache_clear()
    init_db()
    yield db_path
    get_settings.cache_clear()


@pytest.fixture
def seeded_db(temp_db: Path) -> Path:
    """samples/ 를 수집기와 같은 순서로 밀어 넣은 DB.

    PL 만 들어간다. 다른 리그는 "레지스트리에는 있으나 아직 수집 안 됨" 상태가 되어,
    그 경로를 검증하는 데 그대로 쓰인다.
    """
    competition = load_sample("competitions.json")
    standings = load_sample("standings.json")
    matches = load_sample("matches.json")
    block = mappers.pick_standings_block(standings)

    with write_connection() as conn:
        writers.upsert_competition(conn, mappers.to_competition_row(competition))
        writers.upsert_seasons(
            conn, [mappers.to_season_row(competition["currentSeason"], competition["id"])]
        )
        writers.upsert_teams(conn, mappers.to_team_rows_from_standings(block))
        writers.upsert_teams(conn, mappers.to_team_rows_from_matches(matches))
        writers.upsert_standings(conn, mappers.to_standing_rows(standings, block))
        writers.upsert_matches(conn, mappers.to_match_rows(matches))
        writers.record_ingest_run(
            conn,
            competition_code="PL",
            resource="standings",
            status="success",
            started_at="2026-09-08T00:00:00Z",
            finished_at="2026-09-08T00:00:07Z",
            rows_written=3,
        )
    return temp_db


@pytest.fixture
def scheduled_db(seeded_db: Path) -> Path:
    """seeded_db 위에 아직 안 치른 경기 하나를 얹는다.

    samples/ 는 캡처한 실제 응답이라 건드리지 않는다. 거기에 경기를 더하면
    ``count == 2`` 처럼 샘플 크기에 걸린 기존 단언이 줄줄이 깨진다.
    그래서 예정 경기가 필요한 테스트만 이 픽스처를 쓴다.

    킥오프는 샘플의 두 경기(8/21, 8/22)보다 뒤다. 점수는 전부 null 이다.
    """
    with write_connection() as conn:
        writers.upsert_matches(
            conn,
            [
                {
                    "id": SCHEDULED_MATCH_ID,
                    "competition_id": 2021,
                    "season_id": 2502,
                    "utc_date": "2026-08-29T14:00:00Z",
                    "status": "SCHEDULED",
                    "matchday": 2,
                    "stage": "REGULAR_SEASON",
                    "group_name": None,
                    "home_team_id": 57,  # ARS
                    "away_team_id": 65,  # MCI
                    "winner": None,
                    "duration": "REGULAR",
                    "full_time_home": None,
                    "full_time_away": None,
                    "half_time_home": None,
                    "half_time_away": None,
                    "last_updated": "2026-08-23T00:00:00Z",
                }
            ],
        )
    return seeded_db


@pytest.fixture
def client(temp_db: Path) -> Iterator[TestClient]:
    """빈 DB 위의 클라이언트."""
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def api(seeded_db: Path) -> Iterator[TestClient]:
    """PL 데이터가 들어 있는 DB 위의 클라이언트."""
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def api_with_scheduled(scheduled_db: Path) -> Iterator[TestClient]:
    """예정 경기까지 들어 있는 DB 위의 클라이언트."""
    with TestClient(create_app()) as test_client:
        yield test_client
