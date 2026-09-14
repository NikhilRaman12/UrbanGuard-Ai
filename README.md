# UrbanGuard AI

**Sovereign Municipal Sanitation & Pathogen Intelligence Platform** — a local-first hackathon prototype for turning sanitation telemetry into auditable pathogen-risk alerts, crew work orders, and multilingual public notices.

```text
Sensors / citizen reports
          │ POST /telemetry/ingest
          ▼
 SQLite telemetry store ──► PRI scoring ──► Monitor agent
          │                                  │
          └──── GET /risks/heatmap ◄─────────┼── Dispatcher / Compliance agent
                                             └── Public communication agent
                                                        │
                                              work order + DE/EN/FR/IT advisory
```

## Quick start

### Docker (recommended)

```bash
docker compose up --build
```

Open `http://localhost:3000`. The API docs are at `http://localhost:8000/docs`.

### Local development

```bash
# terminal 1
cd backend
python -m venv .venv
.venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend
npm install
npm run dev
```

The dashboard includes **Refresh real weather**, which fetches current temperature and the preceding 24 hours of precipitation from Open-Meteo for five Munich reference locations. **Refresh city reports** imports sanitation-relevant, anonymised Munich Open311 reports when `MUNICH_OPEN311_URL` is configured to the currently approved city feed. It produces explicitly labelled report-derived triage evidence, not a verified inspection or measurement. The separate **Run demo data** control remains for presentation only. The frontend talks to `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).

When a live city feed is not available, **Load realistic scenario** loads a deterministic, clearly synthetic Munich sanitation scenario. It lets teams exercise the risk ranking, audit trail, work-order drafting, and human-approval flow without misrepresenting the data as a live municipal record.

### Streamlit shareable dashboard

An isolated Streamlit client is included for a quick public demo. It uses the same FastAPI service and preserves the explainable scoring, evidence limitations, audit feed, and human-approval workflow.

```bash
streamlit run streamlit/streamlit_app.py
```

For Streamlit Community Cloud, deploy `streamlit/streamlit_app.py` and configure the `URBANGUARD_API_URL` secret with a publicly reachable FastAPI URL. See [streamlit/README.md](streamlit/README.md).

For the stakeholder walkthrough, use the reproducible [demo guide](DEMO_GUIDE.md). It documents the synthetic scenario, expected Munich-area ranking, safe claims, and five-minute presentation flow.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/v1/telemetry/ingest` | Store raw device readings or field reports and score PRI |
| GET | `/api/v1/risks/heatmap` | Get current geospatial sector risk scores |
| POST | `/api/v1/agents/trigger-dispatch` | Run monitor → dispatcher/compliance → communications workflow |
| POST | `/api/v1/simulation/tick` | Create a batch of Munich-template mock readings |
| POST | `/api/v1/data/refresh-weather` | Fetch real public weather evidence from Open-Meteo |
| POST | `/api/v1/data/refresh-munich-reports` | Fetch sanitation-relevant reports from the configured Munich Open311 feed |
| POST | `/api/v1/data/load-realistic-scenario` | Load deterministic, synthetic training records for a full workflow demonstration |
| GET | `/api/v1/activity` | Read the agent audit trail |
| GET | `/api/v1/work-orders` | Review generated work orders |

## Architecture and safety model

`backend/app/agents.py` implements an async native-Python agent graph. Its output is structured, deterministic, and logged: this is intentionally safer than allowing a model to autonomously issue municipal instructions. The compliance copilot applies versioned local protocol excerpts from `backend/data/regulations.json`. An optional `OLLAMA_BASE_URL` can be configured later for local wording assistance, but raw telemetry never needs to leave the deployment boundary.

The PRI is a transparent 0–100 score based on temperature, standing-water hours, organic waste, sewer level, pH deviation, and clog probability. It is a decision-support signal—not an epidemiological diagnosis.

## European digital sovereignty / GDPR

- **Local by design:** SQLite, rule retrieval, agent orchestration, and optional Ollama inference run within the municipal-controlled environment.
- **Data minimisation:** telemetry schema excludes names, addresses, device identifiers tied to people, and citizen-report free text is capped and treated as operational evidence.
- **Human approval:** dispatch tickets begin as `pending_approval`; no crew action or external notification is sent automatically.
- **Auditability:** each workflow step writes a timestamped activity event; risk formulas and protocol references are inspectable.
- **Retention:** this demo has no production retention policy. A real deployment must configure purpose-limited retention, access controls, DPIA, data-subject processes, and regional hosting/contracts.

## Project layout

```text
backend/       FastAPI API, SQLite store, simulation, agents, local regulations
frontend/      Next.js 14 App Router command dashboard
streamlit/     Shareable Streamlit command dashboard
docker-compose.yml
```
