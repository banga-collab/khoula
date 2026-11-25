"""Listening sessions: analysis, suggestions, radar cross-check and opportunities (client + consulting firm)."""
import re, json, datetime as dt
from typing import Literal, Optional
from pydantic import BaseModel, Field
from . import db
from .analyze import (engine as ai_engine, ai_json, ANALYST_MODEL, keyword_domains, tokens, _hits, _IMPACT, _URGENT, _KW,
                      detect_place)
from .config import DOMAINS
from . import settings

RECO = {
    "HOU": "Quantify rental pressure (rents, vacant homes, social-housing waiting times) and prioritise supply for young people and low-income households.",
    "ECO": "Map shop closures and vacant premises, and co-design a local-retail support plan with shopkeepers.",
    "PAR": "Set up a regular listening mechanism (neighbourhood councils, participatory budget) and publish how requests are followed up.",
    "DEV": "Prioritise public services and mobility in the neighbourhoods with the most reports, with an intervention timeline.",
    "TS": "Bring the relevant associations together to quantify social needs and align municipal action with the third sector.",
    "CUL": "Build culture, language and heritage into the territorial plan and support existing local initiatives.",
}


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", text or "") if len(s.strip()) > 25]


# ---------------------------------------------------------------- shared helpers
def radar_matches(domain, toks, territory, limit=3):
    out = []
    for t in db.rows("SELECT * FROM topics WHERE domain=? AND n_signals>0 ORDER BY score DESC LIMIT 200", (domain,)):
        tt = set(json.loads(t["tokens"] or "[]"))
        overlap = len(tt & toks)
        bonus = 1 if t["territory"] == territory else 0
        if overlap + bonus >= 2:
            out.append({"topic_id": t["id"], "label": t["label"], "priority": t["priority"], "kind": t["kind"],
                        "n_signals": t["n_signals"], "match": overlap + bonus})
    return sorted(out, key=lambda x: -x["match"])[:limit]


def grant_candidates(domains, toks, limit=6):
    out = []
    for g in db.rows("SELECT * FROM grants"):
        gd = json.loads(g["domains"] or "[]")
        if g["title"].lower().startswith(("justificación", "justificacion")):
            continue  # administrative follow-up, not a new opportunity
        dom_hit = len(set(gd) & set(domains[:3]))
        tok_hit = len(tokens(g["title"]) & toks)
        score = tok_hit * 2 + dom_hit
        if dom_hit and tok_hit:
            out.append({**g, "score": score, "domains": gd})
    return sorted(out, key=lambda x: -x["score"])[:limit]


def firm_opportunities(domains, session_id, territory):
    opps = []
    # cross-client pattern first: the same issue raised by other clients = a shared study to propose
    for d in domains[:3]:
        others = [s for s in db.rows("SELECT id, client, territory, analysis FROM sessions WHERE id<>?",
                                     (session_id or 0,))
                  if s["analysis"] and d in [i["domain"] for i in json.loads(s["analysis"]).get("issues", [])][:3]]
        if others:
            opps.append({"service": f"Shared study · {DOMAINS[d]['label']}",
                         "why": f"The same issue appears with {len(others)} other client(s): "
                                + ", ".join(o["client"].split(" · ")[0] for o in others[:3])
                                + ". A comparative Basque Country study can be offered to several clients.",
                         "type": "Multi-client offer"})
            break
    for sv in settings.get("services"):
        shared = [d for d in sv["domains"] if d in domains[:2]]
        if not shared or sv["id"] == "SV7":
            continue
        opps.append({"service": sv["name"], "why": f"\"{DOMAINS[shared[0]]['label']}\" is a priority issue "
                     f"in this session.", "type": "Follow-on engagement"})
    if domains:
        opps.append({"service": "Funding applications",
                     "why": "Open public grants match the issues raised in this session (see above).",
                     "type": "Follow-on engagement"})
    return opps[:5]


