"""앱이 뜨고 라우트가 전부 등록되는지."""

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_routes_registered(client: TestClient) -> None:
    paths = set(client.app.openapi()["paths"])
    assert {
        "/health",
        "/health/ingest",
        "/competitions",
        "/competitions/{code}/standings",
        "/competitions/{code}/matches",
        "/competitions/{code}/teams",
        "/teams/{team_id}",
        "/teams/{team_id}/vs/{opponent_id}",
    } <= paths
