"""TokiPulse API + dashboard. Run: python -m uvicorn app.main:app --port 8600"""
import json, pathlib, threading, datetime as dt
from typing import Any
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from . import db, collect, analyze, settings, sessions as sess_mod
from .config import DOMAINS, TERRITORIES

STATIC = pathlib.Path(__file__).resolve().parent.parent / "static"

# Optional local secrets file: tokipulse/.env with lines like GEMINI_API_KEY=...  (never commit it)
_ENV = STATIC.parent / ".env"
if _ENV.exists():
    import os
    for _line in _ENV.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))
import os, hmac
from fastapi import Request
from fastapi.responses import JSONResponse

app = FastAPI(title="TokiPulse")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


@app.middleware("http")
async def admin_guard(request: Request, call_next):
    """Admin changes need the ADMIN_PASSWORD (header X-Admin-Token). Without a password set:
    open locally, read-only when deployed."""
    p = request.url.path
    if (p.startswith("/api/admin") and request.method != "GET" and p != "/api/admin/login") or p == "/api/admin/activity":
        if ADMIN_PASSWORD:
            if not hmac.compare_digest(request.headers.get("x-admin-token", ""), ADMIN_PASSWORD):
                return JSONResponse({"detail": "Admin password required."}, status_code=401)
        elif db.ON_VERCEL:
            return JSONResponse({"detail": "Admin is read-only: set ADMIN_PASSWORD in the Vercel project settings."},
                                status_code=403)
    return await call_next(request)


@app.post("/api/admin/login")
def admin_login(body: dict = Body(...)):
    if not ADMIN_PASSWORD:
        return {"ok": not db.ON_VERCEL, "open": not db.ON_VERCEL}
    if hmac.compare_digest(str(body.get("password", "")), ADMIN_PASSWORD):
        return {"ok": True}
    raise HTTPException(401, "Wrong password.")
_lock = threading.Lock()
STATE = {"running": False, "last": None, "log": []}


def run_pipeline():
    if not _lock.acquire(blocking=False):
        return
    STATE["running"] = True
    try:
        started = dt.datetime.now().isoformat()
        new, log = collect.collect_all()
        n, engine = analyze.analyse_pending(2000)
        log.append({"source": "Analyse", "status": "ok", "analysed": n, "engine": engine})
        STATE.update(last=dt.datetime.now().isoformat(), log=log)
        db.execute("INSERT INTO runs (started, finished, log) VALUES (?,?,?)", (started, STATE["last"], db.dumps(log)))
    finally:
        STATE["running"] = False
        _lock.release()


def _load_state():
    db.init()
    last = db.one("SELECT finished, log FROM runs ORDER BY id DESC LIMIT 1")
    if last:
        STATE.update(last=last["finished"], log=json.loads(last["log"]))


if db.ON_VERCEL:  # serverless: no lifespan events or background threads
    _load_state()


@app.on_event("startup")
def startup():
    _load_state()
    if db.ON_VERCEL:
        return
    threading.Thread(target=_bootstrap, daemon=True).start()
    threading.Thread(target=_scheduler, daemon=True).start()


def _scheduler():
    """Auto-collection every N hours (Admin > General). 0 = manual only."""
    import time
    while True:
        time.sleep(60)
        hours = settings.get("general").get("auto_collect_hours") or 0
        if hours and not STATE["running"]:
            last = STATE.get("last")
            if not last or dt.datetime.now() - dt.datetime.fromisoformat(last) >= dt.timedelta(hours=hours):
                run_pipeline()


def _bootstrap():
    if not db.one("SELECT id FROM signals LIMIT 1"):
        run_pipeline()
    sess_mod.seed_examples()


# ---------------------------------------------------------------- meta & stats
@app.get("/api/meta")
def meta():
    return {"domains": DOMAINS, "territories": TERRITORIES, "ai": analyze.ai_enabled(), "engine": analyze.engine(),
            "keys": {"claude": analyze.claude_available(), "gemini": __import__("app.gemini", fromlist=["x"]).available()},
            "sources": settings.sources(), "services": settings.get("services"), "state": STATE}


