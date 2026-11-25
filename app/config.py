"""TokiPulse configuration: domains, sources (MVP from Source Radar), keywords, scoring weights, services."""
from urllib.parse import quote_plus

DOMAINS = {
    "HOU": {"label": "Housing & Urban Planning", "icon": "home"},
    "ECO": {"label": "Local Economy & Commerce", "icon": "store"},
    "PAR": {"label": "Citizen Participation", "icon": "users"},
    "DEV": {"label": "Territorial Development", "icon": "map"},
    "TS": {"label": "Third Sector", "icon": "heart"},
    "CUL": {"label": "Culture & Heritage", "icon": "landmark"},
}

TERRITORIES = ["Bizkaia", "Gipuzkoa", "Araba", "Navarre", "Euskadi"]

# Place names -> territory (used to tag signals with a territory / municipality)
PLACES = {
    "Bizkaia": ["bizkaia", "vizcaya", "bilbao", "bilbo", "barakaldo", "getxo", "portugalete", "santurtzi", "basauri",
                "durango", "leioa", "sestao", "galdakao", "erandio", "abadiño", "abadino", "atxondo", "elorrio",
                "iurreta", "berriz", "amorebieta", "zornotza", "mungia", "gernika", "bermeo", "basurto", "zorrotza",
                "zorroza", "deusto", "otxarkoaga", "santutxu", "rekalde", "uribarri", "begoña", "begoña"],
    "Gipuzkoa": ["gipuzkoa", "guipúzcoa", "guipuzcoa", "donostia", "san sebastián", "san sebastian", "irun", "errenteria",
                 "eibar", "zarautz", "arrasate", "mondragón", "mondragon", "bergara", "aretxabaleta", "eskoriatza",
                 "oñati", "oñati", "antzuola", "elgeta", "leintz", "tolosa", "hernani", "lasarte", "pasaia", "azpeitia",
                 "beasain", "hondarribia", "debagoiena", "amara", "gros", "egia", "altza"],
    "Araba": ["araba", "álava", "alava", "vitoria", "gasteiz", "vitoria-gasteiz", "llodio", "laudio", "amurrio",
              "aramaio", "salvatierra", "agurain"],
    "Navarre": ["navarra", "nafarroa", "pamplona", "iruña", "iruñea", "tudela", "estella", "lizarra", "barañain",
                "burlada", "tafalla", "baztan"],
}

# MVP sources from Source Radar (phase = MVP, machine-readable endpoint verified 2026-11-24)
SOURCES = [
    {"id": "S13", "name": "Berria", "kind": "rss", "family": "Media", "credibility": 4, "territory": None,
     "url": "https://www.berria.eus/uploads/feeds/feed_berria_eu.xml", "lang": "eu"},
    {"id": "S14", "name": "EITB", "kind": "rss", "family": "Media", "credibility": 4, "territory": None,
     "url": "https://www.eitb.eus/es/rss/noticias/", "lang": "es"},
    {"id": "S15", "name": "Goiena", "kind": "rss", "family": "Media", "credibility": 4, "territory": "Gipuzkoa",
     "url": "https://goiena.eus/aktualitatea/feed-rss", "lang": "eu"},
    {"id": "S16", "name": "Anboto", "kind": "rss", "family": "Media", "credibility": 4, "territory": "Bizkaia",
     "url": "https://anboto.org/aktualitatea/feed-rss", "lang": "eu"},
    {"id": "S07", "name": "SIIS", "kind": "rss", "family": "Expert & third sector", "credibility": 5, "territory": "Euskadi",
     "url": "https://www.siis.net/es/actualidad/rss/7/", "lang": "es"},
    {"id": "S17", "name": "Sareen Sarea", "kind": "rss", "family": "Expert & third sector", "credibility": 4,
     "territory": "Euskadi", "url": "https://sareensarea.eus/feed/", "lang": "es"},
    {"id": "S18", "name": "Bizitegi", "kind": "rss", "family": "Expert & third sector", "credibility": 4,
     "territory": "Bizkaia", "url": "https://www.bizitegi.org/es/feed/", "lang": "es"},
    {"id": "S11", "name": "Irekia (Gobierno Vasco)", "kind": "rss", "family": "Institutional", "credibility": 5,
     "territory": "Euskadi", "url": "https://www.irekia.euskadi.eus/es/news.rss", "lang": "es"},
    {"id": "S31", "name": "Ekologistak Martxan (Bluesky)", "kind": "rss", "family": "Citizen voice", "credibility": 3,
     "territory": None, "url": "https://bsky.app/profile/did:plc:rjpxoplumc763qe7f7jedfd5/rss", "lang": "es"},
    {"id": "S35", "name": "Etxebizitza Sindikatua (YouTube)", "kind": "rss", "family": "Citizen voice", "credibility": 3,
     "territory": None, "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC93_vTqIdfumubY6_LhdeYw", "lang": "eu"},
    {"id": "S36", "name": "EITB (YouTube)", "kind": "rss", "family": "Media", "credibility": 4, "territory": None,
     "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCcAQ9EqxQyfmGlK68GrSDcQ", "lang": "es"},
    {"id": "S21", "name": "Telegram · Comunidad Navarra", "kind": "telegram", "family": "Citizen voice", "credibility": 2,
     "territory": "Navarre", "url": "https://t.me/s/ComunidadNavarra", "lang": "es"},
    {"id": "S22", "name": "Telegram · Gasteizko Berriak", "kind": "telegram", "family": "Citizen voice", "credibility": 2,
     "territory": "Araba", "url": "https://t.me/s/GASTEIZKOBerriak", "lang": "es"},
]
# Google News RSS: one query per domain (S33/S34 pattern)
GNEWS = {
    "HOU": "vivienda alquiler Euskadi", "ECO": "comercio local Euskadi", "PAR": "participación ciudadana Euskadi",
    "DEV": "servicios públicos barrio Bilbao OR Donostia OR Vitoria", "TS": "tercer sector exclusión social Euskadi",
    "CUL": "patrimonio cultura euskera Euskadi",
}
for code, q in GNEWS.items():
    SOURCES.append({"id": f"GN-{code}", "name": f"Google News · {DOMAINS[code]['label']}", "kind": "rss",
                    "family": "Media", "credibility": 3, "territory": None, "lang": "es",
                    "url": "https://news.google.com/rss/search?q=" + quote_plus(q) + "&hl=es&gl=ES&ceid=ES:es"})

