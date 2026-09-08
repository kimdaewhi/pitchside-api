"""레이트리밋과 429 백오프.

실제로 잠들지 않도록 sleep / monotonic 을 주입한다.
"""

import pytest

from ingest.ratelimit import RateLimitedError, RateLimiter, retry_on_429


class FakeClock:
    """호출된 sleep 시간을 기록하고 그만큼 시계를 앞으로 돌린다."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds

    def monotonic(self) -> float:
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def test_first_call_does_not_wait(clock: FakeClock) -> None:
    limiter = RateLimiter(6.5, sleep=clock.sleep, monotonic=clock.monotonic)
    limiter.wait()
    assert clock.slept == []


def test_second_call_waits_the_remaining_interval(clock: FakeClock) -> None:
    limiter = RateLimiter(6.5, sleep=clock.sleep, monotonic=clock.monotonic)
    limiter.wait()
    clock.now += 2.0  # 요청 처리에 2초 걸렸다고 치자
    limiter.wait()
    assert clock.slept == [pytest.approx(4.5)]


def test_no_wait_when_interval_already_elapsed(clock: FakeClock) -> None:
    limiter = RateLimiter(6.5, sleep=clock.sleep, monotonic=clock.monotonic)
    limiter.wait()
    clock.now += 10.0
    limiter.wait()
    assert clock.slept == []


def test_ten_calls_stay_within_the_minute_budget(clock: FakeClock) -> None:
    """5리그 x (standings + matches) = 10콜이 분당 한도 밖으로 나가지 않는지."""
    limiter = RateLimiter(6.5, sleep=clock.sleep, monotonic=clock.monotonic)
    start = clock.now
    for _ in range(10):
        limiter.wait()
    # 호출 간격만 9번. 첫 콜은 즉시 나간다.
    assert clock.now - start == pytest.approx(6.5 * 9)


def test_retry_succeeds_after_backoff(clock: FakeClock) -> None:
    attempts = 0

    def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RateLimitedError("429")
        return "ok"

    result = retry_on_429(flaky, max_attempts=4, base_delay_sec=8.0, sleep=clock.sleep)
    assert result == "ok"
    assert attempts == 3
    assert clock.slept == [8.0, 16.0]  # 지수 백오프


def test_retry_honours_longer_retry_after(clock: FakeClock) -> None:
    def always_limited() -> str:
        raise RateLimitedError("429", retry_after_sec=30.0)

    with pytest.raises(RateLimitedError):
        retry_on_429(always_limited, max_attempts=2, base_delay_sec=8.0, sleep=clock.sleep)
    assert clock.slept == [30.0]  # 서버가 알려준 값이 더 길면 그쪽을 따른다


def test_retry_raises_after_exhausting_attempts(clock: FakeClock) -> None:
    calls = 0

    def always_limited() -> str:
        nonlocal calls
        calls += 1
        raise RateLimitedError("429")

    with pytest.raises(RateLimitedError):
        retry_on_429(always_limited, max_attempts=3, base_delay_sec=8.0, sleep=clock.sleep)
    assert calls == 3
    assert clock.slept == [8.0, 16.0]  # 마지막 실패 뒤에는 기다리지 않는다


def test_backoff_counts_toward_the_call_interval(clock: FakeClock) -> None:
    """백오프로 쉰 시간은 호출 간격에도 반영돼야 한다. 백오프 직후 또 잠들면 낭비다."""
    limiter = RateLimiter(6.5, sleep=clock.sleep, monotonic=clock.monotonic)
    attempts = 0

    def flaky() -> str:
        nonlocal attempts
        attempts += 1
        limiter.wait()
        if attempts == 1:
            raise RateLimitedError("429")
        return "ok"

    retry_on_429(flaky, max_attempts=2, base_delay_sec=8.0, limiter=limiter)
    assert clock.slept == [8.0]  # 백오프만. 두 번째 wait() 는 그냥 통과
