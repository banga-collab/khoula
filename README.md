# TokiPulse — MVP prototype

Territorial-intelligence platform (Basque Country): public-source radar + listening sessions + opportunities + weekly report + admin.

## Run

```
pip install --user fastapi uvicorn feedparser anthropic
python -m uvicorn app.main:app --port 8600
```
Open http://localhost:8600. On first start the collection runs and 3 fictional example sessions are created.

## Enable Claude analysis (optional)

Without a key everything runs in **heuristic mode** (Source Radar keywords). With a key:
```
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```
- Signal triage: `claude-haiku-5-5` (structured outputs, analyst feedback injected as examples)
- Listening sessions: `claude-opus-5-5` (server-side fallback enabled on refusals)

## Features
- **Radar**: topics with priority 1-5, signal type, feedback (Relevant, Not relevant, Watch, Duplicate, To verify)
- **Listening sessions**: issues, quotes, radar cross-check, recommendations, client and firm opportunities
- **Weekly report**: charts, statistics, conclusions. Download as PDF (print), standalone HTML, or CSV data
- **Admin**: sources (add/edit/disable), keywords, scoring weights, services catalogue, content moderation, activity log, auto-collection
- Light / dark mode (follows the system, toggle in the header)

## Structure

| File | Role |
|---|---|
| `app/config.py` | Defaults: sources, domains, keywords, weights, services (**example — replace in Admin**) |
| `app/settings.py` | Admin-editable settings stored in SQLite |
| `app/collect.py` | Research: RSS, public Telegram, open grants (Open Data Euskadi) |
| `app/analyze.py` | Listening + Analysis: classification, priority, topic clustering, signal type |
| `app/sessions.py` | Listening sessions analysis and opportunities |
| `app/main.py` | API, weekly report, admin endpoints, scheduler |
| `static/` | Dashboard |

## Known limits
- No login yet: the Admin tab is open to anyone who can reach the server. Add authentication before any deployment.
- EITB RSS feed is frozen (last items 2025) and Telegram Comunidad Navarra inactive since 2024: replace them in Admin → Sources.
- Reddit not connected (OAuth + commercial agreement required). bilbao.eus sources block scripts (403).
