import datetime as dt
import sqlite3

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS neighbourhoods (
    slug    TEXT PRIMARY KEY,
    name_bg TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    run_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at     TEXT NOT NULL,
    finished_at    TEXT,
    status         TEXT NOT NULL,          -- running | done | failed
    listings_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS listings (
    run_id             INTEGER NOT NULL REFERENCES runs(run_id),
    listing_id         TEXT NOT NULL,
    neighbourhood_slug TEXT NOT NULL REFERENCES neighbourhoods(slug),
    rank               INTEGER NOT NULL,   -- position 1..100 within the neighbourhood
    rooms              INTEGER NOT NULL,   -- 2, 3 or 4 (двустаен/тристаен/четиристаен)
    price_eur          INTEGER,
    area_sqm           REAL,
    price_per_sqm_eur  REAL,
    last_modified      TEXT,               -- ISO date of last publish/edit
    date_kind          TEXT,               -- published | edited
    url                TEXT NOT NULL,
    date_scraped       TEXT NOT NULL,      -- ISO date this row was scraped
    PRIMARY KEY (run_id, listing_id, neighbourhood_slug)
);

CREATE INDEX IF NOT EXISTS ix_listings_listing ON listings(listing_id, date_scraped);

-- Summary box shown on each results page, per neighbourhood and category
CREATE TABLE IF NOT EXISTS neighbourhood_stats (
    run_id                   INTEGER NOT NULL REFERENCES runs(run_id),
    neighbourhood_slug       TEXT NOT NULL REFERENCES neighbourhoods(slug),
    category                 TEXT NOT NULL,  -- all | dvustaen | tristaen | chetiristaen
    rooms                    INTEGER,        -- 2, 3, 4; NULL for 'all' (every property type)
    listings_count           INTEGER NOT NULL,
    avg_price_eur            INTEGER,        -- arithmetic mean
    avg_price_per_sqm_eur    INTEGER,
    median_price_eur         INTEGER,
    median_price_per_sqm_eur INTEGER,
    date_scraped             TEXT NOT NULL,
    PRIMARY KEY (run_id, neighbourhood_slug, category)
);

CREATE VIEW IF NOT EXISTS latest_neighbourhood_stats AS
SELECT s.*, n.name_bg AS neighbourhood_name
FROM neighbourhood_stats s
JOIN neighbourhoods n ON n.slug = s.neighbourhood_slug
WHERE s.run_id = (SELECT MAX(run_id) FROM runs WHERE status = 'done');

CREATE VIEW IF NOT EXISTS latest_listings AS
SELECT l.*, n.name_bg AS neighbourhood_name
FROM listings l
JOIN neighbourhoods n ON n.slug = l.neighbourhood_slug
WHERE l.run_id = (SELECT MAX(run_id) FROM runs WHERE status = 'done');
"""


def _now():
    return dt.datetime.now().isoformat(timespec="seconds")


def connect(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def start_run(conn):
    cur = conn.execute("INSERT INTO runs (started_at, status) VALUES (?, 'running')", (_now(),))
    conn.commit()
    return cur.lastrowid


def finish_run(conn, run_id, status):
    count = conn.execute("SELECT COUNT(*) FROM listings WHERE run_id = ?", (run_id,)).fetchone()[0]
    conn.execute(
        "UPDATE runs SET finished_at = ?, status = ?, listings_count = ? WHERE run_id = ?",
        (_now(), status, count, run_id),
    )
    conn.commit()


def upsert_neighbourhoods(conn, hoods):
    with conn:
        conn.executemany(
            "INSERT INTO neighbourhoods (slug, name_bg) VALUES (?, ?) "
            "ON CONFLICT(slug) DO UPDATE SET name_bg = excluded.name_bg",
            hoods,
        )


def insert_stats(conn, run_id, hood_slug, stats_by_category):
    today = dt.date.today().isoformat()
    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO neighbourhood_stats (run_id, neighbourhood_slug, category, rooms, "
            "listings_count, avg_price_eur, avg_price_per_sqm_eur, median_price_eur, "
            "median_price_per_sqm_eur, date_scraped) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (run_id, hood_slug, category, config.ROOM_TYPES.get(category), s.listings_count,
                 s.avg_price_eur, s.avg_price_per_sqm_eur, s.median_price_eur,
                 s.median_price_per_sqm_eur, today)
                for category, s in stats_by_category.items()
            ],
        )


def insert_listings(conn, run_id, listings):
    today = dt.date.today().isoformat()
    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO listings (run_id, listing_id, neighbourhood_slug, rank, rooms, "
            "price_eur, area_sqm, price_per_sqm_eur, last_modified, date_kind, url, date_scraped) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (run_id, l.listing_id, l.neighbourhood_slug, l.rank, l.rooms, l.price_eur,
                 l.area_sqm, l.price_per_sqm_eur,
                 l.last_modified.isoformat() if l.last_modified else None,
                 l.date_kind, l.url, today)
                for l in listings
            ],
        )
