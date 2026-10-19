# UrbanGuard AI — Google AI Services Integration

## Brief Description of Our Solution

**UrbanGuard AI** is a sovereign municipal sanitation and pathogen intelligence platform for Munich city operations. It ingests real sensor telemetry, Open-Meteo weather data, and citizen Open311 reports to compute a transparent **Pathogen Risk Index (PRI)** for each city district. The system then uses **Google Gemini 2.0 Flash** to generate actionable AI risk narratives, multilingual citizen advisories (DE/EN/FR/IT), and conversational Q&A over live risk data — all while keeping dispatches human-approved and auditable.

---

## How We Leverage Google Services

### 1. 🤖 Google Gemini 2.0 Flash (Primary AI Engine)
**SDK**: `google-generativeai` Python package

| Feature | Gemini Role |
|---------|-------------|
| **AI Risk Narratives** | Per-district risk analysis from PRI components → concise 120-word operational narrative |
| **Multilingual Advisories** | DE/EN/FR/IT citizen safety notices generated on dispatch |
| **Conversational Q&A** | Operators chat with live risk data: *"Which district is most critical today?"* |
| **Structured JSON output** | Advisory generation uses structured prompting for deterministic JSON output |

**Endpoint**: `POST /api/v1/ai/analyze` — on-demand Gemini analysis per sector
**Endpoint**: `POST /api/v1/ai/chat` — conversational AI over live risk snapshot
**Endpoint**: `GET /api/v1/ai/status` — Google AI configuration status

---

### 2. 🧠 Gemma (Fallback / Offline Mode)
When `GEMINI_API_KEY` is not configured or the Gemini API is unreachable, UrbanGuard falls back to **Gemma-style deterministic templates** — structured, language-appropriate advisory text that mirrors the tone and format of Gemini's output. This ensures the platform remains functional in air-gapped municipal environments (EU sovereignty requirement).

---

### 3. ☁️ Google Cloud Vertex AI
**SDK**: `google-cloud-aiplatform`

For **production Cloud Run deployment**, UrbanGuard switches from the Gemini API key path to **Vertex AI with Application Default Credentials (ADC)**:

```python
# Set USE_VERTEX_AI=true in Cloud Run environment
if USE_VERTEX and VERTEX_PROJECT:
    vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
    model = GenerativeModel(GEMINI_MODEL)  # No API key needed, uses ADC
```

---

### 4. 🚀 Google Cloud Run
Both the **FastAPI backend** and **Next.js frontend** are containerised and deployed to Cloud Run via `cloudbuild.yaml`. Zero cold-start cost at idle, scales instantly, native Secret Manager + Cloud Logging integration.

---

### 5. 🔑 Google Cloud Secret Manager
API keys are never baked into container images. `--set-secrets=GEMINI_API_KEY=urbanguard-gemini-key:latest` injects them at runtime.

---

### 6. 📋 Google Cloud Logging
All agent steps emit structured log entries to Cloud Logging when deployed — creating a tamper-evident municipal audit trail.

---

### 7. 🔐 Google Auth / Application Default Credentials
`google-auth` SDK enables Vertex AI authentication from Cloud Run service accounts — no key files on disk.

---

### 8. 🌐 Google Fonts
Manrope and DM Mono from Google Fonts power the dashboard's premium aesthetic.

---

## Architecture

```
Browser (Next.js — Cloud Run)
  ├── Risk Map + Gemini AI Narrative (per location)
  └── Gemini AI Advisor Chat Panel

FastAPI Backend (Python — Cloud Run)
  ├── /api/v1/ai/analyze  ──► gemini_agent.py ──► Gemini 2.0 Flash
  ├── /api/v1/ai/chat     ──► gemini_agent.py ──► Gemini 2.0 Flash
  ├── /api/v1/agents/trigger-dispatch ──► agents.py ──► Gemini
  ├── SQLite + PRI Risk Engine
  ├── Cloud Logging (audit trail)
  └── Secret Manager (API key)

gemini_agent.py (3 paths)
  ├── Gemini API path   (GEMINI_API_KEY) → google-generativeai
  ├── Vertex AI path    (USE_VERTEX_AI=true + ADC) → google-cloud-aiplatform
  └── Gemma fallback    (no credentials) → deterministic templates
```

---

## Quick Start

```bash
# Get free Gemini key: https://aistudio.google.com/app/apikey
$env:GEMINI_API_KEY="your-key"

# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (already running)
# http://localhost:3000
# → Select any risk location → Gemini AI narrative appears
# → Use the Gemini AI Advisor chat panel
# → Trigger dispatch → multilingual Gemini advisories generated
```

---

## New API Endpoints

| Method | Endpoint | Google Service | Description |
|--------|----------|---------------|-------------|
| `POST` | `/api/v1/ai/analyze` | Gemini 2.0 Flash | AI risk narrative + multilingual advisories |
| `POST` | `/api/v1/ai/chat` | Gemini 2.0 Flash | Conversational Q&A over live risk data |
| `GET`  | `/api/v1/ai/status` | — | Google AI configuration status |
| `GET`  | `/health` | — | Enriched with `google_ai` status block |

---

## Files Added / Modified

| File | Change |
|------|--------|
| `backend/app/gemini_agent.py` | **NEW** — Gemini SDK, Vertex AI, Gemma fallback |
| `backend/app/agents.py` | Updated to call Gemini for narratives & advisories |
| `backend/app/main.py` | Added `/api/v1/ai/*` endpoints |
| `backend/requirements.txt` | Added Google AI Python packages |
| `frontend/app/page.tsx` | Gemini chat panel + AI narrative block |
| `frontend/app/styles.css` | Google AI UI styles |
| `cloudbuild.yaml` | **NEW** — Cloud Build + Cloud Run CI/CD |
| `.env.example` | **NEW** — Google AI environment template |
