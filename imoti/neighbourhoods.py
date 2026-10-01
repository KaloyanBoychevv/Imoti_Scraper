import re

from bs4 import BeautifulSoup

from . import config

_HOOD_HREF = re.compile(re.escape(config.CITY_PATH) + r"/([a-z0-9-]+)$")


def parse_neighbourhoods(html):
    """Return [(slug, name_bg)] from the Sofia sales page.

    Neighbourhood links look like
    <nobr><a href="//www.imot.bg/obiavi/prodazhbi/grad-sofiya/lozenets">
    <span>Имоти Лозенец</span> <n>(757)</n></a></nobr>
    """
    soup = BeautifulSoup(html, "html.parser")
    hoods = {}
    for a in soup.select("nobr > a[href]"):
        m = _HOOD_HREF.search(a["href"])
        if not m or re.fullmatch(r"p-\d+", m.group(1)):
            continue
        name = a.span.get_text(strip=True) if a.span else a.get_text(strip=True)
        hoods[m.group(1)] = re.sub(r"^Имоти\s+", "", name)
    return sorted(hoods.items())


def fetch_neighbourhoods(client):
    return parse_neighbourhoods(client.get(config.CITY_PATH))
