"""라우터 공통 의존성.

리그 조회를 HTTP 예외로 옮기는 얇은 어댑터. 이 변환은 HTTP 계층의 일이므로
``app/leagues.py`` 는 프레임워크를 모른 채로 남는다 (수집 배치가 그대로 재사용한다).
"""

from fastapi import HTTPException

from app.leagues import League, get_league


def require_league(code: str) -> League:
    """없는 코드면 404."""
    try:
        return get_league(code)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"unknown competition code: {code}") from None
