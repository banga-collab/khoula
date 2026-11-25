"""Listening + Analysis: classify signals, score priority, cluster into topics.

Two engines:
- Claude (claude-haiku-5-5) when ANTHROPIC_API_KEY is set — structured outputs, batch of signals per call.
- Heuristic fallback (keywords from the Source Radar 'Keywords' sheet) so the prototype runs without a key.
"""
import os, re, json, unicodedata, datetime as dt
from typing import Literal, Optional
from pydantic import BaseModel, Field
from . import db, settings
from .config import DOMAINS, PLACES, IMPACT_WORDS, URGENCY_WORDS, NOISE_WORDS

TRIAGE_MODEL = "claude-haiku-5-5"
ANALYST_MODEL = "claude-opus-5-5"


def claude_available():
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def engine():
    """Active AI engine: 'claude', 'gemini' or None (heuristic). Chosen in Admin > General."""
    from . import gemini
    choice = settings.get("general").get("ai_engine", "auto")
    if choice == "heuristic":
        return None
    if choice == "claude":
        return "claude" if claude_available() else None
    if choice == "gemini":
        return "gemini" if gemini.available() else None
    return "claude" if claude_available() else "gemini" if gemini.available() else None


def ai_enabled():
    return engine() is not None


def ai_json(system, user, model_cls, claude_model, max_tokens=8000, analyst=False):
    """One structured-output call to the active engine; returns a validated pydantic instance."""
    if engine() == "gemini":
        from . import gemini
        model = settings.get("general").get("gemini_model") or "gemini-2.5-flash"
        return gemini.generate_json(system, user, model_cls, model)
    if analyst:  # Opus: server-side fallback on refusals, high effort
        resp = client().beta.messages.parse(
            model=claude_model, max_tokens=max_tokens, system=system,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default", output_config={"effort": "high"},
            messages=[{"role": "user", "content": user}], output_format=model_cls)
    else:
        resp = client().messages.parse(model=claude_model, max_tokens=max_tokens, system=system,
                                       messages=[{"role": "user", "content": user}], output_format=model_cls)
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        raise RuntimeError("no structured output")
    return resp.parsed_output


_client = None


def client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


# ---------------------------------------------------------------- text helpers
def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(ch for ch in s if not unicodedata.combining(ch))


_KW = {}


def reload_keywords():
    _KW.clear()
    _KW.update({code: [norm(k.strip()) for k in words.split(",") if k.strip()]
                for code, words in settings.get("keywords").items()})
_IMPACT = [norm(w) for w in IMPACT_WORDS]
_URGENT = [norm(w) for w in URGENCY_WORDS]
_PLACES = {terr: [norm(p) for p in names] for terr, names in PLACES.items()}
STOP = set(norm(w) for w in """para como esta este estos estas sobre entre desde hasta tras pero porque cuando donde
también tiene tienen será sido han hay más menos muy todo todos todas otra otro otros nueva nuevo años año
según ante bajo contra durante mediante sino eta baina bere dute izan egin dira dela duela edo beste behar
ditu zuen dago daude baita gaur bihar atzo urte hori honek horiek dans pour avec sans sont leur leurs mais
cette entre plus the and with from that this have will euskadi bizkaia gipuzkoa araba navarra vasco vasca""".split())


def tokens(text):
    return {w for w in re.findall(r"[a-z0-9ñ]{4,}", norm(text)) if w not in STOP}


def _hits(text, words):
    """Count keywords present at a word start (prefix match keeps stems like 'inmobiliari' working)."""
    t = " " + norm(text) + " "
    return sum(1 for w in words if w and re.search(r"(?<![a-z0-9])" + re.escape(w), t))


_NOISE = [norm(w) for w in NOISE_WORDS]


def keyword_domains(text):
    if not _KW:
        reload_keywords()
    scores = {c: _hits(text, ws) for c, ws in _KW.items()}
    return [c for c, s in sorted(scores.items(), key=lambda x: -x[1]) if s > 0]


def detect_place(text):
    t = " " + norm(text) + " "
    for terr, names in _PLACES.items():
        for n in names:
            if re.search(r"[^a-z]" + re.escape(n) + r"[^a-z]", t):
                return terr, n.title()
    return None, None


# ---------------------------------------------------------------- feedback memory
def source_adjustments():
    """+0.1 per 'Relevant', -0.1 per 'Not relevant' on a source's signals (Scoring sheet, section D)."""
    adj = {}
    for r in db.rows("""SELECT s.source_id, f.label FROM feedback f JOIN signals s
                        ON f.target='signal' AND f.target_id=s.id"""):
        d = 0.1 if r["label"] == "Relevant" else -0.1 if r["label"] == "Not relevant" else 0
        adj[r["source_id"]] = adj.get(r["source_id"], 0) + d
    return adj


