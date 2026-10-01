import datetime as dt
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

from .list_parser import parse_price

MONTHS_BG = {
    "януари": 1, "февруари": 2, "март": 3, "април": 4, "май": 5, "юни": 6,
    "юли": 7, "август": 8, "септември": 9, "октомври": 10, "ноември": 11, "декември": 12,
}

# "Публикувана в 14:52 на 30 септември, 2026 год." / "Коригирана в ..."
_DATE_RE = re.compile(
    r"(Публикувана|Коригирана)\s+в\s+\d{1,2}:\d{2}\s+на\s+(\d{1,2})\s+([а-я]+),?\s+(\d{4})",
    re.IGNORECASE,
)
_M2_RE = re.compile(r"([\d\s.,]+)\s*€\s*/\s*m")
_AREA_RE = re.compile(r"Площ:\s*([\d.,]+)\s*m")


@dataclass
class ListingDetail:
    last_modified: dt.date | None
    date_kind: str | None  # 'published' | 'edited'
    price_eur: int | None
    price_per_sqm_eur: float | None
    area_sqm: float | None


def parse_date(text):
    m = _DATE_RE.search(text or "")
    if not m:
        return None, None
    kind_bg, day, month_bg, year = m.groups()
    month = MONTHS_BG.get(month_bg.lower())
    if not month:
        return None, None
    kind = "edited" if kind_bg.lower().startswith("коригирана") else "published"
    return dt.date(int(year), month, int(day)), kind


def parse_detail_page(html):
    soup = BeautifulSoup(html, "html.parser")

    last_modified, kind = parse_date(soup.get_text(" "))

    price_per_sqm = None
    m2_div = soup.select_one("div.m2")
    if m2_div:
        m = _M2_RE.search(m2_div.get_text(""))
        if m:
            digits = re.sub(r"\s", "", m.group(1)).replace(",", ".")
            price_per_sqm = float(digits) if digits else None

    price = None
    price_div = soup.select_one("div.price")
    if price_div:
        price = parse_price(price_div.get_text(" ", strip=True))

    area = None
    params = soup.select_one("div.adParams")
    if params:
        m = _AREA_RE.search(params.get_text(" ", strip=True))
        if m:
            area = float(m.group(1).replace(",", "."))

    return ListingDetail(last_modified, kind, price, price_per_sqm, area)
