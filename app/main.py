"""FastAPI 앱.

요청 경로에서 외부 API 를 호출하지 않는다. 이 앱은 DB 만 읽는다.
응답이 비어 있다면 아직 수집되지 않은 것이지 프록시할 대상이 아니다.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.routers import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """기동/종료 훅.

    스케줄러를 띄우지 않는다. 수집은 외부 cron 이 ``python -m ingest`` 를 부른다.
    """
    settings = get_settings()
    if not settings.database_path.exists():
        # 막지는 않는다. 빈 응답과 "DB 가 아예 없음"을 로그에서 구분할 수 있게만 한다.
        print(f"[warn] DB 파일이 없습니다: {settings.database_path} — python -m app.db.init_db")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Pitchside API",
        description="유럽 5대 리그 순위 / 일정·결과 / 팀 / 상대전적",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(api_router)
    return app


app = create_app()