# ---------------------------------------------------------------- heuristic engine
def analyse_heuristic(sess):
    sents = split_sentences(sess["notes"])
    by_dom = {}
    for s in sents:
        for d in keyword_domains(s)[:1]:
            by_dom.setdefault(d, []).append(s)
    issues = []
    for d, ss in sorted(by_dom.items(), key=lambda x: -len(x[1])):
        text = " ".join(ss)
        prio = max(1, min(5, round(1.5 + len(ss) * 0.8 + _hits(text, _IMPACT) * 0.7 + _hits(text, _URGENT) * 0.5)))
        quote = max(ss, key=lambda x: _hits(x, _KW.get(d, [])) + _hits(x, _IMPACT))
        issues.append({"domain": d, "title": DOMAINS[d]["label"], "priority": prio,
                       "summary": f"{len(ss)} contribution(s) on this theme.", "quote": quote[:280],
                       "radar": radar_matches(d, tokens(text), sess["territory"])})
    domains = [i["domain"] for i in issues]
    toks = tokens(sess["notes"])
    return {
        "summary": f"Session with {sess['client']} ({sess['municipality'] or sess['territory']}): "
                   f"{len(issues)} issue(s) identified, mainly "
                   + (", ".join(DOMAINS[d]['label'] for d in domains[:3]) or "—") + ".",
        "issues": issues,
        "recommendations": [{"title": DOMAINS[d]["label"], "text": RECO[d]} for d in domains[:4]],
        "client_opportunities": [{"title": g["title"], "department": g["department"], "end": g["end"],
                                  "url": g["url"], "why": "Matches the issues: "
                                  + ", ".join(DOMAINS[x]["label"] for x in g["domains"] if x in domains)}
                                 for g in grant_candidates(domains, toks)],
        "firm_opportunities": firm_opportunities(domains, sess.get("id"), sess["territory"]),
    }


# ---------------------------------------------------------------- Claude engine
DOM = Literal["HOU", "ECO", "PAR", "DEV", "TS", "CUL"]


class Issue(BaseModel):
    domain: DOM
    title: str
    priority: int = Field(ge=1, le=5)
    summary: str
    quote: str = Field(description="Verbatim excerpt from the notes")


class Reco(BaseModel):
    title: str
    text: str


class ClientOpp(BaseModel):
    grant_index: int = Field(description="Index in the candidate grants list")
    why: str


class FirmOpp(BaseModel):
    service: str
    why: str
    type: Literal["Follow-on engagement", "Multi-client offer", "Potential new client"]


class SessionAnalysis(BaseModel):
    summary: str
    issues: list[Issue]
    recommendations: list[Reco]
    client_opportunities: list[ClientOpp]
    firm_opportunities: list[FirmOpp]


SYSTEM_SESSION = """You are a senior territorial-intelligence consultant at a consulting firm working with local
governments in the Basque Country. You analyse notes from listening sessions held with clients or residents.
Write in English. Be concrete and grounded in the notes; quotes must be verbatim. Recommendations must be
actionable for a municipality. Only propose grants from the candidate list when they genuinely fit, and only
propose consulting services from the firm's catalogue."""


def analyse_with_ai(sess, base):
    domains = keyword_domains(sess["notes"]) or list(DOMAINS)
    cands = grant_candidates(domains, tokens(sess["notes"]), limit=15)
    others = db.rows("SELECT client, territory, analysis FROM sessions WHERE id<>? AND analysis IS NOT NULL",
                     (sess.get("id") or 0,))
    ctx = {
        "client": sess["client"], "territory": sess["territory"], "municipality": sess["municipality"],
        "date": sess["date"], "participants": sess["participants"],
        "candidate_grants": [{"index": i, "title": g["title"], "department": g["department"], "deadline": g["end"]}
                             for i, g in enumerate(cands)],
        "firm_services": settings.get("services"),
        "other_clients_issues": [{"client": o["client"], "territory": o["territory"],
                                  "domains": [i["domain"] for i in json.loads(o["analysis"]).get("issues", [])]}
                                 for o in others][:20],
    }
    a = ai_json(SYSTEM_SESSION, f"<context>{json.dumps(ctx, ensure_ascii=False)}</context>\n"
                                f"<notes>{sess['notes']}</notes>", SessionAnalysis, ANALYST_MODEL,
                max_tokens=16000, analyst=True)
    return {
        "summary": a.summary,
        "issues": [{**i.model_dump(), "radar": radar_matches(i.domain, tokens(i.title + " " + i.quote + " " +
                                                                              i.summary), sess["territory"])}
                   for i in a.issues],
        "recommendations": [r.model_dump() for r in a.recommendations],
        "client_opportunities": [{"title": cands[o.grant_index]["title"],
                                  "department": cands[o.grant_index]["department"],
                                  "end": cands[o.grant_index]["end"], "url": cands[o.grant_index]["url"],
                                  "why": o.why} for o in a.client_opportunities if 0 <= o.grant_index < len(cands)],
        "firm_opportunities": [f.model_dump() for f in a.firm_opportunities],
    }


