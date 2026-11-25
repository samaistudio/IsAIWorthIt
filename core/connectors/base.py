"""Connector framework. Every connector is optional and off by default.

A connector reads one source and writes normalised rows into the local company database.
It only ever stores counts, dates, tool names and team names. Names and e-mail addresses
are replaced by a salted hash before anything is written, and no text content is kept.
"""
import hashlib
import json
import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (person TEXT PRIMARY KEY, team TEXT, hourly_cost REAL, source TEXT);
CREATE TABLE IF NOT EXISTS activity (day TEXT, person TEXT, tool TEXT, source TEXT, units REAL, minutes REAL,
                                     task TEXT, corrections INTEGER, PRIMARY KEY (day, person, tool, source, task));
CREATE TABLE IF NOT EXISTS seats (tool TEXT PRIMARY KEY, seats INTEGER, price_eur REAL);
CREATE TABLE IF NOT EXISTS kpi (month TEXT, name TEXT, value REAL, source TEXT, PRIMARY KEY (month, name, source));
CREATE TABLE IF NOT EXISTS survey (month TEXT, team TEXT, hours_week REAL, source TEXT);
CREATE TABLE IF NOT EXISTS sync_log (connector TEXT PRIMARY KEY, at TEXT, ok INTEGER, rows INTEGER, message TEXT);
"""

REGISTRY = {}


def connector(key, label, kind, provides, how, status):
    """Register a connector. status: 'tested' (checked against real data here),
    'docs' (built from the vendor's public docs, not yet run against a live account)."""
    def wrap(fn):
        REGISTRY[key] = {"key": key, "label": label, "kind": kind, "provides": provides, "how": how,
                         "status": status, "run": fn}
        return fn
    return wrap


class Store:
    def __init__(self, path, salt):
        self.con = sqlite3.connect(path)
        self.con.executescript(SCHEMA)
        self.salt = salt

    def pid(self, raw):
        """Stable pseudonym for a person. The raw value (name, e-mail) is never stored."""
        raw = str(raw).strip().lower()
        return hashlib.sha256((self.salt + raw).encode()).hexdigest()[:16] if raw else ""

    def person(self, raw, team=None, hourly_cost=None, source=""):
        p = self.pid(raw)
        self.con.execute("""INSERT INTO people (person, team, hourly_cost, source) VALUES (?,?,?,?)
            ON CONFLICT(person) DO UPDATE SET team = COALESCE(excluded.team, team),
            hourly_cost = COALESCE(excluded.hourly_cost, hourly_cost)""", (p, team, hourly_cost, source))
        return p

    def activity(self, day, person_pid, tool, source, units=1, minutes=None, task="", corrections=0):
        self.con.execute("""INSERT INTO activity VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(day, person, tool, source, task) DO UPDATE SET units = excluded.units,
            minutes = excluded.minutes, corrections = excluded.corrections""",
                         (day, person_pid, tool, source, units, minutes, task, corrections))

    def kpi(self, month, name, value, source):
        self.con.execute("INSERT OR REPLACE INTO kpi VALUES (?,?,?,?)", (month, name, value, source))

    def survey(self, month, team, hours_week, source):
        self.con.execute("INSERT INTO survey VALUES (?,?,?,?)", (month, team, hours_week, source))

    def seats(self, tool, seats, price):
        self.con.execute("INSERT OR REPLACE INTO seats VALUES (?,?,?)", (tool, seats, price))


def secret(cfg, field):
    """Secrets come from environment variables, never from the config file."""
    name = cfg.get(field)
    value = os.environ.get(name or "")
    if not value:
        raise RuntimeError(f"set the environment variable {name} (see README)")
    return value


def http_json(url, headers=None, data=None, method=None):
    import urllib.request
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, body, {"Content-Type": "application/json", **(headers or {})}, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def expand(path):
    return Path(os.path.expanduser(path))
