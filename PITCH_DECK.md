---
marp: true
theme: default
paginate: true
title: UrbanGuard AI — Pitch & Technical Deck
---

<!--
UrbanGuard AI — Pitch & Technical Deck
=======================================
How to turn this into a PowerPoint:
  1. Marp for VS Code  -> "Export Slide Deck -> PPTX", or
  2. Copy each `---`-separated section into one PowerPoint slide, or
  3. `npx @marp-team/marp-cli PITCH_DECK.md -o pitch.pptx`

LEGEND used throughout:
  [BUILT]     = implemented and running in this repository today
  [TARGET]    = proposed Google Cloud / ADK / Gemini architecture (roadmap)
The current code does NOT call Gemini or Google ADK yet. Those slides describe
the upgrade path and are labelled clearly so nothing is over-claimed.
-->

# UrbanGuard AI

### Sovereign Municipal Sanitation & Pathogen Intelligence

From fragmented sanitation signals to **auditable, human-approved** field priorities —
built today, and designed to scale on **Google Cloud ADK + Gemini**.

<!-- Presenter: 15-second pitch. Then set expectation: "first half is what runs today, second half is the cloud/agent roadmap." -->

---

## The problem

- Municipal sanitation teams get **fragmented** signals:
  weather, drainage, waste, citizen calls, field photos — in different systems.
- Limited crews must decide **where to go first**, and defend that decision.
- Existing tools are opaque, cloud-bound, or emit alerts **no one can audit**.
- Public-health and data-protection rules forbid "black box" automation.

<!-- Presenter: the pain is prioritisation + accountability, not raw data volume. -->

---

## What UrbanGuard AI does

1. **Ingests** multi-source evidence — sensors, weather, reports, images, text.
2. **Scores** risk with a transparent, explainable formula (the PRI).
3. **Fuses** modalities (telemetry + image + text) into one priority signal.
4. **Drafts** work orders and multilingual public advisories.
5. **Requires** a named human to **approve** or **reject** — nothing auto-sends.

> Prioritise. Explain. Approve.

---

## Two-layer story on this deck

| Layer | Status | What it covers |
| --- | --- | --- |
| **A. The running system** | `[BUILT]` | FastAPI + SQLite + deterministic agents + multimodal heuristics |
| **B. The target platform** | `[TARGET]` | Google ADK agents, Gemini models, Vertex AI Agent Engine on GCP |

Layer A proves the design and the governance model.
Layer B shows how it scales with **LLM reasoning + managed agent runtime** —
without weakening the human-in-the-loop guarantees.

<!-- Presenter: be explicit that B is the roadmap; A is what you can demo now. -->

---

## End-to-end flow `[BUILT]`

```text
 Sensors / citizen reports / photos / text
            │
            ▼
   Ingest API ──► SQLite store ──► PRI scoring (risk.py)
            │                          │
   Multimodal fusion ◄────────────────┤
   (image + text + telemetry)         ▼
            │                    Monitor agent
            ▼                          │
   provenance + evidence        Dispatcher / Compliance agent
                                       │
                                  Public communication agent
                                       │
                        work order (pending_approval)
                        + DE / EN / FR / IT advisory
                                       │
                          ┌────────────┴────────────┐
                          ▼                         ▼
                    Human APPROVE            Human REJECT
```

---

## Repository map `[BUILT]`

| Path | Responsibility |
| --- | --- |
| `backend/app/main.py` | FastAPI app, all HTTP endpoints, CORS, lifespan |
| `backend/app/risk.py` | `calculate_pri`, `risk_components`, `severity` |
| `backend/app/agents.py` | Deterministic agent graph `run_dispatch` |
| `backend/app/multimodal.py` | `analyse_image`, `analyse_text`, `fuse_modalities` |
| `backend/app/store.py` | SQLite: telemetry, activity, work_orders, evidence |
| `backend/app/real_data.py` | Open-Meteo + Open311 live connectors |
| `backend/app/scenario_data.py` / `simulation.py` | Synthetic scenario + demo ticks |
| `frontend/app/page.tsx` | Next.js command dashboard |
| `streamlit/streamlit_app.py` | Shareable Streamlit dashboard |
| `backend/tests/` | 29 tests: risk, store, agents, API, multimodal |

---

## Code walkthrough — request lifecycle `[BUILT]`

