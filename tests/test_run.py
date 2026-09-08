"""배치 오케스트레이션.

가짜 클라이언트로 네트워크 없이 검증한다. 관심사는 순서·실패 격리·이력·종료 코드다.
"""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from app.db.connection import read_connection
from app.leagues import League
from ingest.client import FootballDataError
from ingest.run import BatchReport, LeagueResult, run_batch, validate_resources

SAMPLES = Path(__file__).resolve().parent.parent / "samples"

PL = League("PL", 2021, "Premier League", "England")
PD = League("PD", 2014, "La Liga", "Spain")


def load(name: str) -> dict[str, Any]:
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


def payload_for(name: str, league: League) -> dict[str, Any]:
    """샘플을 특정 리그의 응답인 것처럼 바꿔 준다.

    competition id/code 와 season id 는 전역 고유해야 하므로 리그마다 다르게 둔다.
    """
    payload = copy.deepcopy(load(name))
    season_id = league.external_id * 10
    payload["competition"]["id"] = league.external_id
    payload["competition"]["code"] = league.code
    payload["competition"]["name"] = league.name
    if "season" in payload:
        payload["season"]["id"] = season_id
    for match in payload.get("matches") or []:
        match["competition"]["id"] = league.external_id
        match["season"]["id"] = season_id
        match["id"] += league.external_id  # 경기 id 도 전역 고유
    return payload


class FakeClient:
    """호출을 기록하고, 지정한 리그에서만 실패하는 클라이언트."""

    def __init__(self, *, fail_on: set[tuple[int, str]] | None = None) -> None:
        self.calls: list[tuple[str, int]] = []
        self._fail_on = fail_on or set()

    def _serve(self, resource: str, external_id: int, sample: str) -> dict[str, Any]:
        self.calls.append((resource, external_id))
        if (external_id, resource) in self._fail_on:
            raise FootballDataError(f"429 Too Many Requests: {resource}", status_code=429)
        league = next(lg for lg in (PL, PD) if lg.external_id == external_id)
        return payload_for(sample, league)

    def get_standings(self, external_id: int, season: int | None = None) -> dict[str, Any]:
        return self._serve("standings", external_id, "standings.json")

    def get_matches(self, external_id: int, season: int | None = None) -> dict[str, Any]:
        return self._serve("matches", external_id, "matches.json")

    def get_competition(self, external_id: int) -> dict[str, Any]:
        self.calls.append(("competitions", external_id))
        payload = copy.deepcopy(load("competitions.json"))
        league = next(lg for lg in (PL, PD) if lg.external_id == external_id)
        payload["id"] = league.external_id
        payload["code"] = league.code
        payload["currentSeason"]["id"] = league.external_id * 10
        return payload


# --- 인자 검증 ---


def test_unknown_resource_is_rejected_before_any_call() -> None:
    client = FakeClient()
    with pytest.raises(ValueError, match="알 수 없는 리소스"):
        run_batch(resources=["bogus"], leagues=[PL], client=client)
    assert client.calls == []  # 호출이 한 건도 나가지 않았다


def test_empty_resource_list_is_rejected() -> None:
    with pytest.raises(ValueError):
        validate_resources([])


# --- 순차 실행 ---


def test_leagues_run_sequentially_league_outer(temp_db: Path) -> None:
    client = FakeClient()
    run_batch(resources=["standings", "matches"], leagues=[PL, PD], client=client)
    assert client.calls == [
        ("standings", 2021),
        ("matches", 2021),
        ("standings", 2014),
        ("matches", 2014),
    ]


def test_successful_batch_stores_rows(temp_db: Path) -> None:
    client = FakeClient()
    report = run_batch(resources=["standings", "matches"], leagues=[PL, PD], client=client)

    assert report.failed == []
    assert report.exit_code == 0

    with read_connection() as conn:
        counts = {
            table: conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
            for table in ("competitions", "seasons", "standings", "matches")
        }
    assert counts == {"competitions": 2, "seasons": 2, "standings": 6, "matches": 4}


