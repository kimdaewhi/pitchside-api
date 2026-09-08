"""football-data.org 클라이언트.

httpx.MockTransport 로 네트워크 없이 검증한다. 실제 잠도 자지 않는다.
"""

import httpx
import pytest

from ingest.client import FootballDataClient, FootballDataError
from ingest.ratelimit import RateLimiter

SAMPLE = {"competition": {"id": 2021, "code": "PL"}}


def make_client(handler, **kwargs) -> FootballDataClient:
    """sleep 을 가로챈 limiter 와 가짜 transport 를 물린 클라이언트."""
    limiter = RateLimiter(0.0, sleep=lambda _: None)
    return FootballDataClient(
        "test-key",
        limiter=limiter,
        transport=httpx.MockTransport(handler),
        base_delay_sec=0.0,
        **kwargs,
    )


def test_get_standings_returns_payload_unparsed() -> None:
    """응답을 가공하지 않고 그대로 돌려준다. 파싱은 mappers 의 일이다."""
    with make_client(lambda request: httpx.Response(200, json=SAMPLE)) as client:
        assert client.get_standings(2021) == SAMPLE


def test_sends_auth_token_header() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=SAMPLE)

    with make_client(handler) as client:
        client.get_competition(2021)

    assert seen[0].headers["X-Auth-Token"] == "test-key"
    assert seen[0].url.path == "/v4/competitions/2021"


def test_none_params_are_dropped() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=SAMPLE)

    with make_client(handler) as client:
        client.get_matches(2021)
        client.get_matches(2021, season=2026)

    assert seen[0].url.params.get("season") is None
    assert seen[1].url.params["season"] == "2026"


def test_429_is_retried_then_succeeds() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, json=SAMPLE)

    with make_client(handler) as client:
        assert client.get_standings(2021) == SAMPLE
    assert calls == 2


def test_persistent_429_becomes_football_data_error() -> None:
    """재시도를 소진한 429 도 결국 FootballDataError 로 올라온다.

    호출부(run.py)가 예외 하나만 잡으면 되게 하려는 것이다.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    with make_client(handler, max_attempts=3) as client, pytest.raises(FootballDataError) as exc:
        client.get_standings(2021)
    assert exc.value.status_code == 429


def test_404_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404)

    with make_client(handler) as client, pytest.raises(FootballDataError) as exc:
        client.get_competition(9999)
    assert exc.value.status_code == 404
    assert calls == 1


def test_network_error_is_not_retried() -> None:
    """타임아웃을 붙잡고 늘어지면 남은 리그가 분당 한도 안에 못 들어온다."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectTimeout("timed out")

    with make_client(handler) as client, pytest.raises(FootballDataError):
        client.get_matches(2021)
    assert calls == 1


def test_empty_api_key_fails_fast() -> None:
    with pytest.raises(FootballDataError):
        FootballDataClient("", limiter=RateLimiter(0.0))


def test_rate_limiter_spaces_out_sequential_calls() -> None:
    """리그를 순차로 도는 동안 호출 간격이 실제로 걸리는지."""
    slept: list[float] = []
    limiter = RateLimiter(6.5, sleep=slept.append, monotonic=lambda: 0.0)
    client = FootballDataClient(
        "k",
        limiter=limiter,
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=SAMPLE)),
    )
    with client:
        for _ in range(3):
            client.get_standings(2021)
    assert slept == [6.5, 6.5]  # 첫 콜은 즉시, 이후 두 번은 간격을 지킨다
