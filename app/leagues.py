"""리그 레지스트리.

리그 추가는 코드 수정이 아니라 이 파일의 ``LEAGUES`` 항목 추가로 끝나야 한다.
다른 모듈에 ``if code == "PL"`` 같은 리그별 분기를 두지 않는다.

프레임워크를 import 하지 않는다. 수집 배치가 FastAPI 없이 이 모듈을 그대로 쓴다.
404 로 바꾸는 어댑터는 ``app/routers/deps.py`` 에 있다.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class League:
    """대상 리그 하나.

    code
        라우팅 키. 숫자 id가 아니라 competition code 를 URL 에 쓴다.
    external_id
        football-data.org 의 competition id. 외부 호출에만 쓰고 URL 에는 노출하지 않는다.
    """

    code: str
    external_id: int
    name: str
    country: str


LEAGUES: tuple[League, ...] = (
    League("PL", 2021, "Premier League", "England"),
    League("PD", 2014, "La Liga", "Spain"),
    League("FL1", 2015, "Ligue 1", "France"),
    League("SA", 2019, "Serie A", "Italy"),
    League("BL1", 2002, "Bundesliga", "Germany"),
)

LEAGUES_BY_CODE: dict[str, League] = {league.code: league for league in LEAGUES}


def get_league(code: str) -> League:
    """code 로 리그를 찾는다. 없으면 ``LookupError``.

    HTTP 를 모르는 계층(services / ingest)에서 쓴다.
    """
    try:
        return LEAGUES_BY_CODE[code.upper()]
    except KeyError as exc:
        raise LookupError(f"unknown competition code: {code}") from exc