```python
# backend/app/main.py
@app.post("/api/v1/telemetry/ingest")
def ingest(t: TelemetryIn):
    return store_reading(t, synthetic=False)      # score + persist + audit

def store_reading(t, synthetic=False):
    pri = calculate_pri(t)                         # risk.py
    store.add_telemetry(t, pri, synthetic=synthetic)
    store.log("Ingestion Engine", ...)             # audit trail
    return {"accepted": True, "pri": pri, "severity": severity(pri)}
```

Every write also writes an **audit event** — that is the accountability backbone.

<!-- Presenter: point at the audit log on the dashboard. -->

---

## Data model `[BUILT]`

```text
telemetry   (id, sector_id, district, lat, lon, source, payload,
             pri, observed_at, synthetic)
activity    (id, agent, message, created_at)          <- audit feed
work_orders (id, sector_id, title, priority, status, protocol_refs,
             created_at, decided_by, decided_at)      <- governance
evidence    (id, sector_id, modality, lat, lon, caption,
             features, score, observed_at)            <- multimodal
```

- `synthetic` flags training data vs live connector data (honest provenance).
- `decided_by` / `decided_at` make every approval attributable.

---

## Risk model — the PRI `[BUILT]`

`backend/app/risk.py` — a transparent 0–100 score, capped per component:

| Component | Formula (abridged) | Max |
| --- | --- | ---: |
| Temperature | `(T − 10) × 1.25` clamped | 25 |
| Standing water | `hours / 72 × 30` | 30 |
| Organic waste | `pct × 0.2` | 20 |
| Sewer level | `(level − 70) / 3` | 10 |
| pH deviation | `abs(pH − 7) × 2.5` | 5 |
| Clog probability | `pct × 0.1` | 10 |

`severity()`: `critical ≥ 75 · high ≥ 55 · moderate ≥ 30 · low < 30`.

It is a **triage signal**, not an epidemiological diagnosis.

<!-- Presenter: every number on screen traces back to one of these six inputs. -->

---

## The agent graph `[BUILT]`

`backend/app/agents.py` — deterministic and async (safer than autonomous LLM):

```python
async def run_dispatch(sector_id):
    pri = latest point's PRI
    store.log("Sanitation Monitor", "...PRI ... severity")
    if pri < 30: return {"action": "monitor", ...}          # no dispatch
    refs = matching regulations from regulations.json
    priority = "P1 — same day" if pri >= 75 else "P2 — within 24 hours"
    order_id = store.create_order(sector_id, title, priority, refs)
    advisories = {"de":..., "en":..., "fr":..., "it":...}
    store.log("Public Communication Agent", "...human review...")
    return {"action": "dispatch_drafted", "work_order": {...}, "advisories": ...}
```

**Compliance copilot** applies versioned protocol excerpts; output is
structured, logged, and always `pending_approval`.

---

## Multimodal evidence `[BUILT]`

`backend/app/multimodal.py` — three modalities, one explainable score:

| Modality | Method | Output |
| --- | --- | --- |
| Telemetry | weighted PRI | 0–100 |
| **Image** | water-like / waste-like colour-texture pixel fractions | 0–100 |
| **Text** | fixed sanitation taxonomy (water, waste, sewage, blockage, odour, rodents, contamination) | 0–100 |

```python
fuse_modalities(telemetry_pri, visual, text)   # weights 0.60 / 0.25 / 0.15
```

No image or text leaves the deployment boundary.

<!-- Presenter: deterministic today; slide 26+ upgrades the image/text parts to Gemini. -->

---

## Human-in-the-loop governance `[BUILT]`

- Work orders are born `pending_approval` — **nothing is sent automatically**.
- `POST /work-orders/{id}/decision` stores **approve/reject + reviewer + time**.
- A decided order is **locked** (HTTP `409` on a second decision).
- Every decision is written to the audit feed and visible in the UI.

```json
POST /api/v1/work-orders/7/decision
{ "decision": "approve", "actor": "ops.lead@muenchen.de", "note": "crew scheduled" }
```

<!-- Presenter: this is the procurement-grade accountability story. -->

---

## Provenance you can trust `[BUILT]`

- Telemetry tagged **synthetic vs live**; the API reports `data_mode`:
  `live_connector`, `synthetic_training_snapshot`, or `mixed_sources`.
- Public weather = **exposure proxy**; reports = **unverified triage evidence**.
- Limitations are printed on every data surface and in every response.

<!-- Presenter: honest labelling is a feature that builds official trust. -->

---

## Clients & UX `[BUILT]`