def feedback_examples(limit=12):
    return db.rows("""SELECT s.title, s.domain, f.label FROM feedback f JOIN signals s
                      ON f.target='signal' AND f.target_id=s.id
                      WHERE f.label IN ('Relevant','Not relevant') ORDER BY f.id DESC LIMIT ?""", (limit,))


# ---------------------------------------------------------------- classification
class SignalAnalysis(BaseModel):
    id: int
    relevant: bool = Field(description="True if it concerns a territorial issue or resident need in one of the domains")
    domain: Literal["HOU", "ECO", "PAR", "DEV", "TS", "CUL"]
    secondary: list[Literal["HOU", "ECO", "PAR", "DEV", "TS", "CUL"]]
    territory: Literal["Bizkaia", "Gipuzkoa", "Araba", "Navarre", "Euskadi", "Iparralde", "Other"]
    municipality: Optional[str]
    importance: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    urgency: int = Field(ge=1, le=5)
    summary: str = Field(description="One sentence in English")
    topic_label: str = Field(description="Short generic topic label in English, 3-7 words, reusable across articles")


class Batch(BaseModel):
    items: list[SignalAnalysis]


SYSTEM_TRIAGE = """You are the triage analyst of TokiPulse, a territorial-intelligence platform run by a consulting firm
for local governments in the Basque Country (Bizkaia, Gipuzkoa, Araba, Navarre, Iparralde).
For each item (Spanish, Basque or French), decide whether it reveals a territorial issue or a need of residents.
Domains: HOU housing & urban planning · ECO local economy & commerce · PAR citizen participation ·
DEV territorial development (mobility, public services, neighbourhoods) · TS third sector (social exclusion,
associations, care, migration) · CUL culture, heritage, Basque language.
Sports results, celebrity news, international politics and generic national news are not relevant.
Scores 1-5: importance for the territory (1 one street, 5 a whole city), impact on residents (1 inconvenience,
5 housing loss / health / safety / income), urgency (1 structural, 5 deadline under two weeks).
Topic labels must be generic enough to group several articles about the same problem."""


def classify_with_claude(batch):
    examples = feedback_examples()
    ex_txt = "\n".join(f"- [{e['label']}] ({e['domain']}) {e['title']}" for e in examples) or "none yet"
    items = "\n".join(f"<item id=\"{s['id']}\" source=\"{s['source_name']}\">{s['title']} — {s['summary'][:400]}</item>"
                      for s in batch)
    out = ai_json(SYSTEM_TRIAGE, f"Analyst feedback on past items (learn from it):\n{ex_txt}\n\nItems:\n{items}\n\n"
                  "Return one analysis per item id.", Batch, TRIAGE_MODEL)
    return {a.id: a for a in out.items}


def classify_heuristic(s):
    text = f"{s['title']} {s['summary']}"
    doms = [] if _hits(text, _NOISE) else keyword_domains(text)
    terr, muni = detect_place(text)
    if not terr:
        src_terr = next((x["territory"] for x in settings.sources()
                         if x["id"] == s["source_id"]), None)
        terr = src_terr or "Euskadi"
    if not doms and s["family"].startswith("Expert"):
        doms = ["TS"]
    hits = _hits(text, _KW.get(doms[0], [])) if doms else 0
    return {"relevant": bool(doms), "domain": doms[0] if doms else None, "secondary": doms[1:3],
            "territory": terr, "municipality": muni,
            "importance": min(5, 1 + hits + (1 if muni else 0)),
            "impact": min(5, 2 + _hits(text, _IMPACT)),
            "urgency": min(5, 1 + 2 * _hits(text, _URGENT)),
            "summary": None, "topic_label": None}


def analyse_pending(limit=400):
    pending = db.rows("SELECT * FROM signals WHERE analysed_by IS NULL ORDER BY id LIMIT ?", (limit,))
    engine = "heuristic"
    results = {}
    eng = engine()
    if eng and pending:
        try:
            for i in range(0, len(pending), 20):
                for sid, a in classify_with_ai(pending[i:i + 20]).items():
                    results[sid] = {"relevant": a.relevant and a.territory != "Other", "domain": a.domain,
                                    "secondary": a.secondary, "territory": a.territory,
                                    "municipality": a.municipality, "importance": a.importance,
                                    "impact": a.impact, "urgency": a.urgency, "summary": a.summary,
                                    "topic_label": a.topic_label}
        except Exception as e:  # API problem (quota, network): keep going with the heuristic
            print(f"{eng} triage failed, using heuristic for the rest:", e)
        if results:
            engine = eng
    for s in pending:
        r = results.get(s["id"]) or classify_heuristic(s)
        db.execute("""UPDATE signals SET domain=?, secondary=?, territory=?, municipality=?, importance=?, impact=?,
                      urgency=?, relevant=?, ai_summary=?, analysed_by=? WHERE id=?""",
                   (r["domain"], ",".join(r["secondary"] or []), r["territory"], r["municipality"], r["importance"],
                    r["impact"], r["urgency"], 1 if r["relevant"] else 0, r["summary"],
                    (eng or "heuristic") if s["id"] in results else "heuristic", s["id"]))
        if r["relevant"]:
            assign_topic(s["id"], r.get("topic_label"))
    recompute_topics()
    return len(pending), engine