@app.get("/api/stats")
def stats():
    week = (dt.datetime.now() - dt.timedelta(days=7)).isoformat()
    by_dom = {r["domain"]: r["n"] for r in db.rows(
        "SELECT domain, COUNT(*) n FROM signals WHERE relevant=1 GROUP BY domain")}
    by_terr = {r["territory"]: r["n"] for r in db.rows(
        "SELECT territory, COUNT(*) n FROM signals WHERE relevant=1 GROUP BY territory")}
    by_kind = {r["kind"]: r["n"] for r in db.rows(
        "SELECT kind, COUNT(*) n FROM topics WHERE n_signals>0 GROUP BY kind")}
    return {
        "signals": db.one("SELECT COUNT(*) n FROM signals")["n"],
        "relevant": db.one("SELECT COUNT(*) n FROM signals WHERE relevant=1")["n"],
        "signals_week": db.one("SELECT COUNT(*) n FROM signals WHERE relevant=1 AND published>=?", (week,))["n"],
        "topics": db.one("SELECT COUNT(*) n FROM topics WHERE n_signals>0")["n"],
        "high_priority": db.one("SELECT COUNT(*) n FROM topics WHERE n_signals>0 AND priority>=4")["n"],
        "watch": db.one("SELECT COUNT(*) n FROM topics WHERE watch=1")["n"],
        "feedback": db.one("SELECT COUNT(*) n FROM feedback")["n"],
        "grants": db.one("SELECT COUNT(*) n FROM grants")["n"],
        "sessions": db.one("SELECT COUNT(*) n FROM sessions")["n"],
        "by_domain": by_dom, "by_territory": by_terr, "by_kind": by_kind,
    }


# ---------------------------------------------------------------- topics & signals
def _flags(tid):
    return [r["label"] for r in db.rows("SELECT DISTINCT label FROM feedback WHERE target='topic' AND target_id=?",
                                        (tid,))]


@app.get("/api/topics")
def topics(domain: str = "", territory: str = "", kind: str = "", q: str = "", watch: int = 0, limit: int = 60):
    sql = "SELECT * FROM topics WHERE n_signals>0"
    args = []
    for col, val in (("domain", domain), ("territory", territory), ("kind", kind)):
        if val:
            sql += f" AND {col}=?"; args.append(val)
    if watch:
        sql += " AND watch=1"
    if q:
        sql += " AND (label LIKE ? OR id IN (SELECT topic_id FROM signals WHERE title LIKE ?))"
        args += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY watch DESC, score DESC, updated DESC LIMIT ?"
    args.append(limit)
    out = db.rows(sql, args)
    for t in out:
        t.pop("tokens", None)
        t["sources"] = [r["source_name"] for r in db.rows(
            "SELECT DISTINCT source_name FROM signals WHERE topic_id=? AND relevant=1 LIMIT 4", (t["id"],))]
        t["flags"] = _flags(t["id"])
    return out


@app.get("/api/topics/{tid}")
def topic(tid: int):
    t = db.one("SELECT * FROM topics WHERE id=?", (tid,))
    if not t:
        raise HTTPException(404)
    t.pop("tokens", None)
    t["criteria"] = analyze.topic_criteria(tid)
    t["signals"] = db.rows("""SELECT id, source_name, family, url, title, summary, ai_summary, published, territory,
                              municipality, importance, impact, urgency, analysed_by FROM signals
                              WHERE topic_id=? AND relevant=1 ORDER BY published DESC""", (tid,))
    t["flags"] = _flags(tid)
    t["grants"] = sess_mod.grant_candidates([t["domain"]], analyze.tokens(t["label"]), limit=3)
    return t


@app.get("/api/signals")
def signals(domain: str = "", limit: int = 50):
    sql = "SELECT * FROM signals WHERE relevant=1" + (" AND domain=?" if domain else "") + \
          " ORDER BY published DESC LIMIT ?"
    return db.rows(sql, ([domain] if domain else []) + [limit])