- **Next.js 14 command dashboard** (`frontend/app/page.tsx`)
  - metrics strip, city risk map, evidence panel, agent audit feed
  - approve / reject controls with a required reviewer field
  - CSV export of the live triage snapshot
- **Streamlit dashboard** for quick public demos
- Selecting a location **inspects** it; dispatch is a deliberate second action.

<!-- Presenter: the UI encodes the governance policy. -->

---

## Quality & delivery `[BUILT]`

- **29 automated tests** — risk formula, store, agents, API, multimodal.
- **GitHub Actions CI** — backend pytest + Next.js build on every PR.
- **Docker Compose** — one command: API + dashboard.
- **Live connectors** verified — Open-Meteo weather + Open311 reports.

```bash
cd backend && pip install -r requirements.txt -r requirements-dev.txt && pytest
docker compose up --build
```

---

## Live run — real data this session `[BUILT]`

```text
POST /data/refresh-weather      -> 5 Open-Meteo observations ingested
/health                         -> data_mode: mixed_sources, 8 locations

Image evidence  -> visual water 55.5 · waste 39.7 · quality ok
Text  evidence  -> signal 70.0 · {standing_water, drainage_blockage, odor, rodent}

POST /evidence/fuse/MUC-NEU-05
  -> 27.1 = telemetry 4.5 @ 60%  +  visual 55.5 @ 25%  +  text 70 @ 15%
```

Fusion lifts an activity-driven location while still deferring to hard sensors.

<!-- Presenter: this is reproducible; show the API docs at /docs. -->

---

<!-- ============================================================= -->
<!-- SECTION B — TARGET ARCHITECTURE ON GOOGLE CLOUD (PROPOSED)     -->
<!-- ============================================================= -->

# Part B — Scaling on Google Cloud

### ADK agents · Gemini · Vertex AI

> Everything from here is **`[TARGET]`** — proposed, not yet in the code.

---

## Why agents (and why not just more `if` statements)?

`[TARGET]` — the deterministic graph is great for governance, but:

- Compliance text, citizen wording, and **photos** need **language + vision** reasoning.
- New regulations and new sectors appear constantly → **tool-calling** beats hard-coding.
- Operators want a **conversational** layer ("why is Neuhausen P1?").
- You need **evaluation**, **tracing**, and a **managed runtime** for production.

→ Adopt **Google's Agent Development Kit (ADK)** + **Gemini** while keeping the
deterministic PRI as a **tool** the agents must call and cite.

<!-- Presenter: reassure — the PRI stays; agents orchestrate and explain around it. -->

---

## Google ADK in one slide `[TARGET]`

**Agent Development Kit** — open-source, code-first framework for building,
evaluating and deploying multi-agent systems.

| Primitive | Role in UrbanGuard |
| --- | --- |
| `LlmAgent` | a reasoning agent bound to a Gemini model + tools |
| `SequentialAgent` | monitor → compliance → communications pipeline |
| `ParallelAgent` | analyse image + text + telemetry evidence concurrently |
| `LoopAgent` | poll feeds until a sector stabilises |
| `FunctionTool` | wraps existing Python (`calculate_pri`, `create_order`) |
| `SessionService` / `MemoryService` | conversation + long-term recall |
| `Runner` | executes agent trees, streams events, traces calls |
| `adk web` / `adk eval` | local dev UI + automated evaluation |

Model-agnostic, but **optimised for Gemini**.

---

## Mapping current agents → ADK agents `[TARGET]`

| Today (`agents.py`) `[BUILT]` | ADK agent `[TARGET]` | Model |
| --- | --- | --- |
| `Sanitation Monitor` | `sanitation_monitor` (`LlmAgent`) | `gemini-2.5-flash` |
| `Dispatcher & Compliance Copilot` | `compliance_copilot` (`LlmAgent` + RAG) | `gemini-2.5-pro` |
| `Public Communication Agent` | `public_communication` (`LlmAgent`) | `gemini-2.5-flash` |
| `Multimodal Evidence Agent` | `vision_triage` (`LlmAgent`, multimodal) | `gemini-2.5-flash` |
| `Evidence Fusion Agent` | deterministic tool (kept as-is) | — |
| orchestration in `run_dispatch` | `SequentialAgent` root | — |

**Rule:** agents may *reason and draft*, but only tools may *mutate state*.

---

## Proposed ADK code `[TARGET]`

