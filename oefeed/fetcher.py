from __future__ import annotations

import logging
from typing import Tuple

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


def fetch_with_playwright(url: str, timeout_ms: int = 20000) -> Tuple[str | None, str | None]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None, None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_navigation_timeout(timeout_ms)
            page.goto(url)
            title = page.title()
            content = page.content()
            browser.close()
            # extract text from HTML content using BeautifulSoup for consistency
            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text("\n", strip=True)
            return title, text
    except Exception as e:
        log.warning("Playwright fetch failed for %s: %s", url, e)
        return None, None


def fetch_with_requests(url: str, timeout: int = 20) -> Tuple[str | None, str | None]:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "oefeed/0.1"})
        r.raise_for_status()
    except Exception as e:
        log.warning("Requests fetch failed for %s: %s", url, e)
        return None, None
    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    text = soup.get_text("\n", strip=True)
    return title, text


def fetch_full_text(url: str) -> Tuple[str | None, str | None]:
    title, text = fetch_with_playwright(url)
    if text:
        return title, text
    return fetch_with_requests(url)