class Feedback(BaseModel):
    target: str  # topic | signal | opportunity
    target_id: int
    label: str
    note: str | None = None


@app.post("/api/feedback")
def feedback(f: Feedback):
    db.execute("INSERT INTO feedback (target, target_id, label, note, created) VALUES (?,?,?,?,?)",
               (f.target, f.target_id, f.label, f.note, dt.datetime.now().isoformat()))
    if f.target == "topic":
        if f.label == "Watch":
            db.execute("UPDATE topics SET watch=1 WHERE id=?", (f.target_id,))
        if f.label in ("Not relevant", "Duplicate"):
            db.execute("UPDATE signals SET relevant=0 WHERE topic_id=?", (f.target_id,))
    if f.target == "signal" and f.label in ("Not relevant", "Duplicate"):
        db.execute("UPDATE signals SET relevant=0 WHERE id=?", (f.target_id,))
    analyze.recompute_topics()
    return {"ok": True}


# ---------------------------------------------------------------- pipeline
@app.post("/api/collect")
def trigger():
    if STATE["running"]:
        return {"running": True}
    if db.ON_VERCEL:  # a function is frozen after it responds: collect within the request
        run_pipeline()
        return {"running": False, "last": STATE["last"]}
    threading.Thread(target=run_pipeline, daemon=True).start()
    return {"running": True}


# ---------------------------------------------------------------- sessions
class SessionIn(BaseModel):
    client: str
    territory: str | None = None
    municipality: str | None = None
    date: str | None = None
    participants: str | None = None
    notes: str


@app.get("/api/sessions")
def list_sessions():
    out = db.rows("SELECT * FROM sessions ORDER BY date DESC, id DESC")
    for s in out:
        s["analysis"] = json.loads(s["analysis"]) if s["analysis"] else None
    return out


@app.post("/api/sessions")
def new_session(s: SessionIn):
    if len(s.notes.strip()) < 40:
        raise HTTPException(400, "Notes too short (40 characters minimum).")
    sid = sess_mod.create_session(s.model_dump())
    return list_sessions_one(sid)


@app.post("/api/sessions/{sid}/reanalyse")
def reanalyse(sid: int):
    sess_mod.analyse_session(sid)
    return list_sessions_one(sid)


def list_sessions_one(sid):
    s = db.one("SELECT * FROM sessions WHERE id=?", (sid,))
    s["analysis"] = json.loads(s["analysis"]) if s["analysis"] else None
    return s


# ---------------------------------------------------------------- opportunities
@app.get("/api/opportunities")
def opportunities():
    client_opps, firm_opps = [], []
    for s in list_sessions():
        a = s["analysis"] or {}
        for o in a.get("client_opportunities", []):
            client_opps.append({**o, "client": s["client"], "session_id": s["id"]})
        for o in a.get("firm_opportunities", []):
            firm_opps.append({**o, "client": s["client"], "session_id": s["id"]})
    grants = db.rows("SELECT * FROM grants ORDER BY end")
    for g in grants:
        g["domains"] = json.loads(g["domains"] or "[]")
    return {"client": client_opps, "firm": firm_opps, "grants": grants}


