"""헬스 엔드포인트."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db.connection import get_db
from app.schemas.health import HealthStatus, IngestHealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus)
def health() -> HealthStatus:
    """앱 생존 확인. DB 도 외부도 건드리지 않는다."""
    return HealthStatus(status="ok")


@router.get("/health/ingest", response_model=IngestHealthResponse)
def ingest_health(conn: sqlite3.Connection = Depends(get_db)) -> IngestHealthResponse:
    """리그별 마지막 수집 성공 시각."""
    # TODO: repositories.ingest_runs.last_success_per_league
    raise HTTPException(status_code=501, detail="not implemented")
