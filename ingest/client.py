"""football-data.org API v4 클라이언트.

외부 HTTP 는 이 파일에만 존재한다. 다른 어떤 모듈도 외부로 나가지 않는다.
응답은 파싱하지 않고 dict 그대로 돌려준다. 변환은 ``ingest/mappers.py`` 의 일이다.
"""

import logging
from types import TracebackType
from typing import Any, Self

import httpx

from ingest.ratelimit import RateLimitedError, RateLimiter, retry_on_429

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.football-data.org/v4"


class FootballDataError(RuntimeError):
    """수집 실패. status_code 를 실어 이력 기록에 쓴다."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _parse_retry_after(value: str | None) -> float | None:
    """Retry-After 헤더를 초 단위로. 초 형식만 받고 HTTP-date 는 무시한다."""
    if value is None:
        return None
    try:
        return float(value.strip())
    except ValueError:
        return None


class FootballDataClient:
    """레이트리밋이 걸린 동기 클라이언트.

    모든 요청은 ``_get`` 을 거치고, ``_get`` 은 반드시 limiter 를 통과한다.
    커넥션을 재사용하므로 배치 하나당 인스턴스 하나를 만들어 끝까지 쓰고 닫는다.

        with FootballDataClient.from_settings() as client:
            payload = client.get_standings(2021)
    """

    def __init__(
        self,
        api_key: str,
        *,
        limiter: RateLimiter,
        base_url: str = DEFAULT_BASE_URL,
        timeout_sec: float = 10.0,
        max_attempts: int = 4,
        base_delay_sec: float = 8.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise FootballDataError("FOOTBALL_DATA_API_KEY 가 비어 있다")
        self._limiter = limiter
        self._max_attempts = max_attempts
        self._base_delay_sec = base_delay_sec
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"X-Auth-Token": api_key},
            timeout=timeout_sec,
            transport=transport,
        )

    @classmethod
    def from_settings(cls, **overrides: Any) -> Self:
        """환경변수 설정으로 클라이언트를 만든다."""
        from app.config import get_settings

        settings = get_settings()
        kwargs: dict[str, Any] = {
            "limiter": RateLimiter(settings.ingest_min_interval_sec),
            "base_url": settings.football_data_base_url,
            "timeout_sec": settings.football_data_timeout_sec,
            "max_attempts": settings.ingest_max_retries,
            "base_delay_sec": settings.ingest_retry_base_delay_sec,
        }
        kwargs.update(overrides)
        return cls(settings.football_data_api_key, **kwargs)

    # --- 수명주기 ---

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # --- 요청 ---

    def _request_once(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """실제 요청 한 번. 429 는 재시도 대상이므로 RateLimitedError 로 올린다."""
        self._limiter.wait()
        logger.info("GET %s %s", path, params or "")
        try:
            response = self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            # 타임아웃·연결 실패는 재시도하지 않는다. 이 리그를 실패로 두고 넘어간다.
            raise FootballDataError(f"요청 실패: {path} ({exc})") from exc

        if response.status_code == 429:
            raise RateLimitedError(
                f"429 Too Many Requests: {path}",
                retry_after_sec=_parse_retry_after(response.headers.get("Retry-After")),
            )
        if response.status_code >= 400:
            raise FootballDataError(
                f"{response.status_code} {response.reason_phrase}: {path}",
                status_code=response.status_code,
            )
        try:
            return response.json()
        except ValueError as exc:
            raise FootballDataError(
                f"JSON 파싱 실패: {path}", status_code=response.status_code
            ) from exc

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET 한 번. limiter.wait() → 요청 → 429 면 지수 백오프 재시도.

        None 인 쿼리 파라미터는 떨군다. 재시도까지 소진한 429 도 결국
        FootballDataError 로 바꿔 올려, 호출부는 이 예외 하나만 잡으면 되게 한다.
        """
        cleaned = {k: v for k, v in (params or {}).items() if v is not None}
        try:
            return retry_on_429(
                lambda: self._request_once(path, cleaned),
                max_attempts=self._max_attempts,
                base_delay_sec=self._base_delay_sec,
                limiter=self._limiter,
            )
        except RateLimitedError as exc:
            raise FootballDataError(str(exc), status_code=429) from exc

    # --- 엔드포인트 ---

    def get_competition(self, external_id: int) -> dict[str, Any]:
        """GET /competitions/{id} — currentSeason 으로 시즌 전환을 감지한다."""
        return self._get(f"/competitions/{external_id}")

    def get_standings(self, external_id: int, season: int | None = None) -> dict[str, Any]:
        """GET /competitions/{id}/standings — standings[] 는 블록 배열로 온다.

        season 은 시즌 시작 연도다 (2026-27 시즌이면 2026).
        생략하면 서버가 현재 시즌을 준다.
        """
        return self._get(f"/competitions/{external_id}/standings", {"season": season})

    def get_matches(self, external_id: int, season: int | None = None) -> dict[str, Any]:
        """GET /competitions/{id}/matches — 매 실행마다 현재 시즌 전체를 다시 가져온다."""
        return self._get(f"/competitions/{external_id}/matches", {"season": season})
