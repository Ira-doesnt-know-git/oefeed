import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Optional
import time


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS sites (
  id INTEGER PRIMARY KEY,
  url TEXT NOT NULL UNIQUE,
  name TEXT,
  last_indexed_at INTEGER
);

CREATE TABLE IF NOT EXISTS known_urls (
  id INTEGER PRIMARY KEY,
  site_id INTEGER NOT NULL,
  url TEXT NOT NULL UNIQUE,
  first_seen INTEGER NOT NULL,
  last_seen INTEGER NOT NULL,
  FOREIGN KEY(site_id) REFERENCES sites(id)
);

CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY,
  site_id INTEGER NOT NULL,
  url TEXT NOT NULL UNIQUE,
  title TEXT,
  content TEXT,
  teaser TEXT,
  created_at INTEGER NOT NULL,
  FOREIGN KEY(site_id) REFERENCES sites(id)
);
"""


class DB:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as con:
            con.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            yield con
        finally:
            con.commit()
            con.close()

    def add_sites(self, sites: Iterable[tuple[str, Optional[str]]]):
        now = int(time.time())
        with self._conn() as con:
            for url, name in sites:
                con.execute(
                    "INSERT OR IGNORE INTO sites(url, name, last_indexed_at) VALUES(?,?,?)",
                    (url, name, None),
                )

    def list_sites(self) -> list[sqlite3.Row]:
        with self._conn() as con:
            cur = con.execute("SELECT * FROM sites ORDER BY id")
            return cur.fetchall()

    def upsert_known_urls(self, site_id: int, urls: list[str]) -> tuple[int, int]:
        now = int(time.time())
        new_count = 0
        total = 0
        with self._conn() as con:
            for url in urls:
                total += 1
                try:
                    con.execute(
                        "INSERT INTO known_urls(site_id, url, first_seen, last_seen) VALUES(?,?,?,?)",
                        (site_id, url, now, now),
                    )
                    new_count += 1
                except sqlite3.IntegrityError:
                    con.execute(
                        "UPDATE known_urls SET last_seen=? WHERE url=?",
                        (now, url),
                    )
        return new_count, total

    def get_new_known_urls(self, site_id: int, limit: int = 50) -> list[str]:
        with self._conn() as con:
            cur = con.execute(
                """
                SELECT ku.url
                FROM known_urls ku
                LEFT JOIN articles a ON a.url = ku.url
                WHERE ku.site_id = ? AND a.id IS NULL
                ORDER BY ku.first_seen DESC
                LIMIT ?
                """,
                (site_id, limit),
            )
            return [r[0] for r in cur.fetchall()]

    def insert_article(self, site_id: int, url: str, title: str | None, content: str | None, teaser: str | None):
        with self._conn() as con:
            con.execute(
                "INSERT OR IGNORE INTO articles(site_id, url, title, content, teaser, created_at) VALUES(?,?,?,?,?,?)",
                (site_id, url, title, content, teaser, int(time.time())),
            )

    def list_articles(self, limit: int = 100) -> list[sqlite3.Row]:
        with self._conn() as con:
            cur = con.execute(
                "SELECT a.*, s.name AS site_name, s.url AS site_url FROM articles a JOIN sites s ON s.id = a.site_id ORDER BY a.created_at DESC LIMIT ?",
                (limit,),
            )
            return cur.fetchall()

    def get_all_known_urls(self, site_id: int, limit: int | None = None) -> list[str]:
        with self._conn() as con:
            sql = "SELECT url FROM known_urls WHERE site_id = ? ORDER BY first_seen DESC"
            params: tuple = (site_id,)
            if limit is not None:
                sql += " LIMIT ?"
                params = (site_id, limit)
            cur = con.execute(sql, params)
            return [r[0] for r in cur.fetchall()]

    def upsert_article(self, site_id: int, url: str, title: str | None, content: str | None, teaser: str | None, overwrite: bool = False):
        now = int(time.time())
        with self._conn() as con:
            if overwrite:
                con.execute(
                    """
                    INSERT INTO articles(site_id, url, title, content, teaser, created_at)
                    VALUES(?,?,?,?,?,?)
                    ON CONFLICT(url) DO UPDATE SET
                      site_id=excluded.site_id,
                      title=excluded.title,
                      content=excluded.content,
                      teaser=excluded.teaser,
                      created_at=excluded.created_at
                    """,
                    (site_id, url, title, content, teaser, now),
                )
            else:
                con.execute(
                    """
                    INSERT INTO articles(site_id, url, title, content, teaser, created_at)
                    VALUES(?,?,?,?,?,?)
                    ON CONFLICT(url) DO UPDATE SET
                      teaser=COALESCE(articles.teaser, excluded.teaser)
                    """,
                    (site_id, url, title, content, teaser, now),
                )