def analyse_session(session_id):
    sess = db.one("SELECT * FROM sessions WHERE id=?", (session_id,))
    base = analyse_heuristic(sess)
    result, engine = base, "heuristic"
    eng = ai_engine()
    if eng:
        try:
            result, engine = analyse_with_ai(sess, base), eng
        except Exception as e:
            print(f"{eng} session analysis failed, using heuristic:", e)
    db.execute("UPDATE sessions SET analysis=?, analysed_by=? WHERE id=?", (db.dumps(result), engine, session_id))
    return result


def create_session(data, example=False):
    terr = data.get("territory") or detect_place(data.get("notes", ""))[0] or "Euskadi"
    sid = db.execute("""INSERT INTO sessions (client, territory, municipality, date, participants, notes, created,
                        example) VALUES (?,?,?,?,?,?,?,?)""",
                     (data["client"], terr, data.get("municipality"), data.get("date") or dt.date.today().isoformat(),
                      data.get("participants"), data["notes"], dt.datetime.now().isoformat(), 1 if example else 0))
    analyse_session(sid)
    return sid


EXAMPLES = [
    {"client": "Ayuntamiento de Bilbao · Distrito Basurto-Zorroza", "territory": "Bizkaia", "municipality": "Bilbao",
     "date": "2026-11-12", "participants": "Concejal de distrito, 2 técnicos, 14 vecinos, Asociación vecinal Zorrotza",
     "notes": """Los vecinos explican que el precio del alquiler en Zorrotza ha subido mucho y que los jóvenes del barrio no pueden emanciparse; varios hablan de pisos turísticos en la zona de Basurto.
Una vecina mayor cuenta que vive sola y que la soledad no deseada es un problema creciente entre las personas mayores del barrio, sobre todo en invierno.
La asociación vecinal pide más frecuencia del autobús y denuncia que el centro de salud está saturado, con esperas de dos semanas.
Se menciona el cierre de tres comercios de proximidad en la calle principal en el último año y la sensación de abandono del barrio.
El concejal propone abrir un proceso de presupuestos participativos específico para el distrito y los vecinos piden que se haga un seguimiento público de las demandas.
Una técnica señala que la asociación de personas sin hogar Bizitegi observa más casos de exclusión residencial en la zona."""},
    {"client": "Ayuntamiento de Donostia · Servicio de Participación", "territory": "Gipuzkoa", "municipality": "Donostia",
     "date": "2026-11-05", "participants": "Técnica de participación, 9 asociaciones, 2 comerciantes de Egia",
     "notes": """Las asociaciones de Egia y Altza señalan que el alquiler se ha disparado y que muchas familias jóvenes se marchan a otros municipios; piden más vivienda protegida en alquiler.
Los comerciantes de Egia explican que el comercio local sufre por la competencia online y por la subida de los alquileres de los locales; tres tiendas han cerrado este año.
Varias asociaciones de cultura piden que el euskera tenga más presencia en las actividades del barrio y que se recupere el patrimonio industrial de Tabakalera como espacio vecinal.
Se critica que los procesos de participación ciudadana no tienen retorno: los vecinos no saben qué pasa con sus propuestas.
Una asociación de inmigrantes advierte de casos de racismo en el acceso a la vivienda."""},
    {"client": "Ayuntamiento de Vitoria-Gasteiz · Departamento de Políticas Sociales", "territory": "Araba",
     "municipality": "Vitoria-Gasteiz", "date": "2026-10-28",
     "participants": "Jefa de servicio, 3 educadores sociales, 5 entidades del tercer sector",
     "notes": """Las entidades del tercer sector describen un aumento de personas sin hogar en el centro de Vitoria-Gasteiz y la falta de plazas de acogida en invierno; piden una respuesta urgente antes de diciembre.
Los educadores sociales hablan de la salud mental de los jóvenes como una preocupación creciente, con listas de espera largas.
Se menciona la dificultad de las asociaciones para acceder a financiación estable y la carga administrativa de las subvenciones.
Una entidad comenta que muchas personas mayores viven solas y que la soledad no deseada aumenta en los barrios de Zaramaga y Coronación.
La jefa de servicio quiere un diagnóstico compartido de las necesidades sociales de la ciudad para el próximo plan municipal."""},
]


def seed_examples():
    if not db.one("SELECT id FROM sessions LIMIT 1"):
        for e in EXAMPLES:
            create_session(e, example=True)
        for r in db.rows("SELECT id FROM sessions"):  # second pass so cross-client patterns are detected
            analyse_session(r["id"])
