"""리그 레지스트리 무결성."""

import pytest

from app.leagues import LEAGUES, LEAGUES_BY_CODE, get_league


def test_five_leagues_registered() -> None:
    assert len(LEAGUES) == 5


def test_codes_and_ids_are_unique() -> None:
    assert len({lg.code for lg in LEAGUES}) == len(LEAGUES)
    assert len({lg.external_id for lg in LEAGUES}) == len(LEAGUES)
    assert set(LEAGUES_BY_CODE) == {lg.code for lg in LEAGUES}


def test_lookup_is_case_insensitive() -> None:
    assert get_league("pl") is get_league("PL")


def test_unknown_code_raises() -> None:
    with pytest.raises(LookupError):
        get_league("XX")
