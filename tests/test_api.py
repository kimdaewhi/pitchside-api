"""조회 엔드포인트.

seeded_db 에는 PL 만 들어 있다. 나머지 리그는 "레지스트리에는 있으나 아직 수집 안 됨"이다.
"""

from fastapi.testclient import TestClient

from tests.conftest import SCHEDULED_MATCH_ID

# 샘플에 등장하는 팀
MAN_CITY = 65  # 순위표에만 있고 경기에는 없다
ARSENAL = 57  # 560542 홈 승 (3-0 vs Coventry)
COVENTRY = 1076

# 샘플에 등장하는 경기. 둘 다 1라운드다.
ARSENAL_WIN = 560542  # ARS 3-0 COV, 2026-08-21
OTHER_MATCHDAY_1 = 560543  # 2026-08-22


# --- 대회 목록 ---


def test_list_competitions_returns_only_ingested(api: TestClient) -> None:
    response = api.get("/competitions")
    assert response.status_code == 200
    assert [c["code"] for c in response.json()] == ["PL"]


def test_list_competitions_is_empty_before_any_ingest(client: TestClient) -> None:
    """빈 껍데기를 지어내지 않는다."""
    assert client.get("/competitions").json() == []


# --- 순위표 ---


def test_standings_ordered_by_position(api: TestClient) -> None:
    body = api.get("/competitions/PL/standings").json()
    assert body["competition"]["code"] == "PL"
    assert body["season"]["id"] == 2502
    assert (body["stage"], body["type"], body["group"]) == (
        "REGULAR_SEASON",
        "TOTAL",
        "Matchday",
    )
    assert [row["position"] for row in body["table"]] == [1, 2, 3]
    assert body["table"][0]["team"]["tla"] == "MCI"
    assert body["table"][0]["points"] == 9


def test_standings_response_has_no_form_field(api: TestClient) -> None:
    """외부 form 은 항상 null 이라 응답 표면에서 뺐다."""
    row = api.get("/competitions/PL/standings").json()["table"][0]
    assert "form" not in row


def test_standings_uses_snake_case(api: TestClient) -> None:
    row = api.get("/competitions/PL/standings").json()["table"][0]
    assert "played_games" in row and "goal_difference" in row
    assert "playedGames" not in row


def test_unknown_league_code_is_404(api: TestClient) -> None:
    response = api.get("/competitions/XX/standings")
    assert response.status_code == 404
    assert "unknown competition code" in response.json()["detail"]


def test_known_league_without_data_is_404_with_different_reason(api: TestClient) -> None:
    """코드가 틀린 것과 아직 수집되지 않은 것은 다른 상황이다."""
    response = api.get("/competitions/PD/standings")
    assert response.status_code == 404
    assert "수집되지 않았습니다" in response.json()["detail"]


# --- 일정·결과 ---


def test_list_matches(api: TestClient) -> None:
    body = api.get("/competitions/PL/matches").json()
    assert body["count"] == 2
    first = body["matches"][0]
    assert first["id"] == 560542
    assert first["home_team"]["tla"] == "ARS"
    assert first["score"]["full_time_home"] == 3
    assert first["score"]["winner"] == "HOME_TEAM"


def test_matches_sorted_by_kickoff(api: TestClient) -> None:
    dates = [m["utc_date"] for m in api.get("/competitions/PL/matches").json()["matches"]]
    assert dates == sorted(dates)


def test_matches_filter_by_status(api: TestClient) -> None:
    assert api.get("/competitions/PL/matches?status=FINISHED").json()["count"] == 2
    assert api.get("/competitions/PL/matches?status=SCHEDULED").json()["count"] == 0


def test_matches_filter_by_matchday(api: TestClient) -> None:
    assert api.get("/competitions/PL/matches?matchday=1").json()["count"] == 2
    assert api.get("/competitions/PL/matches?matchday=38").json()["count"] == 0


def test_invalid_status_is_400_not_empty_list(api: TestClient) -> None:
    """오타를 빈 목록으로 돌려주면 디버깅이 어렵다."""
    response = api.get("/competitions/PL/matches?status=BOGUS")
    assert response.status_code == 400
    assert "알 수 없는 status" in response.json()["detail"]


# --- 팀 ---


def test_list_teams_comes_from_standings(api: TestClient) -> None:
    body = api.get("/competitions/PL/teams").json()
    assert body["count"] == 3
    assert {t["id"] for t in body["teams"]} == {MAN_CITY, ARSENAL, 322}


