"""레이트리밋과 재시도.

football-data.org 무료 티어는 분당 10회다.
전체 1회 = 5리그 x (standings + matches) = 10콜이라 한도에 딱 붙는다.
따라서 병렬 호출은 금지하고, 호출 사이에 최소 간격을 강제한다.
"""

from collections.abc import Callable


class RateLimiter:
    """호출 사이 최소 간격을 보장한다.

    프로세스 하나에서 순차 호출하는 것을 전제로 한다. 스레드 안전을 노리지 않는다.
    """

    def __init__(self, min_interval_sec: float = 6.5) -> None:
        self._min_interval_sec = min_interval_sec
        self._last_call_at: float | None = None

    def wait(self) -> None:
        """직전 호출로부터 min_interval_sec 이 지날 때까지 잠든다."""
        raise NotImplementedError  # TODO: time.monotonic() 비교 후 time.sleep


def retry_on_429[T](
    fn: Callable[[], T],
    *,
    max_attempts: int = 4,
    base_delay_sec: float = 8.0,
) -> T:
    """429 를 만나면 지수 백오프 후 재시도한다.

    max_attempts 를 소진하면 마지막 예외를 그대로 올린다.
    호출한 쪽(run.py)이 그 리그를 실패로 기록하고 다음 리그로 넘어간다.
    """
    raise NotImplementedError  # TODO: 429 판별 → base_delay * 2**n 대기 → 재시도
