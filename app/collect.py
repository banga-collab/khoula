"""Recherche: collect signals from the MVP sources and open grants from Open Data Euskadi."""
import re, html, json, datetime as dt, urllib.request, concurrent.futures as cf
import feedparser
from . import db
from .config import GRANTS_URL
from . import settings

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TokiPulse-prototype/0.1",
      "Accept-Language": "es,eu;q=0.9,fr;q=0.8"}
MAX_AGE_DAYS = 30


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def clean(text, n=600):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()[:n]


def _iso(struct):
    try:
        return dt.datetime(*struct[:6]).isoformat()
    except Exception:
        return None


def fetch_rss(src):
    feed = feedparser.parse(_get(src["url"]))
    out = []
    for e in feed.entries[:40]:
        summary = clean(e.get("summary") or e.get("description"))
        out.append({"url": e.get("link"), "title": clean(e.get("title"), 300) or summary[:140],
                    "summary": summary,
                    "published": _iso(e.get("published_parsed") or e.get("updated_parsed"))})
    return out


def fetch_telegram(src):
    page = _get(src["url"]).decode("utf-8", "ignore")
    out = []
    for block in re.findall(r'<div class="tgme_widget_message_wrap.*?</time>', page, re.S):
        link = re.search(r'data-post="([^"]+)"', block)
        text = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', block, re.S)
        when = re.search(r'datetime="([^"]+)"', block)
        if not (link and text):
            continue
        body = clean(text.group(1))
        out.append({"url": "https://t.me/" + link.group(1), "title": body[:140], "summary": body,
                    "published": when.group(1)[:19] if when else None})
    return out


def collect_source(src):
    try:
        items = fetch_telegram(src) if src["kind"] == "telegram" else fetch_rss(src)
    except Exception as e:  # network / parse failure: report and continue
        return src, [], f"{type(e).__name__}: {str(e)[:80]}"
    return src, items, None


def collect_all():
    now = dt.datetime.now()
    cutoff = (now - dt.timedelta(days=settings.get('general')['max_age_days'])).isoformat()
    log, new = [], 0
    with cf.ThreadPoolExecutor(8) as ex:
        for src, items, err in ex.map(collect_source, settings.sources(enabled_only=True)):
            if err:
                log.append({"source": src["name"], "status": "error", "detail": err}); continue
            added = 0
            for it in items:
                if not it["url"] or not it["title"]:
                    continue
                if it["published"] and it["published"] < cutoff:
                    continue
                try:
                    db.execute("""INSERT INTO signals (source_id, source_name, family, credibility, url, title, summary,
                                  lang, published, collected) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                               (src["id"], src["name"], src["family"], src["credibility"], it["url"], it["title"],
                                it["summary"], src["lang"], it["published"] or now.isoformat(), now.isoformat()))
                    added += 1
                except Exception:
                    pass  # duplicate URL
            new += added
            log.append({"source": src["name"], "status": "ok", "fetched": len(items), "new": added})
    log.append({"source": "Open Data Euskadi · aides", **collect_grants()})
    return new, log


def _fix(s):
    try:
        return s.encode("latin-1").decode("utf-8")
    except Exception:
        return s


def collect_grants():
    """Open grants (S59) = opportunities for clients."""
    from .analyze import keyword_domains
    try:
        data = json.loads(_get(GRANTS_URL, 60).decode("latin-1"))
    except Exception as e:
        return {"status": "error", "detail": str(e)[:80]}
    n = 0
    for g in data:
        status = _fix(g.get("procedureStatus", ""))
        if not status.startswith("Abierto"):
            continue
        title = _fix(g.get("documentName", "")).strip()
        dept = _fix(g.get("department", ""))
        doms = keyword_domains(title + " " + dept)
        try:
            db.execute("""INSERT OR REPLACE INTO grants (title, department, start, end, status, url, domains)
                          VALUES (?,?,?,?,?,?,?)""",
                       (title, dept, g.get("procedureStartDate"), g.get("procedureEndDate"), status,
                        g.get("friendlyUrl") or g.get("physicalUrl"), json.dumps(doms)))
            n += 1
        except Exception:
            pass
    return {"status": "ok", "open_grants": n}
