---
marp: true
theme: default
paginate: true
title: UrbanGuard AI — Design Deck
---

<!--
UrbanGuard AI — Design Deck
A markdown slide deck. To present as PowerPoint either:
  * open in Marp / Marp for VS Code and "Export > PowerPoint (.pptx)", or
  * paste each `---`-separated section into its own PowerPoint slide.
Presenter notes live in these HTML comments and are invisible on the slide.
-->

# UrbanGuard AI

### Sovereign Municipal Sanitation & Pathogen Intelligence

Turning fragmented sanitation telemetry, photos and citizen reports into
**auditable, human-approved** field priorities.

<!-- Presenter: one-line pitch. Local-first decision support, not a diagnosis engine. -->

---

## The problem

- Municipal teams receive **fragmented** signals: weather, drainage, waste,
  citizen reports, field photos — across different systems.
- Limited crews must decide **where to go first**, and be able to **justify it**.
- Existing tools are either opaque, cloud-dependent, or produce alerts no one
  can audit.

<!-- Presenter: emphasise the operational pain, not the technology. -->

---

## What UrbanGuard does

1. **Ingests** multi-source evidence (sensors, weather, reports, images, text).
2. **Scores** risk with a transparent, explainable formula.
3. **Fuses** modalities into one priority signal.
4. **Drafts** work orders and multilingual advisories.
5. **Requires** a named human to approve or reject.

<!-- Presenter: "explainable", "auditable", "human-in-the-loop" are the three pillars. -->

---

## Architecture

```text
 Sensors / citizen reports / photos
            │
            ▼
   Ingest API ──► SQLite store ──► PRI scoring
            │                          │
   Multimodal fusion ◄───────────────┤
            │                          ▼
            │                    Monitor agent
            ▼                          │
   Evidence + provenance        Dispatcher / Compliance agent
                                       │
                                  Public communication agent
                                       │
                        work order (pending) + DE/EN/FR/IT advisory
                                       │
                              Human APPROVE / REJECT
```

<!-- Presenter: everything runs inside the municipal boundary. -->

---

## European digital sovereignty

- **Local by design** — SQLite, rule retrieval and (optional) local inference
  run inside the controlled environment.
- **Data minimisation** — no names, addresses, or person-linked device IDs.
- **No cloud egress** for inference; evidence never leaves the boundary.
- **Auditable** — every step writes a timestamped activity event.

<!-- Presenter: aligns with GDPR + public-sector procurement concerns. -->

---

## Risk scoring: the PRI

A transparent 0–100 score from six named contributions:

| Component | Weight |
| --- | ---: |
| Temperature | 25 |
| Standing-water hours | 30 |
| Organic waste | 20 |
| Sewer level | 10 |
| pH deviation | 5 |
| Clog probability | 10 |

Every score shows **which** inputs contributed. It is a **triage signal**, not
an epidemiological diagnosis.

<!-- Presenter: show the evidence chips in the UI to make this concrete. -->

---

## Multimodal evidence pipeline

Three modalities, one explainable decision:

| Modality | Method | Output |
| --- | --- | --- |
| Telemetry | Weighted PRI | 0–100 risk |
| Image | Water / waste colour-texture proxies | 0–100 visual score |
| Text | Fixed sanitation taxonomy | 0–100 signal |

**Fusion:** weighted average — telemetry 60%, image 25%, text 15%.

<!-- Presenter: emphasise deterministic + on-premise; no ML model ever leaves the box. -->

---

## Live run (real data this session)

```text
POST /data/refresh-weather  ->  ingested 5 Open-Meteo observations
/health                     ->  data_mode: mixed_sources, 8 locations

Image evidence  -> visual water 55.5 · waste 39.7 · quality ok
Text evidence   -> signal 70.0 · {standing_water, drainage_blockage, odor, rodent}

POST /evidence/fuse/MUC-NEU-05
  -> score 27.1
     = telemetry 4.5 @ 60%  +  visual 55.5 @ 25%  +  text 70 @ 15%
```

<!-- Presenter: concrete proof the fusion favours hard sensor data while still lifting
activity-driven locations. -->

---

## Human-in-the-loop governance

- Work orders start `pending_approval` — **nothing is sent automatically**.
- `POST /work-orders/{id}/decision` records **approve/reject + reviewer + time**.
- A decided order is **locked** (HTTP 409 on re-decision).
- Every decision appears in the audit feed.

<!-- Presenter: this is the compliance story — the system recommends, humans decide. -->

---

## Provenance you can trust

- Telemetry is tagged **synthetic vs live**.
- Dashboards report `data_mode`: `live_connector`, `synthetic_training_snapshot`,
  or `mixed_sources`.
- Public weather = **exposure proxy**; reports = **unverified triage evidence**.
- Limitations are stated on every data surface.

<!-- Presenter: honest labelling is a feature, not a disclaimer. -->

---

## API surface (v1)

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/telemetry/ingest` | Store a reading and score PRI |
| GET | `/risks/heatmap` · `/risks/export.csv` | Geo risk + CSV export |
| POST | `/data/refresh-weather` · `/data/refresh-munich-reports` | Live feeds |
| POST | `/evidence/image` · `/evidence/text` | Multimodal ingestion |
| POST | `/evidence/fuse/{sector_id}` | Weighted fusion |
| POST | `/agents/trigger-dispatch` | Draft a reviewed work order |
| POST | `/work-orders/{id}/decision` | Human approve / reject |

<!-- Presenter: OpenAPI docs auto-served at /docs. -->

---

## Quality & deployment

- **29 automated tests**: risk, store, agents, API, and multimodal.
- **GitHub Actions CI** runs tests + builds the Next.js dashboard.
- **Docker Compose** one-command stack (API + dashboard).
- Clients: Next.js command dashboard **and** Streamlit shareable dashboard.

<!-- Presenter: reproducibility lowers the barrier to a pilot. -->

---

## Roadmap

1. Connect authorised drainage / waste / inspection feeds for a real pilot.
2. Swap heuristic image proxies for an on-prem vision model (same boundary).
3. Persist fusion outcomes and field verification for calibration.
4. Retention policy, access control, DPIA, regional hosting.
5. Outcome metrics: prioritisation time, response time, false-alert rate.

<!-- Presenter: close with a credible path from prototype to procurement. -->

---

## Claims to avoid

Do **not** say UrbanGuard:

- detects disease,
- proves contamination,
- predicts infection, or
- replaces inspectors.

Say it **prioritises sanitation signals for human-reviewed field verification**.

<!-- Presenter: repeat this boundary; it builds trust with officials. -->

---

# UrbanGuard AI

### Prioritise. Explain. Approve.

<!-- Presenter: Q&A. Repository: github.com/NikhilRaman12/UrbanGuard-Ai -->