def test_get_team_attaches_form(api: TestClient) -> None:
    body = api.get(f"/teams/{ARSENAL}").json()
    assert body["team"]["tla"] == "ARS"
    assert body["form"]["results"] == ["W"]


def test_unknown_team_is_404(api: TestClient) -> None:
    assert api.get("/teams/999999").status_code == 404


# --- 폼 가이드 ---


def test_form_is_not_padded(api: TestClient) -> None:
    """5경기 미만이면 있는 만큼만. 패딩 금지."""
    body = api.get(f"/competitions/PL/teams/{ARSENAL}/form").json()
    assert body["results"] == ["W"]


def test_form_is_from_the_teams_perspective(api: TestClient) -> None:
    """같은 경기가 원정 팀에게는 패배다."""
    assert api.get(f"/competitions/PL/teams/{COVENTRY}/form").json()["results"] == ["L"]


def test_form_is_empty_without_finished_matches(api: TestClient) -> None:
    body = api.get(f"/competitions/PL/teams/{MAN_CITY}/form").json()
    assert body["team"]["tla"] == "MCI"
    assert body["results"] == []


# --- 상대전적 ---


def test_head_to_head_from_home_side(api: TestClient) -> None:
    body = api.get(f"/teams/{ARSENAL}/vs/{COVENTRY}").json()
    summary = body["summary"]
    assert summary["team"]["id"] == ARSENAL
    assert (summary["played"], summary["won"], summary["draw"], summary["lost"]) == (1, 1, 0, 0)
    assert (summary["goals_for"], summary["goals_against"]) == (3, 0)
    assert [m["id"] for m in body["recent_matches"]] == [560542]


def test_head_to_head_is_bidirectional(api: TestClient) -> None:
    """홈/원정이 뒤집혀도 같은 경기를 찾아야 한다. 단방향 조회면 절반을 놓친다."""
    body = api.get(f"/teams/{COVENTRY}/vs/{ARSENAL}").json()
    summary = body["summary"]
    assert (summary["played"], summary["won"], summary["lost"]) == (1, 0, 1)
    assert (summary["goals_for"], summary["goals_against"]) == (0, 3)


def test_head_to_head_defaults_to_all_competitions(api: TestClient) -> None:
    assert api.get(f"/teams/{ARSENAL}/vs/{COVENTRY}").json()["competition_code"] is None


def test_head_to_head_competition_filter(api: TestClient) -> None:
    body = api.get(f"/teams/{ARSENAL}/vs/{COVENTRY}?competition=PL").json()
    assert body["competition_code"] == "PL"
    assert body["summary"]["played"] == 1


def test_head_to_head_unknown_competition_is_404(api: TestClient) -> None:
    assert api.get(f"/teams/{ARSENAL}/vs/{COVENTRY}?competition=XX").status_code == 404


def test_head_to_head_against_self_is_400(api: TestClient) -> None:
    response = api.get(f"/teams/{ARSENAL}/vs/{ARSENAL}")
    assert response.status_code == 400


def test_head_to_head_without_meetings_is_zeroed(api: TestClient) -> None:
    body = api.get(f"/teams/{MAN_CITY}/vs/{ARSENAL}").json()
    assert body["summary"]["played"] == 0
    assert body["summary"]["goals_for"] == 0
    assert body["recent_matches"] == []


# --- 경기 상세 ---


def test_match_detail_carries_the_match_itself(api: TestClient) -> None:
    body = api.get(f"/matches/{ARSENAL_WIN}").json()
    assert body["match"]["id"] == ARSENAL_WIN
    assert body["match"]["status"] == "FINISHED"
    assert body["match"]["matchday"] == 1
    assert body["match"]["score"]["full_time_home"] == 3
    assert body["competition"]["code"] == "PL"
    assert body["season"]["id"] == 2502


def test_match_detail_attaches_standings(api: TestClient) -> None:
    home = api.get(f"/matches/{ARSENAL_WIN}").json()["home"]
    assert home["team"]["id"] == ARSENAL
    assert home["standing"]["position"] == 2
    assert home["standing"]["points"] == 9


def test_match_detail_standing_is_null_for_team_outside_the_table(api: TestClient) -> None:
    """순위표에 없는 팀은 null 이다. 0으로 지어내지 않는다."""
    away = api.get(f"/matches/{ARSENAL_WIN}").json()["away"]
    assert away["team"]["id"] == COVENTRY
    assert away["standing"] is None