def test_batch_is_idempotent(temp_db: Path) -> None:
    for _ in range(3):
        run_batch(resources=["standings", "matches"], leagues=[PL], client=FakeClient())

    with read_connection() as conn:
        standings = conn.execute("SELECT COUNT(*) AS n FROM standings").fetchone()["n"]
        matches = conn.execute("SELECT COUNT(*) AS n FROM matches").fetchone()["n"]
        runs = conn.execute("SELECT COUNT(*) AS n FROM ingest_runs").fetchone()["n"]
    assert (standings, matches) == (3, 2)
    assert runs == 6  # 이력은 실행마다 쌓인다


# --- 실패 격리 ---


def test_one_league_failure_does_not_stop_the_batch(temp_db: Path) -> None:
    """한 리그 실패가 배치 전체를 죽이면 안 된다."""
    client = FakeClient(fail_on={(2021, "standings")})
    report = run_batch(resources=["standings"], leagues=[PL, PD], client=client)

    assert [r.status for r in report.results] == ["failure", "success"]
    assert client.calls == [("standings", 2021), ("standings", 2014)]
    assert report.exit_code == 0  # 부분 실패는 cron 을 깨우지 않는다


def test_failed_league_writes_nothing(temp_db: Path) -> None:
    """실패한 단위는 롤백된다. 절반만 쓰인 상태가 남으면 안 된다."""
    client = FakeClient(fail_on={(2021, "standings")})
    run_batch(resources=["standings"], leagues=[PL, PD], client=client)

    with read_connection() as conn:
        codes = [r["code"] for r in conn.execute("SELECT code FROM competitions")]
    assert codes == ["PD"]


def test_total_failure_returns_nonzero_exit_code(temp_db: Path) -> None:
    client = FakeClient(fail_on={(2021, "standings"), (2014, "standings")})
    report = run_batch(resources=["standings"], leagues=[PL, PD], client=client)
    assert len(report.failed) == 2
    assert report.exit_code == 1


# --- 수집 이력 ---


def test_ingest_runs_record_both_outcomes(temp_db: Path) -> None:
    client = FakeClient(fail_on={(2021, "standings")})
    run_batch(resources=["standings"], leagues=[PL, PD], client=client)

    with read_connection() as conn:
        rows = conn.execute("SELECT * FROM ingest_runs ORDER BY id").fetchall()

    assert [(r["competition_code"], r["status"]) for r in rows] == [
        ("PL", "failure"),
        ("PD", "success"),
    ]
    failure, success = rows
    assert failure["http_status"] == 429
    assert "429" in failure["error"]
    assert failure["rows_written"] is None
    assert success["rows_written"] == 3
    assert success["error"] is None
    assert success["started_at"] <= success["finished_at"]


def test_failure_history_survives_the_rollback(temp_db: Path) -> None:
    """단위가 롤백돼도 이력 행은 남아야 헬스 엔드포인트가 실패를 볼 수 있다."""
    client = FakeClient(fail_on={(2021, "standings")})
    run_batch(resources=["standings"], leagues=[PL], client=client)

    with read_connection() as conn:
        runs = conn.execute("SELECT COUNT(*) AS n FROM ingest_runs").fetchone()["n"]
        comps = conn.execute("SELECT COUNT(*) AS n FROM competitions").fetchone()["n"]
    assert (runs, comps) == (1, 0)


# --- 리포트 ---


def test_empty_report_is_a_failure() -> None:
    assert BatchReport().exit_code == 1


def test_report_totals() -> None:
    report = BatchReport(
        results=[
            LeagueResult("PL", "standings", "success", rows_written=20),
            LeagueResult("PD", "standings", "failure", error="boom"),
        ]
    )
    assert report.rows_written == 20
    assert [r.competition_code for r in report.failed] == ["PD"]
    assert report.exit_code == 0
