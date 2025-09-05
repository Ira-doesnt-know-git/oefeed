import argparse
from pathlib import Path

from oefeed.cli import CLI


def main():
    parser = argparse.ArgumentParser(description="OEFeed - article feed scraper/teaser server")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Initialize DB and load sites from config")
    sub.add_parser("index", help="Index sites: discover and store known URLs")

    p_scrape = sub.add_parser("scrape_new", help="Fetch new articles, save content, and generate teasers")
    p_scrape.add_argument("--limit", type=int, default=10, help="Max new articles to process this run")

    p_serve = sub.add_parser("serve", help="Run the web UI and scheduler")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=5000)
    p_serve.add_argument("--interval-days", type=int, default=3, help="Rescrape interval in days")

    p_debug = sub.add_parser("debug_generate_all", help="[DEBUG] Generate teasers for ALL indexed links (ignore new/diff)")
    p_debug.add_argument("--limit", type=int, default=None, help="Limit total URLs per site (optional)")
    p_debug.add_argument("--overwrite", action="store_true", help="Overwrite existing article content/teasers")

    args = parser.parse_args()

    data_dir = Path.cwd() / "data"
    data_dir.mkdir(exist_ok=True)

    cli = CLI(db_path=data_dir / "oefeed.db")

    if args.cmd == "init":
        cli.init()
    elif args.cmd == "index":
        cli.index()
    elif args.cmd == "scrape_new":
        cli.scrape_new(limit=args.limit)
    elif args.cmd == "serve":
        cli.serve(host=args.host, port=args.port, interval_days=args.interval_days)
    elif args.cmd == "debug_generate_all":
        cli.debug_generate_all(limit=args.limit, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
