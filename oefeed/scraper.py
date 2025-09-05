from __future__ import annotations

from urllib.parse import urljoin, urlparse
import re
import logging
from typing import Iterable

import requests
from bs4 import BeautifulSoup


log = logging.getLogger(__name__)


KEYWORDS = [
    "/blog",
    "/news",
    "/updates",
    "/article",
    "/whitepaper",
    "/post",
]


def is_probably_article_link(base: str, href: str) -> bool:
    try:
        base_host = urlparse(base).netloc
        u = urlparse(href)
    except Exception:
        return False

    # same host or relative
    if u.netloc and u.netloc != base_host:
        return False
    if u.scheme and u.scheme not in ("http", "https"):
        return False
    if not u.path or u.path == "/":
        return False
    if u.path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg', '.pdf', '.zip')):
        return False
    if any(k in u.path.lower() for k in KEYWORDS):
        return True
    # heuristic: path depth >= 2 and not obviously category/listing
    if u.path.count('/') >= 2 and not re.search(r"/page/\\d+|/category/|/tags?/", u.path.lower()):
        return True
    return False


def extract_links_from_site(site_url: str, timeout: int = 15) -> list[str]:
    try:
        r = requests.get(site_url, timeout=timeout, headers={"User-Agent": "oefeed/0.1"})
        r.raise_for_status()
    except Exception as e:
        log.warning("Failed to fetch site %s: %s", site_url, e)
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    candidates: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.startswith("mailto:"):
            continue
        abs_url = urljoin(site_url, href)
        if is_probably_article_link(site_url, abs_url):
            candidates.add(abs_url)
    return list(candidates)

