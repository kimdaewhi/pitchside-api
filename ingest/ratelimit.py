"""레이트리밋과 재시도.

football-data.org 무료 티어는 분당 10회다.
전체 1회 = 5리그 x (standings + matches) = 10콜이라 한도에 딱 붙는다.
따라서 병렬 호출은 금지하고, 호출 사이에 최소 간격을 강제한다.

여기서는 429 만 재시도한다. 타임아웃이나 5xx 는 재시도하지 않고 그대로 올려서
해당 리그를 실패로 기록하고 다음 리그로 넘어가게 한다 — 한 리그를 붙잡고 늘어지면
뒤에 남은 리그들이 분당 한도 안에 못 들어온다.
"""

import logging
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


class RateLimitedError(Exception):
    """429 응답.

    ``retry_after_sec`` 는 Retry-After 헤더에서 읽은 값이다. 서버가 알려준 대기 시간이
    계산한 백오프보다 길면 서버 쪽을 따른다.
    """

    def __init__(self, message: str, *, retry_after_sec: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_sec = retry_after_sec


class RateLimiter:
    """호출 사이 최소 간격을 보장한다.

    프로세스 하나에서 순차 호출하는 것을 전제로 한다. 스레드 안전을 노리지 않는다.
    ``sleep`` / ``monotonic`` 을 주입할 수 있게 열어둔 건 테스트에서 실제로 잠들지
    않게 하기 위해서다.
    """

    def __init__(
        self,
        min_interval_sec: float = 6.5,
        *,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._min_interval_sec = min_interval_sec
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_call_at: float | None = None

    def wait(self) -> None:
        """직전 호출로부터 min_interval_sec 이 지날 때까지 잠든다.

        첫 호출은 기다리지 않는다. 반환 직전에 호출 시각을 갱신하므로
        "요청을 보내기 직전"이 기준점이 된다.
        """
        now = self._monotonic()
        if self._last_call_at is not None:
            remaining = self._min_interval_sec - (now - self._last_call_at)
            if remaining > 0:
                logger.debug("레이트리밋 대기 %.2fs", remaining)
                self._sleep(remaining)
                now = self._monotonic()
        self._last_call_at = now

    def pause(self, seconds: float) -> None:
        """외부 사정(429 백오프)으로 강제로 쉰다.

        마지막 호출 시각은 일부러 갱신하지 않는다. 그래야 다음 ``wait()`` 이
        "마지막 요청으로부터 얼마나 지났나"를 기준으로 남은 시간만 계산하고,
        백오프로 이미 쉰 시간만큼 덜 잔다. 갱신해 버리면 8초 쉬고 또 6.5초를 잔다.
        """
        if seconds > 0:
            self._sleep(seconds)


def retry_on_429[T](
    fn: Callable[[], T],
    *,
    max_attempts: int = 4,
    base_delay_sec: float = 8.0,
    limiter: RateLimiter | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """429 를 만나면 지수 백오프 후 재시도한다.

    대기 시간은 ``base_delay_sec * 2 ** n`` 이고, 서버가 Retry-After 를 주면
    둘 중 긴 쪽을 쓴다. max_attempts 를 소진하면 마지막 예외를 그대로 올린다 —
    호출한 쪽(run.py)이 그 리그를 실패로 기록하고 다음 리그로 넘어간다.

    ``limiter`` 를 넘기면 백오프 시간을 호출 간격 계산에도 반영한다.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts 는 1 이상이어야 한다")

    for attempt in range(max_attempts):
        try:
            return fn()
        except RateLimitedError as exc:
            is_last = attempt == max_attempts - 1
            if is_last:
                logger.warning("429 재시도 %d 회 모두 실패", max_attempts)
                raise
            delay = base_delay_sec * (2**attempt)
            if exc.retry_after_sec is not None:
                delay = max(delay, exc.retry_after_sec)
            logger.warning(
                "429 수신. %.1fs 후 재시도 (%d/%d)", delay, attempt + 2, max_attempts
            )
            if limiter is not None:
                limiter.pause(delay)
            else:
                sleep(delay)

    # 도달하지 않는다. 위 루프는 반환하거나 예외를 올린다.
    raise AssertionError("unreachable")
