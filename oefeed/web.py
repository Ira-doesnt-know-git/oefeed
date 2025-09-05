from __future__ import annotations

from flask import Flask, render_template
from pathlib import Path

from .db import DB


def create_app(db_path: Path) -> Flask:
    app = Flask(__name__, template_folder=str((Path(__file__).parent.parent / "templates").resolve()))
    db = DB(db_path)

    @app.route("/")
    def index():
        articles = db.list_articles(limit=200)
        return render_template("index.html", articles=articles)

    return app

