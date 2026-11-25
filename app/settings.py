"""Admin-editable settings stored in SQLite; config.py values are the defaults."""
import json, copy
from . import db, config

DEFAULTS = {
    "sources": [{**s, "enabled": True} for s in config.SOURCES],
    "keywords": config.KEYWORDS,
    "weights": config.PRIORITY_WEIGHTS,
    "services": config.SERVICES,
    "general": {"auto_collect_hours": 0, "max_age_days": 30, "cluster_threshold": 0.22, "org_name": "TokiPulse",
                "ai_engine": "auto", "gemini_model": "gemini-2.5-flash"},
}
_cache = {}


def _ensure():
    db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")


def get(key):
    if key in _cache:
        return _cache[key]
    _ensure()
    row = db.one("SELECT value FROM settings WHERE key=?", (key,))
    val = json.loads(row["value"]) if row else copy.deepcopy(DEFAULTS[key])
    if key == "general":  # fill new defaults
        val = {**DEFAULTS["general"], **val}
    _cache[key] = val
    return val


def put(key, value):
    _ensure()
    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, json.dumps(value, ensure_ascii=False)))
    _cache.pop(key, None)
    if key == "keywords":
        from . import analyze
        analyze.reload_keywords()


def reset(key):
    _ensure()
    db.execute("DELETE FROM settings WHERE key=?", (key,))
    _cache.pop(key, None)
    if key == "keywords":
        from . import analyze
        analyze.reload_keywords()


def sources(enabled_only=False):
    s = get("sources")
    return [x for x in s if x.get("enabled", True)] if enabled_only else s
