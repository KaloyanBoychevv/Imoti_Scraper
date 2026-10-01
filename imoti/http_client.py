import logging
import random
import time

import requests

from . import config

log = logging.getLogger(__name__)


class HttpClient:
    """requests.Session wrapper with rate limiting, retries and cp1251 decoding."""

    def __init__(self, delay_min=config.DELAY_MIN, delay_max=config.DELAY_MAX):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept-Language": "bg,en;q=0.8",
        })
        self.delay_min = delay_min
        self.delay_max = delay_max
        self._last_request = 0.0

    def _wait(self):
        delay = random.uniform(self.delay_min, self.delay_max)
        elapsed = time.monotonic() - self._last_request
        if elapsed < delay:
            time.sleep(delay - elapsed)

    def get(self, url):
        """Return the decoded page text, or None for a 404."""
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = config.BASE_URL + url

        for attempt in range(1, config.RETRIES + 1):
            self._wait()
            self._last_request = time.monotonic()
            try:
                resp = self.session.get(url, timeout=config.TIMEOUT)
            except requests.RequestException as exc:
                log.warning("GET %s failed (%s), attempt %d", url, exc, attempt)
            else:
                if resp.status_code == 404:
                    return None
                if resp.status_code == 200:
                    return resp.content.decode(config.ENCODING, errors="replace")
                log.warning("GET %s -> HTTP %d, attempt %d", url, resp.status_code, attempt)
            time.sleep(5 * 2 ** (attempt - 1))
        raise RuntimeError(f"Giving up on {url}")
