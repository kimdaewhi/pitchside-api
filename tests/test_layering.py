"""계층 규칙을 테스트로 못 박는다.

문서로만 적어둔 의존 방향은 조용히 썩는다.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _imported_modules(path: Path) -> set[str]:
    """해당 파일이 import 하는 최상위 모듈 이름들."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_ingest_runs_without_fastapi() -> None:
    """수집 배치는 FastAPI 앱과 독립 실행 가능해야 한다."""
    code = (
        "import sys, importlib;"
        "importlib.import_module('ingest.__main__');"
        "print(sorted(m for m in sys.modules "
        "if m.split('.')[0] in {'fastapi', 'starlette', 'uvicorn'}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "[]", f"ingest 가 웹 프레임워크를 끌고 들어옴: {result.stdout}"


@pytest.mark.parametrize("package", ["app/repositories", "app/services"])
def test_lower_layers_are_framework_free(package: str) -> None:
    """리포지토리·서비스는 HTTP 를 모른다."""
    forbidden = {"fastapi", "starlette", "httpx", "requests"}
    for path in (PROJECT_ROOT / package).glob("*.py"):
        offenders = {m for m in _imported_modules(path) if m.split(".")[0] in forbidden}
        assert not offenders, f"{path.name} 이 {offenders} 를 import 함"


def test_repositories_have_no_external_client() -> None:
    """외부 API 클라이언트는 ingest/ 한 곳에만 있어야 한다."""
    for path in (PROJECT_ROOT / "app").rglob("*.py"):
        assert "ingest" not in _imported_modules(path), f"{path} 가 ingest 를 import 함"
