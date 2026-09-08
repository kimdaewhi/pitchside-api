"""테스트 공통 픽스처.

실제 DB 파일을 건드리지 않도록 매 테스트마다 임시 경로로 갈아끼운다.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.init_db import init_db
from app.main import create_app


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
def client(temp_db: Path) -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client
