"""HTTP 계층.

라우터는 파라미터 검증과 응답 모델 선언까지만 한다. SQL 을 직접 쓰지 않는다.
"""

from fastapi import APIRouter

from app.routers import competitions, head_to_head, health, matches, teams

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(competitions.router)
api_router.include_router(matches.router)
api_router.include_router(teams.router)
api_router.include_router(head_to_head.router)

__all__ = ["api_router"]