GRANTS_URL = ("https://www.euskadi.eus/contenidos/ds_ayudas_subvenciones/ultimas_ayudas_subvencion_bec/"
              "opendata/ayudas.json")

# Seed keywords (Keywords sheet of the enriched Source Radar), ES / EU / FR
KEYWORDS = {
    "HOU": "vivienda, alquiler, desahucio, okupa, vpo, vivienda protegida, emancipación, pisos turísticos, zona tensionada, rehabilitación, urbanismo, inmobiliari, hipoteca, etxebizitza, alokairu, etxegabet, emantzipazio, hirigintza, logement, loyer, expulsion",
    "ECO": "comercio, tienda, paro, empleo, hostelería, polígono, precios, coste de vida, autónomo, empresa, industria, salario, huelga, merkataritza, langabezia, enplegu, ostalaritza, enpresa, greba, lanpostu, commerce, chômage, emploi",
    "PAR": "participación, presupuestos participativos, consulta pública, alegaciones, asociación vecinal, pleno, moción, firmas, protesta, manifestación, concentración, vecinos, parte-hartze, kontsulta, auzo elkarte, osoko bilkura, mozio, sinadura, manifestazio, elkarretaratze, herritar, auzokide, concertation, pétition",
    "DEV": "movilidad, transporte, autobús, metro, tranvía, despoblación, servicios públicos, centro de salud, osakidetza, equipamiento, barrio, regeneración, obras, carretera, ayuntamiento, mugikortasun, garraio, autobus, tranbia, osasun zentro, auzo, udal, obra, mobilité, transports",
    "TS": "tercer sector, asociación, voluntariado, exclusión, pobreza, sin hogar, soledad, salud mental, cuidados, inmigra, racismo, refugiad, mayores, discapacidad, igualdad, violencia machista, hirugarren sektore, elkarte, boluntario, bazterkeria, pobrezia, etxerik gabe, bakardade, buru-osasun, zaintza, immigrazio, arrazakeria, adinekoen, berdintasun, indarkeria matxista",
    "CUL": "patrimonio, cultura, euskera, fiestas, biblioteca, museo, teatro, festival, música, txistu, bertsolari, ondare, kultura, euskara, jaiak, liburutegi, museo, antzerki, jaialdi, musika, bertso, kontzertu, patrimoine, culture",
}
IMPACT_WORDS = "desahucio, etxegabet, salud, osasun, muerte, heridos, pobreza, pobrezia, sin hogar, etxerik gabe, violencia, indarkeria, despido, cierre, ixte, accidente, istripu, contaminación, kutsadura, inundación, uholde, precio, prezio".split(", ")
URGENCY_WORDS = "urgente, urgencia, hoy, mañana, plazo, último día, inminente, gaur, bihar, epea, azken eguna, larri, emergencia, larrialdi, convoca, deialdi, manifestación, manifestazio, huelga, greba".split(", ")

# Signal priority weights (Scoring sheet, section B)
PRIORITY_WEIGHTS = {"importance": 0.20, "recurrence": 0.25, "impact": 0.25, "urgency": 0.15, "credibility": 0.15}

# Consulting services catalogue — EXAMPLE, replace with the firm's real offer
SERVICES = [
    {"id": "SV1", "name": "Territorial diagnosis", "domains": ["DEV", "HOU", "ECO"],
     "desc": "Data-driven baseline of a territory and its priority issues."},
    {"id": "SV2", "name": "Housing study", "domains": ["HOU"],
     "desc": "Local market analysis, housing needs and housing-policy recommendations."},
    {"id": "SV3", "name": "Citizen engagement process", "domains": ["PAR"],
     "desc": "Design and facilitation of participatory processes and participatory budgets."},
    {"id": "SV4", "name": "Local retail strategy", "domains": ["ECO"],
     "desc": "Revitalising town centres and local shops."},
    {"id": "SV5", "name": "Third-sector support", "domains": ["TS"],
     "desc": "Mapping social needs and structuring partnerships with associations."},
    {"id": "SV6", "name": "Culture & heritage development", "domains": ["CUL"],
     "desc": "Territorial cultural projects, heritage and language."},
    {"id": "SV7", "name": "Funding applications", "domains": ["HOU", "ECO", "PAR", "DEV", "TS", "CUL"],
     "desc": "Identifying public grants and writing applications."},
]

# Items matching these are treated as noise (sports results, etc.)
NOISE_WORDS = "fútbol, futbol, liga, athletic, real sociedad, osasuna, alavés, alaves, eibar sd, sailkapen, lasterketa, txapelketa, partido de, gol, baloncesto, pelota vasca, ciclismo, maratón, maraton, kirol".split(", ")
