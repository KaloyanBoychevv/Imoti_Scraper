import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

from . import config

_URL_RE = re.compile(r"obiava-([0-9a-z]+)-prodava-([a-z]+)-")
_AREA_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*кв\.м")
_TOTAL_RE = re.compile(r"от общо\s*([\d\s]+?)\s*обяв")


@dataclass
class ListingStub:
    listing_id: str
    url: str
    type_slug: str
    rooms: int | None
    price_eur: int | None
    area_sqm: float | None


@dataclass
class SearchStats:
    listings_count: int
    avg_price_eur: int | None = None
    avg_price_per_sqm_eur: int | None = None
    median_price_eur: int | None = None
    median_price_per_sqm_eur: int | None = None


def parse_search_stats(html):
    """Parse the summary box of a results page.

    It holds two <div class="params2"> blocks, one labelled 'средно аритметично' (mean)
    and one 'медианна стойност' (median), each with
    'Средна цена на имотите в извадката: <strong>667 426 euro</strong>' and
    'Средна цена на кв.м: <strong>3 889 euro</strong>'.
    Pages with no results ('Няма намерени обяви') have no such blocks.
    """
    soup = BeautifulSoup(html, "html.parser")
    m = _TOTAL_RE.search(soup.get_text(" "))
    stats = SearchStats(listings_count=int(re.sub(r"\s", "", m.group(1))) if m else 0)
    for block in soup.select("div.params2"):
        values = [_to_int(s.get_text()) for s in block.find_all("strong")]
        if len(values) < 2:
            continue
        label = block.get_text(" ").lower()
        if "аритметично" in label:
            stats.avg_price_eur, stats.avg_price_per_sqm_eur = values[:2]
        elif "медианна" in label:
            stats.median_price_eur, stats.median_price_per_sqm_eur = values[:2]
    return stats


def _to_int(text):
    digits = re.sub(r"\D", "", text or "")
    return int(digits) if digits else None


def parse_price(text):
    """'164 900 €' -> 164900; anything non-numeric (e.g. 'При запитване') -> None."""
    if not text or "€" not in text:
        return None
    digits = re.sub(r"\D", "", text.split("€")[0])
    return int(digits) if digits else None


def parse_area(text):
    m = _AREA_RE.search(text or "")
    return float(m.group(1).replace(",", ".")) if m else None


def parse_list_page(html):
    """Return ([ListingStub], total_count) for a search results page."""
    soup = BeautifulSoup(html, "html.parser")
    stubs = []
    for item in soup.select("div.item[id^=ida]"):
        link = item.select_one("a.title[href]") or item.select_one("a[href*=obiava-]")
        m = _URL_RE.search(link["href"]) if link else None
        if not m:
            continue
        listing_id, type_slug = m.groups()
        url = link["href"].split("#")[0]
        if url.startswith("//"):
            url = "https:" + url
        price_div = item.select_one("div.price")
        info_div = item.select_one("div.info")
        stubs.append(ListingStub(
            listing_id=listing_id,
            url=url,
            type_slug=type_slug,
            rooms=config.ROOM_TYPES.get(type_slug),
            price_eur=parse_price(price_div.get_text(" ", strip=True) if price_div else None),
            area_sqm=parse_area(info_div.get_text(" ", strip=True) if info_div else None),
        ))

    m = _TOTAL_RE.search(soup.get_text(" "))
    total = int(re.sub(r"\s", "", m.group(1))) if m else None
    return stubs, total
