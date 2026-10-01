"""Live end-to-end test against imot.bg (network required).

Run with:  python -m pytest -m live -s
"""
import datetime as dt
import sqlite3

import pytest

from imoti import pipeline

HOOD = "lozenets"
LIMIT = 20


@pytest.mark.live
def test_scrape_lozenets_20(tmp_path):
    db_path = tmp_path / "imoti_live.db"
    assert pipeline.main(["--hood", HOOD, "--limit", str(LIMIT), "--db", str(db_path)]) == 0

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM latest_listings ORDER BY rank").fetchall()

    print(f"\n{'#':>3} {'listing_id':<18} {'rooms':>5} {'price €':>10} {'m²':>6} {'€/m²':>8}  "
          f"{'last_modified (kind)':<23} date_scraped")
    for r in rows:
        modified = f"{r['last_modified']} ({r['date_kind']})"
        print(f"{r['rank']:>3} {r['listing_id']:<18} {r['rooms']:>5} {r['price_eur'] or '-':>10} "
              f"{r['area_sqm'] or '-':>6} {r['price_per_sqm_eur'] or '-':>8}  {modified:<23} {r['date_scraped']}")

    assert len(rows) == LIMIT
    assert [r["rank"] for r in rows] == list(range(1, LIMIT + 1))
    assert len({r["listing_id"] for r in rows}) == LIMIT
    assert all(r["neighbourhood_slug"] == HOOD and r["neighbourhood_name"] == "Лозенец" for r in rows)
    assert all(r["rooms"] in (2, 3, 4) for r in rows)

    today = dt.date.today()
    for r in rows:
        assert r["last_modified"], f"{r['listing_id']} has no date"
        assert dt.date.fromisoformat(r["last_modified"]) <= today
        assert r["date_kind"] in ("published", "edited")
        assert r["date_scraped"] == today.isoformat()
        assert r["area_sqm"] and 15 <= r["area_sqm"] <= 1000
        if r["price_eur"]:
            # the site rounds €/m² to whole euros
            assert r["price_per_sqm_eur"] == pytest.approx(r["price_eur"] / r["area_sqm"], abs=2)

    run = conn.execute("SELECT status, listings_count FROM runs").fetchone()
    assert tuple(run) == ("done", LIMIT)

    stats = {r["category"]: r for r in conn.execute("SELECT * FROM latest_neighbourhood_stats")}
    print(f"\n{'category':<13} {'rooms':>5} {'count':>6} {'avg €':>9} {'avg €/m²':>9} "
          f"{'median €':>9} {'med €/m²':>9}")
    for r in stats.values():
        print(f"{r['category']:<13} {r['rooms'] or '-':>5} {r['listings_count']:>6} "
              f"{r['avg_price_eur'] or '-':>9} {r['avg_price_per_sqm_eur'] or '-':>9} "
              f"{r['median_price_eur'] or '-':>9} {r['median_price_per_sqm_eur'] or '-':>9}")

    assert set(stats) == {"all", "dvustaen", "tristaen", "chetiristaen"}
    assert stats["all"]["rooms"] is None and stats["tristaen"]["rooms"] == 3
    assert all(r["date_scraped"] == today.isoformat() for r in stats.values())
    # Lozenets is big: every category has listings and figures
    for r in stats.values():
        assert r["listings_count"] > 0
        assert r["avg_price_eur"] and r["median_price_per_sqm_eur"]
    # 'all' covers every property type, so it includes the apartment categories
    assert stats["all"]["listings_count"] >= sum(
        stats[c]["listings_count"] for c in ("dvustaen", "tristaen", "chetiristaen"))
