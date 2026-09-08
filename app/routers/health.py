"""헬스 엔드포인트."""

from fastapi import APIRouter

from app.db.connection import read_connection
from app.schemas.health import HealthStatus, IngestHealthResponse
from app.services import health as health_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus)
def health() -> HealthStatus:
    """앱 생존 확인. DB 도 외부도 건드리지 않는다."""
    return HealthStatus(status="ok")


@router.get("/health/ingest", response_model=IngestHealthResponse)
def ingest_health() -> IngestHealthResponse:
    """리그별 마지막 수집 성공 시각."""
    with read_connection() as conn:
        return health_service.get_ingest_health(conn)