def test_match_detail_form_excludes_the_match_itself(api: TestClient) -> None:
    """폼은 그 경기 이전 기준이다. 자기 자신이 들어가면 순환이다."""
    body = api.get(f"/matches/{ARSENAL_WIN}").json()
    assert body["home"]["form"] == []
    assert body["away"]["form"] == []


def test_match_detail_head_to_head_is_before_this_match(api: TestClient) -> None:
    """유일한 맞대결이 이 경기라 이전 기준이면 비어야 한다."""
    body = api.get(f"/matches/{ARSENAL_WIN}").json()
    h2h = body["head_to_head"]
    assert (h2h["team"]["id"], h2h["opponent"]["id"]) == (ARSENAL, COVENTRY)
    assert h2h["played"] == 0
    assert body["recent_meetings"] == []


def test_match_detail_same_matchday_excludes_self(api: TestClient) -> None:
    body = api.get(f"/matches/{ARSENAL_WIN}").json()
    assert [m["id"] for m in body["same_matchday"]] == [OTHER_MATCHDAY_1]


def test_match_detail_uses_snake_case(api: TestClient) -> None:
    body = api.get(f"/matches/{ARSENAL_WIN}").json()
    assert "same_matchday" in body and "recent_meetings" in body
    assert "goal_difference" in body["home"]["standing"]


def test_unknown_match_is_404(api: TestClient) -> None:
    response = api.get("/matches/999999")
    assert response.status_code == 404
    assert "저장된 경기가 아닙니다" in response.json()["detail"]


# --- 경기 상세: 예정 경기 ---


def test_scheduled_match_detail_has_null_score(api_with_scheduled: TestClient) -> None:
    """예정 경기는 스코어 다섯 필드가 전부 null 이다. 0으로 채우지 않는다."""
    match = api_with_scheduled.get(f"/matches/{SCHEDULED_MATCH_ID}").json()["match"]
    assert match["status"] == "SCHEDULED"
    assert match["score"] == {
        "winner": None,
        "full_time_home": None,
        "full_time_away": None,
        "half_time_home": None,
        "half_time_away": None,
    }


def test_scheduled_match_detail_still_has_context(api_with_scheduled: TestClient) -> None:
    """치르지 않은 경기여도 순위와 폼은 나온다."""
    body = api_with_scheduled.get(f"/matches/{SCHEDULED_MATCH_ID}").json()
    assert body["home"]["standing"]["position"] == 2  # ARS
    assert body["away"]["standing"]["position"] == 1  # MCI
    # 8/21 승리가 이 경기(8/29)보다 앞서므로 폼에 잡힌다.
    assert body["home"]["form"] == ["W"]
    # MCI 는 순위표에만 있고 치른 경기가 없다.
    assert body["away"]["form"] == []


def test_scheduled_match_detail_has_no_same_matchday_peers(
    api_with_scheduled: TestClient,
) -> None:
    """2라운드에는 이 경기뿐이다. 자기 자신만 빠지면 빈 목록이 된다."""
    body = api_with_scheduled.get(f"/matches/{SCHEDULED_MATCH_ID}").json()
    assert body["same_matchday"] == []


def test_scheduled_match_does_not_leak_into_form_of_finished_match(
    api_with_scheduled: TestClient,
) -> None:
    """치르지 않은 경기는 어떤 폼에도 들어가지 않는다."""
    body = api_with_scheduled.get(f"/matches/{ARSENAL_WIN}").json()
    assert body["home"]["form"] == []


# --- 헬스 ---


def test_ingest_health_reports_recorded_runs(api: TestClient) -> None:
    body = api.get("/health/ingest").json()
    pl = next(
        row
        for row in body["leagues"]
        if row["competition_code"] == "PL" and row["resource"] == "standings"
    )
    assert pl["last_success_at"] == "2026-09-08T00:00:07Z"
    assert pl["last_status"] == "success"


def test_ingest_health_shows_never_ingested_leagues(api: TestClient) -> None:
    """이력이 아예 없는 리그가 헬스에서 사라지면 안 된다."""
    body = api.get("/health/ingest").json()
    codes = {row["competition_code"] for row in body["leagues"]}
    assert {"PL", "PD", "FL1", "SA", "BL1"} <= codes

    pd_rows = [row for row in body["leagues"] if row["competition_code"] == "PD"]
    assert pd_rows
    assert all(row["last_success_at"] is None and row["last_status"] is None for row in pd_rows)