# ---------------------------------------------------------------- clustering into topics
def assign_topic(signal_id, ai_label=None):
    s = db.one("SELECT * FROM signals WHERE id=?", (signal_id,))
    toks = tokens(s["title"] + " " + (ai_label or ""))
    since = (dt.datetime.now() - dt.timedelta(days=14)).isoformat()
    best, best_sim = None, 0.0
    for t in db.rows("SELECT id, tokens, label FROM topics WHERE domain=? AND updated>=?", (s["domain"], since)):
        if ai_label and t["label"].lower() == ai_label.lower():
            best, best_sim = t, 1.0; break
        tt = set(json.loads(t["tokens"] or "[]"))
        if not tt or not toks:
            continue
        sim = len(tt & toks) / len(tt | toks)
        if sim > best_sim:
            best, best_sim = t, sim
    now = dt.datetime.now().isoformat()
    if best and best_sim >= settings.get("general")["cluster_threshold"]:
        merged = sorted(set(json.loads(best["tokens"] or "[]")) | toks)[:60]
        db.execute("UPDATE topics SET tokens=?, updated=? WHERE id=?", (json.dumps(merged), now, best["id"]))
        tid = best["id"]
    else:
        label = ai_label or s["title"][:110]
        tid = db.execute("""INSERT INTO topics (label, domain, territory, created, updated, tokens)
                            VALUES (?,?,?,?,?,?)""", (label, s["domain"], s["territory"], now, now,
                                                     json.dumps(sorted(toks))))
    db.execute("UPDATE signals SET topic_id=? WHERE id=?", (tid, signal_id))


def recurrence_score(n_sources):
    return 1 if n_sources <= 1 else 2 if n_sources == 2 else 3 if n_sources <= 4 else 4 if n_sources <= 7 else 5


def recompute_topics():
    adj = source_adjustments()
    now = dt.datetime.now()
    for t in db.rows("SELECT * FROM topics"):
        sigs = db.rows("SELECT * FROM signals WHERE topic_id=? AND relevant=1", (t["id"],))
        if not sigs:
            db.execute("UPDATE topics SET n_signals=0, priority=0, score=0 WHERE id=?", (t["id"],)); continue
        n_sources = len({s["source_id"] for s in sigs})
        latest = max(s["published"] or s["collected"] for s in sigs)
        age = (now - dt.datetime.fromisoformat(latest[:19])).days
        cred = max(min(5, max(1, s["credibility"] + adj.get(s["source_id"], 0))) for s in sigs)
        fresh = 5 if age <= 2 else 4 if age <= 7 else 3 if age <= 14 else 2
        crit = {"importance": max(s["importance"] or 1 for s in sigs),
                "recurrence": recurrence_score(n_sources),
                "impact": max(s["impact"] or 1 for s in sigs),
                "urgency": max(s["urgency"] or 1 for s in sigs),
                "credibility": round((cred + fresh) / 2, 1)}
        w = settings.get("weights")
        score = sum(w.get(k, 0) * v for k, v in crit.items())
        if n_sources >= 3 and crit["impact"] >= 4:
            kind = "Territorial issue to study"
        elif n_sources >= 3 or len(sigs) >= 4:
            kind = "Recurring concern"
        elif len(sigs) >= 2:
            kind = "Emerging trend"
        else:
            kind = "One-off information"
        terr = max({s["territory"] for s in sigs}, key=lambda x: sum(1 for s in sigs if s["territory"] == x))
        db.execute("""UPDATE topics SET n_signals=?, n_sources=?, score=?, priority=?, kind=?, territory=?, updated=?
                      WHERE id=?""", (len(sigs), n_sources, round(score, 2), max(1, min(5, round(score))), kind,
                                      terr, latest, t["id"]))


def topic_criteria(topic_id):
    """Explainability: the five criteria behind a topic's priority."""
    sigs = db.rows("SELECT * FROM signals WHERE topic_id=? AND relevant=1", (topic_id,))
    if not sigs:
        return {}
    return {"Importance": max(s["importance"] or 1 for s in sigs),
            "Recurrence": recurrence_score(len({s["source_id"] for s in sigs})),
            "Impact": max(s["impact"] or 1 for s in sigs),
            "Urgency": max(s["urgency"] or 1 for s in sigs),
            "Credibility": max(s["credibility"] for s in sigs)}
