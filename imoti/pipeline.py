"""Weekly entry point: python -m imoti.pipeline [--hood SLUG ...] [--limit N]"""
import argparse
import datetime as dt
import logging
import sys
from pathlib import Path

from . import config, db
from .http_client import HttpClient
from .neighbourhoods import fetch_neighbourhoods
from .scraper import scrape_neighbourhood

log = logging.getLogger("imoti")


def setup_logging():
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logfile = config.LOG_DIR / f"run_{dt.date.today():%Y%m%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(logfile, encoding="utf-8"), logging.StreamHandler()],
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scrape Sofia 2-4 room apartments from imot.bg")
    parser.add_argument("--hood", action="append", help="only these neighbourhood slugs (repeatable)")
    parser.add_argument("--limit", type=int, default=config.MAX_PER_HOOD, help="listings per neighbourhood")
    parser.add_argument("--db", default=str(config.DB_PATH), help="SQLite file path")
    args = parser.parse_args(argv)

    setup_logging()
    conn = db.connect(Path(args.db))
    client = HttpClient()

    hoods = fetch_neighbourhoods(client)
    log.info("Found %d neighbourhoods", len(hoods))
    db.upsert_neighbourhoods(conn, hoods)
    if args.hood:
        hoods = [h for h in hoods if h[0] in set(args.hood)]

    run_id = db.start_run(conn)
    failed = []
    try:
        for i, (slug, name) in enumerate(hoods, start=1):
            try:
                listings, stats = scrape_neighbourhood(client, slug, args.limit)
                db.insert_listings(conn, run_id, listings)
                db.insert_stats(conn, run_id, slug, stats)
                log.info("[%d/%d] %s (%s): saved %d listings", i, len(hoods), slug, name, len(listings))
            except Exception:
                log.exception("Neighbourhood %s failed", slug)
                failed.append(slug)
    except BaseException:
        db.finish_run(conn, run_id, "failed")
        raise

    status = "failed" if failed and len(failed) == len(hoods) else "done"
    db.finish_run(conn, run_id, status)
    log.info("Run %d %s; failed neighbourhoods: %s", run_id, status, failed or "none")
    return 0 if status == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