# ---------------------------------------------------------------- weekly report
@app.get("/api/report")
def report():
    week = (dt.datetime.now() - dt.timedelta(days=7)).isoformat()
    excluded = {r["target_id"] for r in db.rows("SELECT target_id FROM feedback WHERE target='topic' AND label='To verify'")}
    tops = [t for t in topics(limit=200) if t["id"] not in excluded]
    recent = [t for t in tops if (t["updated"] or "") >= week]
    pick = lambda kind: [t for t in recent if t["kind"] == kind][:5]
    sess = [s for s in list_sessions() if (s["date"] or "") >= (dt.date.today() - dt.timedelta(days=30)).isoformat()]
    opp = opportunities()
    by_dom = {}
    for t in recent:
        by_dom[t["domain"]] = by_dom.get(t["domain"], 0) + t["n_signals"]
    lead = max(by_dom, key=by_dom.get) if by_dom else None
    conclusions = []
    if lead:
        conclusions.append(f"The most active domain this week is \"{DOMAINS[lead]['label']}\" "
                           f"({by_dom[lead]} signals).")
    probs = pick("Territorial issue to study") + pick("Recurring concern")
    if probs:
        conclusions.append(f"{len(probs)} recurring topic(s) deserve an in-depth analysis, led by "
                           f"\"{probs[0]['label'][:90]}\".")
    session_doms = {}
    for s in sess:
        for i in (s["analysis"] or {}).get("issues", []):
            session_doms[i["domain"]] = session_doms.get(i["domain"], 0) + 1
    both = [d for d in session_doms if d in by_dom]
    if both:
        conclusions.append("Listening sessions and the radar converge on: "
                           + ", ".join(DOMAINS[d]["label"] for d in both) + ".")
    return {
        "period": {"from": week[:10], "to": dt.date.today().isoformat()},
        "kpis": stats(),
        "top": recent[:8],
        "problems": pick("Territorial issue to study"),
        "recurring": pick("Recurring concern"),
        "emerging": pick("Emerging trend"),
        "watch": [t for t in tops if t["watch"]][:8],
        "sessions": [{"client": s["client"], "date": s["date"], "summary": (s["analysis"] or {}).get("summary")}
                     for s in sess],
        "conclusions": conclusions,
        "recommendations": [r for s in sess for r in (s["analysis"] or {}).get("recommendations", [])][:6],
        "client_opportunities": opp["client"][:6], "firm_opportunities": opp["firm"][:6],
        "engine": analyze.engine() or "heuristic",
        "charts": chart_data(),
    }


