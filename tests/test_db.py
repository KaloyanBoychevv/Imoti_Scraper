import datetime as dt

from imoti import db
from imoti.list_parser import SearchStats
from imoti.scraper import Listing


def make_listing(price):
    return Listing(
        listing_id="1b178705536086742", neighbourhood_slug="lozenets", rank=1, rooms=2,
        price_eur=price, area_sqm=65.0, price_per_sqm_eur=round(price / 65.0),
        last_modified=dt.date(2026, 9, 28), date_kind="edited",
        url="https://www.imot.bg/obiava-1b178705536086742",
    )


def test_same_listing_across_runs_keeps_history(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.upsert_neighbourhoods(conn, [("lozenets", "Лозенец")])

    for price in (230000, 225000):
        run_id = db.start_run(conn)
        db.insert_listings(conn, run_id, [make_listing(price)])
        db.finish_run(conn, run_id, "done")

    history = conn.execute(
        "SELECT run_id, date_scraped, price_eur FROM listings "
        "WHERE listing_id = '1b178705536086742' ORDER BY run_id"
    ).fetchall()
    today = dt.date.today().isoformat()
    assert history == [(1, today, 230000), (2, today, 225000)]

    # latest_listings only shows the most recent run
    assert conn.execute("SELECT price_eur FROM latest_listings").fetchall() == [(225000,)]


def test_insert_stats(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.upsert_neighbourhoods(conn, [("lozenets", "Лозенец")])
    run_id = db.start_run(conn)
    db.insert_stats(conn, run_id, "lozenets", {
        "all": SearchStats(754, 667426, 3889, 464367, 3720),
        "chetiristaen": SearchStats(0),
    })
    db.finish_run(conn, run_id, "done")

    rows = conn.execute(
        "SELECT category, rooms, listings_count, avg_price_eur, median_price_per_sqm_eur, "
        "neighbourhood_name FROM latest_neighbourhood_stats ORDER BY category"
    ).fetchall()
    assert rows == [
        ("all", None, 754, 667426, 3720, "Лозенец"),
        ("chetiristaen", 4, 0, None, None, "Лозенец"),
    ]
