import logging
from dataclasses import dataclass

from . import config
from .detail_parser import parse_detail_page
from .list_parser import ListingStub, SearchStats, parse_list_page, parse_search_stats

log = logging.getLogger(__name__)


@dataclass
class Listing:
    listing_id: str
    neighbourhood_slug: str
    rank: int
    rooms: int
    price_eur: int | None
    area_sqm: float | None
    price_per_sqm_eur: float | None
    last_modified: object  # datetime.date | None
    date_kind: str | None
    url: str


def collect_stubs(client, hood_slug, limit=config.MAX_PER_HOOD):
    """Walk the neighbourhood's result pages and keep the first `limit` 2-4 room apartments.

    Returns (stubs, stats) where stats is the summary box of the first page (all property types).
    """
    kept: list[ListingStub] = []
    seen = set()
    stats = SearchStats(listings_count=0)
    for page in range(1, config.MAX_LIST_PAGES + 1):
        path = f"{config.CITY_PATH}/{hood_slug}" + (f"/p-{page}" if page > 1 else "")
        html = client.get(path)
        if html is None:
            break
        if page == 1:
            stats = parse_search_stats(html)
        stubs, total = parse_list_page(html)
        if not stubs:
            break
        for stub in stubs:
            if stub.rooms is None or stub.listing_id in seen:
                continue
            seen.add(stub.listing_id)
            kept.append(stub)
            if len(kept) >= limit:
                return kept, stats
        if total is not None and page * 40 >= total:
            break
    return kept, stats


def collect_category_stats(client, hood_slug, all_stats):
    """Return {category: SearchStats} for 'all' property types and each apartment type."""
    by_category = {"all": all_stats}
    for type_slug in config.ROOM_TYPES:
        html = client.get(f"{config.CITY_PATH}/{hood_slug}/{type_slug}")
        by_category[type_slug] = parse_search_stats(html) if html else SearchStats(listings_count=0)
    return by_category


def scrape_neighbourhood(client, hood_slug, limit=config.MAX_PER_HOOD):
    """Return (listings, {category: SearchStats}) for one neighbourhood."""
    stubs, all_stats = collect_stubs(client, hood_slug, limit)
    log.info("%s: %d apartments on list pages", hood_slug, len(stubs))
    stats = collect_category_stats(client, hood_slug, all_stats)

    listings = []
    for rank, stub in enumerate(stubs, start=1):
        html = client.get(stub.url)
        detail = parse_detail_page(html) if html else None
        if detail is None:
            log.warning("%s: detail page missing for %s", hood_slug, stub.listing_id)

        price = (detail and detail.price_eur) or stub.price_eur
        area = (detail and detail.area_sqm) or stub.area_sqm
        price_m2 = detail.price_per_sqm_eur if detail else None
        if price_m2 is None and price and area:
            price_m2 = round(price / area, 2)

        listings.append(Listing(
            listing_id=stub.listing_id,
            neighbourhood_slug=hood_slug,
            rank=rank,
            rooms=stub.rooms,
            price_eur=price,
            area_sqm=area,
            price_per_sqm_eur=price_m2,
            last_modified=detail.last_modified if detail else None,
            date_kind=detail.date_kind if detail else None,
            url=stub.url,
        ))
    return listings, stats
