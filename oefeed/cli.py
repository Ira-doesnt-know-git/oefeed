from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

from apscheduler.schedulers.background import BackgroundScheduler

from .db import DB
from .scraper import extract_links_from_site
from .fetcher import fetch_full_text
from .teaser import generate_teaser
from .web import create_app


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


DEFAULT_SITES = [
    ("https://openai.com/blog", "OpenAI Blog"),
    ("https://research.google/blog/", "Google Research Blog"),
    ("https://engineering.fb.com/", "Meta Engineering"),
]


class CLI:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db = DB(self.db_path)

    def _load_sites_config(self) -> list[tuple[str, str | None]]:
        cfg_path = Path("config/sites.json")
        if cfg_path.exists():
            try:
                data = json.loads(cfg_path.read_text())
                sites = [(item["url"], item.get("name")) for item in data]
                if sites:
                    return sites
            except Exception:
                pass
        return DEFAULT_SITES

    def init(self):
        sites = self._load_sites_config()
        self.db.add_sites(sites)
        log.info("Initialized DB. Loaded %d site(s).", len(sites))
        log.info("You can edit config/sites.json to customize sites.")

    def index(self):
        sites = self.db.list_sites()
        if not sites:
            log.warning("No sites configured. Run: python main.py init")
            return
        for s in sites:
            log.info("Indexing %s", s["url"])
            links = extract_links_from_site(s["url"]) or []
            new_count, total = self.db.upsert_known_urls(s["id"], links)
            log.info("Found %d links (%d new)", total, new_count)

    def scrape_new(self, limit: int = 10):
        sites = self.db.list_sites()
        if not sites:
            log.warning("No sites configured. Run: python main.py init")
            return
        for s in sites:
            to_process = self.db.get_new_known_urls(s["id"], limit=limit)
            if not to_process:
                log.info("No new URLs for %s", s["url"])
                continue
            log.info("Processing %d new URLs for %s", len(to_process), s["url"])
            for url in to_process:
                title, text = fetch_full_text(url)
                if not text:
                    log.info("Skip (no text): %s", url)
                    continue
                teaser = generate_teaser(text, title=title) or None
                self.db.insert_article(s["id"], url, title, text, teaser)
                log.info("Saved article: %s", url)

    def serve(self, host: str = "127.0.0.1", port: int = 5000, interval_days: int = 3):
        app = create_app(self.db_path)

        scheduler = BackgroundScheduler()

        def job():
            try:
                log.info("[Job] Indexing + scraping new articles...")
                self.index()
                self.scrape_new(limit=10)
            except Exception as e:
                log.exception("Scheduled job failed: %s", e)

        scheduler.add_job(job, "interval", days=max(1, interval_days), id="rescrape")
        scheduler.start()

        try:
            app.run(host=host, port=port, debug=False)
        finally:
            scheduler.shutdown(wait=False)

    def debug_generate_all(self, limit: int | None = None, overwrite: bool = True):
        """Force-generate teasers for ALL indexed links (ignores new/old).

        - If overwrite=True, re-fetch and replace existing article content/teasers.
        - If overwrite=False, only fills in missing entries/teasers.
        """
        sites = self.db.list_sites()
        if not sites:
            log.warning("No sites configured. Run: python main.py init")
            return
        for s in sites:
            urls = self.db.get_all_known_urls(s["id"], limit=limit)
            if not urls:
                log.info("No indexed URLs for %s", s["url"])
                continue
            log.info("[DEBUG] Regenerating %d URL(s) for %s (overwrite=%s)", len(urls), s["url"], overwrite)
            for url in urls:
                title, text = fetch_full_text(url)
                if not text:
                    log.info("Skip (no text): %s", url)
                    continue
                teaser = generate_teaser(text, title=title) or None
                self.db.upsert_article(s["id"], url, title, text, teaser, overwrite=overwrite)
                log.info("Upserted article: %s", url)
