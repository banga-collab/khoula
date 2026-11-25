import sqlite3, json, pathlib, os, shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
ON_VERCEL = bool(os.environ.get("VERCEL"))
# Vercel functions can only write to /tmp (ephemeral): start each instance from the bundled snapshot.
DB_PATH = pathlib.Path("/tmp/tokipulse.db") if ON_VERCEL else ROOT / "data" / "tokipulse.db"
SEED_PATH = ROOT / "data" / "seed.db"


def prepare():
    if not DB_PATH.exists() and SEED_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(SEED_PATH, DB_PATH)

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT, source_name TEXT, family TEXT, credibility INTEGER,
  url TEXT UNIQUE, title TEXT, summary TEXT, lang TEXT, published TEXT, collected TEXT,
  domain TEXT, secondary TEXT, territory TEXT, municipality TEXT,
  importance INTEGER, impact INTEGER, urgency INTEGER,
  topic_id INTEGER, analysed_by TEXT, relevant INTEGER DEFAULT 1, ai_summary TEXT
);
CREATE TABLE IF NOT EXISTS topics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  label TEXT, domain TEXT, territory TEXT, created TEXT, updated TEXT,
  kind TEXT, priority INTEGER, score REAL, n_signals INTEGER, n_sources INTEGER,
  watch INTEGER DEFAULT 0, tokens TEXT
);
CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  target TEXT, target_id INTEGER, label TEXT, note TEXT, created TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client TEXT, territory TEXT, municipality TEXT, date TEXT, participants TEXT,
  notes TEXT, analysis TEXT, analysed_by TEXT, created TEXT, example INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS grants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT, department TEXT, start TEXT, end TEXT, status TEXT, url TEXT UNIQUE,
  domains TEXT
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, started TEXT, finished TEXT, log TEXT
);
"""


def conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def init():
    prepare()
    with conn() as c:
        c.executescript(SCHEMA)


def rows(sql, args=()):
    with conn() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def one(sql, args=()):
    r = rows(sql, args)
    return r[0] if r else None


def execute(sql, args=()):
    with conn() as c:
        cur = c.execute(sql, args)
        return cur.lastrowid


def dumps(x):
    return json.dumps(x, ensure_ascii=False)
