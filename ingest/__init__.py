"""수집 배치.

FastAPI 앱과 독립적으로 실행된다. ``app.db.connection`` 과 ``app.leagues`` 만 공유하고
``app.main`` / ``app.routers`` / ``app.services`` 는 import 하지 않는다.
외부 API 클라이언트와 레이트리밋은 이 패키지 안에만 존재한다.
"""
