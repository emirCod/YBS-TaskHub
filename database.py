import sqlite3
from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect("taskhub.db")
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()

    with current_app.open_resource("models.sql") as file:
        db.executescript(file.read().decode("utf-8"))


def init_app(app):
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()