"""헬스 응답."""

from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: str


class LeagueIngestStatus(BaseModel):
    """리그·리소스별 마지막 수집 성공 시각."""

    competition_code: str
    resource: str
    last_success_at: str | None = None
    last_status: str | None = None


class IngestHealthResponse(BaseModel):
    leagues: list[LeagueIngestStatus]
