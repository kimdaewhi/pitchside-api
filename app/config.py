"""애플리케이션 설정.

값의 출처는 환경변수 하나뿐이다. API 키는 코드에 두지 않는다.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """환경변수로 주입되는 런타임 설정."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 외부 API — 수집 배치에서만 쓴다. 요청 경로는 이 값을 건드리지 않는다.
    football_data_api_key: str = ""
    football_data_base_url: str = "https://api.football-data.org/v4"
    football_data_timeout_sec: float = 10.0

    # SQLite
    database_path: Path = PROJECT_ROOT / "data" / "pitchside.db"
    sqlite_busy_timeout_ms: int = 5000

    # 수집 레이트리밋 — 분당 10회 제한이라 호출 사이 6~7초를 둔다.
    ingest_min_interval_sec: float = 6.5
    ingest_max_retries: int = 4
    ingest_retry_base_delay_sec: float = 8.0


@lru_cache
def get_settings() -> Settings:
    """프로세스 수명 동안 재사용되는 Settings 싱글턴."""
    return Settings()