```python
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
from app.risk import calculate_pri        # existing code, wrapped as a tool
from app.store import create_order, latest_points

monitor = LlmAgent(
    name="sanitation_monitor",
    model="gemini-2.5-flash",
    instruction=("Assess sanitation risk. You MUST call calculate_pri and cite the "
                 "component contributions. Never diagnose disease or assert pathogens."),
    tools=[FunctionTool(calculate_pri), FunctionTool(latest_points)],
)

compliance = LlmAgent(
    name="compliance_copilot",
    model="gemini-2.5-pro",
    instruction=("Draft a work order citing ONLY retrieved regulation excerpts. "
                 "All orders start pending_approval. Never contact the public."),
    tools=[FunctionTool(retrieve_regulations), FunctionTool(create_order)],
)

advisory = LlmAgent(
    name="public_communication",
    model="gemini-2.5-flash",
    instruction="Produce DE/EN/FR/IT advisories for human review only.",
)

root = SequentialAgent(name="urbanguard_pipeline",
                       sub_agents=[monitor, compliance, advisory])
```

---

## Gemini for multimodal triage `[TARGET]`

Replace the colour-texture heuristic with **Gemini vision**, with **structured output**:

```python
from pydantic import BaseModel

class Triage(BaseModel):
    water_likelihood: float      # 0-1
    waste_likelihood: float      # 0-1
    hazards: list[str]
    confidence: float
    rationale: str

vision = LlmAgent(
    name="vision_triage",
    model="gemini-2.5-flash",                 # native image understanding
    instruction=("Classify sanitation evidence in the photo. Return JSON only. "
                 "Do not identify people. Do not assert contamination."),
    generate_content_config={"response_mime_type": "application/json",
                             "response_schema": Triage},
)
```

Feeds the **same `fuse_modalities()`** weights → governance unchanged.

<!-- Presenter: same contract, better perception. The fusion layer is agnostic to who produced the score. -->

---

## Gemini for text, language & grounding `[TARGET]`

- **Multilingual advisories** — one prompt → DE / EN / FR / IT, tone-checked.
- **Citizen-report understanding** — structured extraction of category, severity,
  location hints from free text (replaces the keyword taxonomy).
- **Grounding** — Vertex AI Search / RAG Engine over `regulations.json`,
  municipal SOPs, and public health guidance, so the copilot **cites** sources.
- **Function calling** — agents call real tools (`create_order`, `export_csv`)
  rather than inventing actions.
- **Structured output** — every agent returns a validated schema, so nothing
  unvalidated ever reaches the store.

---

## GCP deployment architecture `[TARGET]`

```text
                 ┌──────────────────────────────────────────────┐
   citizens  ──► │  Cloud Run: Next.js dashboard + Streamlit     │
   crews         └──────────────────────────────────────────────┘
                                   │  HTTPS
                 ┌─────────────────▼──────────────────────────────┐
                 │  Cloud Run / Vertex AI Agent Engine             │
                 │  ADK root agent (SequentialAgent)               │
                 │   ├─ sanitation_monitor  (gemini-2.5-flash)     │
                 │   ├─ compliance_copilot  (gemini-2.5-pro + RAG) │
                 │   ├─ public_communication(gemini-2.5-flash)     │
                 │   └─ vision_triage       (gemini-2.5-flash)     │
                 └───────┬───────────────┬───────────────┬────────┘
                         │               │               │
                 Firestore / AlloyDB   Pub/Sub      Vertex AI
                 (sessions, orders)  (ingest)   Vector Search (RAG)
                         │               │               │
                 Cloud Storage     BigQuery        Secret Manager
                 (images)          (analytics)     (keys, config)
```

---

## Google Cloud services used `[TARGET]`

