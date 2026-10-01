import datetime as dt
from pathlib import Path

from imoti.detail_parser import parse_date, parse_detail_page
from imoti.list_parser import SearchStats, parse_list_page, parse_price, parse_search_stats
from imoti.neighbourhoods import parse_neighbourhoods

FIXTURES = Path(__file__).parent / "fixtures"


def read(name):
    return (FIXTURES / name).read_bytes().decode("cp1251", errors="replace")


def test_neighbourhoods():
    hoods = dict(parse_neighbourhoods(read("city_sofiya.html")))
    assert len(hoods) > 150
    assert hoods["lozenets"] == "Лозенец"
    assert hoods["mladost-1"] == "Младост 1"
    # property-type and pagination slugs must not leak in
    assert not {"ednostaen", "dvustaen", "kashta", "ofis", "p-2"} & hoods.keys()


def test_list_page():
    stubs, total = parse_list_page(read("list_lozenets.html"))
    assert total == 754
    assert len(stubs) == 40
    first = stubs[0]
    assert first.listing_id == "1a179076912258458"
    assert first.type_slug == "ednostaen" and first.rooms is None
    assert first.price_eur == 164900 and first.area_sqm == 51.0
    two_room = next(s for s in stubs if s.type_slug == "dvustaen")
    assert two_room.rooms == 2


def test_search_stats_all_types():
    s = parse_search_stats(read("list_lozenets.html"))
    assert s == SearchStats(754, 667426, 3889, 464367, 3720)


def test_search_stats_room_type():
    s = parse_search_stats(read("list_lozenets_dvustaen.html"))
    assert s == SearchStats(102, 315895, 4099, 298660, 4129)


def test_search_stats_no_results():
    assert parse_search_stats(read("list_empty.html")) == SearchStats(0)


def test_detail_page():
    d = parse_detail_page(read("detail_1a179076912258458.html"))
    assert d.last_modified == dt.date(2026, 9, 30)
    assert d.date_kind == "published"
    assert d.price_eur == 164900
    assert d.price_per_sqm_eur == 3233.0
    assert d.area_sqm == 51.0


def test_parse_date_edited():
    assert parse_date("Коригирана в 09:05 на 3 март, 2025 год.") == (dt.date(2025, 3, 3), "edited")
    assert parse_date("нищо") == (None, None)


def test_parse_price():
    assert parse_price("1 250 000 €") == 1250000
    assert parse_price("При запитване") is None
