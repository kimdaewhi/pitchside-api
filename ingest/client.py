"""football-data.org API v4 클라이언트.

외부 HTTP 는 이 파일에만 존재한다. 다른 어떤 모듈도 외부로 나가지 않는다.
"""

from typing import Any

from ingest.ratelimit import RateLimiter


class FootballDataError(RuntimeError):
    """수집 실패. status_code 를 실어 이력 기록에 쓴다."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class FootballDataClient:
    """레이트리밋이 걸린 동기 클라이언트.

    모든 요청은 ``_get`` 을 거치고, ``_get`` 은 반드시 limiter 를 통과한다.
    """

    def __init__(
        self,
        api_key: str,
        *,
        limiter: RateLimiter,
        base_url: str = "https://api.football-data.org/v4",
        timeout_sec: float = 10.0,
    ) -> None:
        self._api_key = api_key
        self._limiter = limiter
        self._base_url = base_url.rstrip("/")
        self._timeout_sec = timeout_sec

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET 한 번. limiter.wait() → 요청 → 429 면 retry_on_429."""
        raise NotImplementedError  # TODO: httpx.Client, X-Auth-Token 헤더, 상태코드 처리

    def get_competition(self, external_id: int) -> dict[str, Any]:
        """GET /competitions/{id} — currentSeason 으로 시즌 전환을 감지한다."""
        raise NotImplementedError  # TODO: self._get(f"/competitions/{external_id}")

    def get_standings(self, external_id: int, season: int | None = None) -> dict[str, Any]:
        """GET /competitions/{id}/standings — standings[] 는 블록 배열로 온다."""
        raise NotImplementedError  # TODO: self._get(..., params={"season": season})

    def get_matches(self, external_id: int, season: int | None = None) -> dict[str, Any]:
        """GET /competitions/{id}/matches — 매 실행마다 현재 시즌 전체를 다시 가져온다."""
        raise NotImplementedError  # TODO: self._get(..., params={"season": season})