| Concern | Service |
| --- | --- |
| Agent runtime | **Vertex AI Agent Engine** (managed) or **Cloud Run** |
| Models | **Gemini 2.5 Flash / Pro** on **Vertex AI** |
| RAG / grounding | **Vertex AI Search**, **Vector Search**, RAG Engine |
| State | **Firestore** (sessions) · **AlloyDB**/**Cloud SQL** (orders) |
| Evidence media | **Cloud Storage** (photos, signed URLs) |
| Streaming ingest | **Pub/Sub**, **Eventarc**, **Cloud Scheduler** |
| Analytics | **BigQuery** (triage outcomes, response times) |
| Observability | **Cloud Logging / Monitoring / Trace**, ADK eval |
| Secrets & CI/CD | **Secret Manager**, **Artifact Registry**, **Cloud Build/Deploy** |

---

## Security, privacy & sovereignty on GCP `[TARGET]`

- **Region pinning** — deploy in `europe-west3` (Frankfurt) / `europe-west4`.
- **CMEK** — Cloud KMS customer-managed keys for data at rest.
- **VPC Service Controls** — perimeter around Vertex AI, Storage, Firestore.
- **IAM + Workload Identity** — no long-lived keys; least-privilege service accounts.
- **Data governance** — Vertex AI/Enterprise terms: customer data not used to
  train foundation models; configure data residency + logging.
- **Honest tradeoff:** "local-first" (today) vs "EU-region managed cloud"
  (target). Offer a **hybrid**: PRI + storage on-prem, Gemini for language/vision
  with **de-identified** payloads.

<!-- Presenter: acknowledge the sovereignty tension — it is the #1 objection in EU procurement. -->

---

## Agent-to-agent & tool interoperability `[TARGET]`

- **A2A (Agent2Agent) protocol** — let the sanitation agent collaborate with a
  municipal GIS agent, a fleet-dispatch agent, or a public-health agent, each
  owning its own tools and data.
- **MCP (Model Context Protocol)** — expose tools like `latest_points` or
  `retrieve_regulations` as MCP servers, reusable by any agent.
- **Single source of truth** — the PRI, the store, and the audit trail stay
  shared; agents are interchangeable workers around them.

<!-- Presenter: future-proofs the architecture against vendor lock-in of orchestration. -->

---

## Evaluation & observability `[TARGET]`

- **`adk eval`** — golden set of Munich scenarios; assert the agent calls
  `calculate_pri`, cites the right regulation, and never asserts a diagnosis.
- **Cloud Trace** — end-to-end span per request: ingest → agent → order.
- **Agent analytics (BigQuery)** — recommendation volume, approval rate,
  time-to-approve, false-alert rate, field-verification rate.
- **Guardrail evals** — fail CI if an agent produces unsafe language or skips
  the approval step.

<!-- Presenter: evals are how you earn the right to automate more later. -->

---

## Migration roadmap `[TARGET]`

| Phase | Deliverable | Keeps |
| --- | --- | --- |
| 0 (now) | Deterministic agents + PRI + governance | `[BUILT]` |
| 1 | Wrap `risk.py`/`store.py` as **tools** | audit trail |
| 2 | Add **Gemini vision** for image triage | fusion weights |
| 3 | Add **RAG** over regulations for the copilot | citations |
| 4 | Run the ADK `SequentialAgent` on **Cloud Run** | human approval |
| 5 | Move to **Agent Engine** + Firestore sessions | same contracts |
| 6 | Add **A2A** partner agents (GIS, fleet) | sovereignty controls |

Each phase is independently shippable and reversible.

---

## Cost & scaling notes `[TARGET]`

- **Gemini Flash** for high-volume triage; **Pro** only for the compliance draft.
- **Context caching** for the stable instruction + regulation context.
- **Batch** overnight re-scoring; **Cloud Scheduler** for periodic refreshes.
- **Image preprocessing** (downscale to ≤256 px, as today) before Gemini calls.
- Cloud Run scales to zero between bursts; Agent Engine handles session sprawl.

<!-- Presenter: agents are cheap if Flash handles volume and Pro is reserved for drafting. -->

---

## 5-minute demo script

1. Show the **dashboard** with live Munich weather ingested (`mixed_sources`).
2. Open **Neuhausen** — walk through the six PRI contributors.
3. Upload a **photo** → show the visual water/waste scores.
4. Paste a **citizen report** → show extracted categories.
5. Run **fusion** → explain the weighted score.
6. Draft a **work order** → it is `pending_approval`.
7. Enter reviewer name → **APPROVE** → the audit feed records who/when.
8. Switch to the **`[TARGET]` slides** and show the ADK/Gemini upgrade path.

---

## Claims to avoid

Do **not** say UrbanGuard:

- detects disease,
- proves contamination,
- predicts infection, or
- replaces inspectors.

Say it **prioritises sanitation signals for human-reviewed field verification** —
and that Gemini/ADK **assist reasoning**, never replace the approving official.

<!-- Presenter: repeat the boundary; it is what makes the pitch credible. -->

---

# UrbanGuard AI

### Prioritise. Explain. Approve.

**Today:** deterministic, auditable, local-first (`[BUILT]`).
**Next:** ADK agents + Gemini on Google Cloud, EU region, same guarantees (`[TARGET]`).

`github.com/NikhilRaman12/UrbanGuard-Ai`

<!-- Presenter: Q&A. Offer the repo, the DESIGN_DECK.md, and the live /docs. -->