def chart_data():
    today = dt.date.today()
    days = [(today - dt.timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    daily = {r["d"]: r["n"] for r in db.rows(
        "SELECT substr(published,1,10) d, COUNT(*) n FROM signals WHERE relevant=1 GROUP BY d")}
    return {
        "by_domain": [{"key": c, "label": DOMAINS[c]["label"], "value": db.one(
            "SELECT COUNT(*) n FROM signals WHERE relevant=1 AND domain=?", (c,))["n"]} for c in DOMAINS],
        "by_territory": [{"label": r["territory"], "value": r["n"]} for r in db.rows(
            "SELECT territory, COUNT(*) n FROM signals WHERE relevant=1 GROUP BY territory ORDER BY n DESC")],
        "by_kind": [{"label": k, "value": db.one("SELECT COUNT(*) n FROM topics WHERE n_signals>0 AND kind=?",
                                                 (k,))["n"]}
                    for k in ("Territorial issue to study", "Recurring concern", "Emerging trend",
                              "One-off information")],
        "by_priority": [{"label": f"P{p}", "value": db.one(
            "SELECT COUNT(*) n FROM topics WHERE n_signals>0 AND priority=?", (p,))["n"]} for p in range(1, 6)],
        "by_family": [{"label": r["family"], "value": r["n"]} for r in db.rows(
            "SELECT family, COUNT(*) n FROM signals WHERE relevant=1 GROUP BY family ORDER BY n DESC")],
        "daily": [{"label": d, "value": daily.get(d, 0)} for d in days],
    }


@app.get("/api/report/data.csv")
def report_csv():
    import csv, io
    from fastapi.responses import Response
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["topic_id", "label", "domain", "territory", "kind", "priority", "score", "signals", "sources",
                "last_update", "watch"])
    for t in topics(limit=1000):
        w.writerow([t["id"], t["label"], DOMAINS.get(t["domain"], {}).get("label", t["domain"]), t["territory"],
                    t["kind"], t["priority"], t["score"], t["n_signals"], t["n_sources"], t["updated"], t["watch"]])
    return Response(buf.getvalue().encode("utf-8-sig"), media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=tokipulse-topics-{dt.date.today()}.csv"})


# ---------------------------------------------------------------- admin
EDITABLE = ("sources", "keywords", "weights", "services", "general")


@app.get("/api/admin/overview")
def admin_overview():
    count = lambda t, w="": db.one(f"SELECT COUNT(*) n FROM {t} {w}")["n"]
    return {"signals": count("signals"), "relevant": count("signals", "WHERE relevant=1"),
            "topics": count("topics", "WHERE n_signals>0"), "sessions": count("sessions"),
            "grants": count("grants"), "feedback": count("feedback"), "runs": count("runs"),
            "sources_enabled": len(settings.sources(True)), "sources_total": len(settings.sources()),
            "ai": analyze.ai_enabled(), "engine": analyze.engine(), "state": STATE, "db_path": str(db.DB_PATH)}


@app.get("/api/admin/settings/{key}")
def admin_get(key: str):
    if key not in EDITABLE:
        raise HTTPException(404)
    return settings.get(key)


@app.put("/api/admin/settings/{key}")
def admin_put(key: str, value: Any = Body(...)):
    if key not in EDITABLE:
        raise HTTPException(404)
    if key == "weights":
        total = sum(float(v) for v in value.values())
        if abs(total - 1) > 0.011:
            raise HTTPException(400, f"Weights must add up to 100% (currently {total:.0%}).")
    if key == "sources":
        ids = set()
        for s in value:
            if not all(s.get(k) for k in ("id", "name", "url", "kind")):
                raise HTTPException(400, "Each source needs an id, a name, a URL and a type.")
            if s["id"] in ids:
                raise HTTPException(400, f"Duplicate source id {s['id']}.")
            ids.add(s["id"])
            s["credibility"] = max(1, min(5, int(s.get("credibility") or 3)))
    if key == "services":
        for sv in value:
            if not sv.get("name") or not sv.get("domains"):
                raise HTTPException(400, "Each service needs a name and at least one domain.")
    settings.put(key, value)
    if key == "weights":
        analyze.recompute_topics()
    return {"ok": True, "value": settings.get(key)}


@app.post("/api/admin/settings/{key}/reset")
def admin_reset(key: str):
    if key not in EDITABLE:
        raise HTTPException(404)
    settings.reset(key)
    if key == "weights":
        analyze.recompute_topics()
    return {"ok": True, "value": settings.get(key)}


@app.post("/api/admin/reanalyse")
def admin_reanalyse():
    """Re-run classification and clustering on all signals with the current keywords and settings."""
    db.execute("DELETE FROM topics")
    db.execute("UPDATE signals SET analysed_by=NULL, topic_id=NULL, relevant=1")
    n, engine = analyze.analyse_pending(5000)
    return {"ok": True, "analysed": n, "engine": engine}


@app.delete("/api/admin/sessions/{sid}")
def admin_del_session(sid: int):
    db.execute("DELETE FROM sessions WHERE id=?", (sid,))
    return {"ok": True}


@app.delete("/api/admin/topics/{tid}")
def admin_del_topic(tid: int):
    db.execute("UPDATE signals SET relevant=0 WHERE topic_id=?", (tid,))
    db.execute("DELETE FROM topics WHERE id=?", (tid,))
    return {"ok": True}


@app.delete("/api/admin/feedback/{fid}")
def admin_del_feedback(fid: int):
    db.execute("DELETE FROM feedback WHERE id=?", (fid,))
    analyze.recompute_topics()
    return {"ok": True}


@app.get("/api/admin/activity")
def admin_activity():
    fb = db.rows("SELECT * FROM feedback ORDER BY id DESC LIMIT 200")
    for f in fb:
        t = db.one("SELECT label FROM topics WHERE id=?", (f["target_id"],)) if f["target"] == "topic" else             db.one("SELECT title AS label FROM signals WHERE id=?", (f["target_id"],))
        f["target_label"] = t["label"] if t else "(deleted)"
    runs = db.rows("SELECT * FROM runs ORDER BY id DESC LIMIT 30")
    for r in runs:
        r["log"] = json.loads(r["log"] or "[]")
    return {"feedback": fb, "runs": runs}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
