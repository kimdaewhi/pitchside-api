"""커넥션의 스레드 구속을 못 박는다.

FastAPI 는 동기 핸들러를 워커 스레드 풀에서 돌린다. 커넥션이 요청 하나 안에서
스레드를 넘어가면 ``sqlite3.ProgrammingError`` 로 500 이 난다. 동시 요청이
몰려야 드러나므로 단발 요청 테스트로는 잡히지 않는다.
"""

import ast
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# DB 를 건드리는 모든 엔드포인트. 폼만이 아니라 전부가 같은 함정을 공유했다.
DB_ENDPOINTS = [
    "/competitions",
    "/competitions/PL/standings",
    "/competitions/PL/matches",
    "/competitions/PL/teams",
    "/competitions/PL/teams/57/form",
    "/teams/57",
    "/teams/57/vs/61",
    # 한 요청에 쿼리를 여섯 번 낸다. 커넥션 스레드 구속을 가장 세게 검증한다.
    "/matches/560542",
    "/health/ingest",
]


def test_concurrent_form_requests_do_not_fail(api: TestClient) -> None:
    """순위표 화면이 팀별 폼을 한꺼번에 요청하는 상황."""
    urls = [f"/competitions/PL/teams/{team_id}/form" for team_id in (57, 61, 62, 63, 64, 65)] * 5
    with ThreadPoolExecutor(max_workers=12) as pool:
        codes = list(pool.map(lambda url: api.get(url).status_code, urls))
    assert not [c for c in codes if c >= 500], f"5xx 발생: {sorted(set(codes))}"


def test_all_db_endpoints_survive_concurrency(api: TestClient) -> None:
    """DB 를 읽는 엔드포인트 전부를 동시에 두드린다."""
    urls = DB_ENDPOINTS * 5
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda url: (url, api.get(url).status_code), urls))
    failures = sorted({result for result in results if result[1] >= 500})
    assert not failures, f"5xx 발생: {failures}"


@pytest.mark.parametrize(
    "path", sorted((PROJECT_ROOT / "app" / "routers").glob("*.py")), ids=lambda p: p.name
)
def test_routers_do_not_inject_connections(path: Path) -> None:
    """커넥션을 ``Depends`` 로 주입하지 않는다.

    동기 제너레이터 의존성은 진입·본문·정리가 서로 다른 워커 스레드에서 돌 수
    있다. 커넥션은 핸들러 본문 안에서 ``read_connection()`` 으로 연다.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        annotations = [ast.unparse(a.annotation) for a in node.args.args if a.annotation]
        offenders = [a for a in annotations if "Connection" in a]
        assert not offenders, f"{path.name}::{node.name} 이 커넥션을 주입받음: {offenders}"


def test_connection_module_exposes_no_fastapi_dependency() -> None:
    """``get_db`` 같은 커넥션 주입 의존성이 되살아나지 않게 한다."""
    import app.db.connection as connection_module

    assert not hasattr(connection_module, "get_db")
