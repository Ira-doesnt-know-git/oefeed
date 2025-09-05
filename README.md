OEFeed — Minimal Article Scraper + Teaser Feed

Overview

OEFeed scrapes a predefined list of websites, tracks discovered URLs, fetches new articles (via Playwright when available), asks a local LLM (OpenAI-compatible) to generate short teasers, and presents them in a simple web UI.

Quickstart

- Python 3.10+
- Local LLM: OpenAI-compatible API at http://localhost:8080

1) Install dependencies

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium

2) Configure sites (optional)

Edit `config/sites.json` to your liking. Defaults are meant to overridden.

3) Initialize DB and index URLs

    python main.py init
    python main.py index

4) Fetch new articles and generate teasers with optional limit

    python main.py scrape_new --limit 10

5) Run the web UI (with background rescrape every N days)

    python main.py serve --port 5000 --interval-days 3

Then open http://127.0.0.1:5000

Debug: Force-generate on all indexed links

- Generate teasers for all known URLs, ignoring the "new diff".
- Use `--overwrite` to re-fetch and replace existing content/teasers.

    python main.py debug_generate_all --limit 50 --overwrite

Environment Variables

- `LLM_BASE_URL` (default: http://localhost:8080)
- `LLM_MODEL` (default: Qwen3-30B-A3B-Instruct)

Notes

- Indexing uses simple heuristics to detect article-like links; you can refine `oefeed/scraper.py` for your sources.
- Full-page fetching prefers Playwright; falls back to requests+BeautifulSoup.
- Data is stored in SQLite at `data/oefeed.db`.
- Only non-reasoning models are supported since I cba to clean reasoning tags.
