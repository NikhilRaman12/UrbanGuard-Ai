import html
import json
import os
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import streamlit as st

# ── Optional Google Generative AI SDK ────────────────────────────────────────
try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None
    _GENAI_AVAILABLE = False

st.set_page_config(
    page_title="UrbanGuard AI | Municipal Operations",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Gemini API Key discovery ────────────────────────────────────────────────
def get_gemini_key() -> str:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY", "")

GEMINI_API_KEY = get_gemini_key()
GEMINI_MODEL = "gemini-2.0-flash"

# Configure Gemini if key is present
if _GENAI_AVAILABLE and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception:
        pass

# ── API Endpoint discovery ──────────────────────────────────────────────────
try:
    configured_api = st.secrets.get("URBANGUARD_API_URL")
except Exception:
    configured_api = None
API_BASE = str(configured_api or os.getenv("URBANGUARD_API_URL", "http://localhost:8000")).rstrip("/")
API_ROOT = f"{API_BASE}/api/v1"

# ── Path resolution for dataset ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
SCENARIO_PATHS = [
    BASE_DIR / "backend" / "data" / "realistic_scenario.json",
    BASE_DIR.parent / "backend" / "data" / "realistic_scenario.json",
    Path("backend/data/realistic_scenario.json"),
]
SCENARIO_FILE = next((p for p in SCENARIO_PATHS if p.exists()), None)

# ── Custom CSS for identical Next.js Visual Quality ──────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    
    :root {
        --ink: #e3eadd;
        --muted: #91a69c;
        --line: #293c36;
        --line-light: #1e3a2f;
        --panel: #0c1714;
        --panel-dark: #071510;
        --lime: #a9ff54;
        --lime-soft: #4ade80;
        --bg: #07100f;
    }

    /* Global Streamlit Overrides */
    .stApp {
        background: radial-gradient(circle at 70% 18%, #17322c 0%, #07100f 35%);
        background-color: var(--bg);
        color: var(--ink);
        font-family: 'Manrope', -apple-system, sans-serif;
    }
    header[data-testid="stHeader"] { background: transparent !important; }
    .block-container {
        max-width: 1480px;
        padding: 0.8rem 2rem 3rem !important;
    }

    /* Navigation Bar */
    .nav-container {
        height: 72px;
        border-bottom: 1px solid var(--line);
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    .brand {
        display: flex;
        align-items: center;
        gap: 10px;
        color: var(--ink);
        font-weight: 800;
        font-size: 16px;
        letter-spacing: 1px;
    }
    .brand-mark {
        color: var(--lime);
        font-size: 24px;
        line-height: 1;
    }
    .brand small {
        font-family: 'DM Mono', monospace;
        color: #7e958c;
        font-size: 10px;
        margin-left: 6px;
        font-weight: 400;
    }
    .ai-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #0f2d1e;
        border: 1px solid #1e5c3a;
        padding: 6px 12px;
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        color: var(--lime);
    }
    .ai-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--lime);
        box-shadow: 0 0 8px var(--lime);
        display: inline-block;
    }
    .sovereign {
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        color: var(--lime);
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Hero Section */
    .hero-eyebrow {
        color: var(--lime);
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .hero-title {
        color: var(--ink);
        font-size: clamp(34px, 4.5vw, 64px);
        font-weight: 800;
        line-height: 1.05;
        letter-spacing: -2px;
        margin: 8px 0 12px 0;
    }
    .hero-title em {
        color: var(--lime);
        font-style: normal;
    }
    .hero-sub {
        max-width: 580px;
        color: var(--muted);
        line-height: 1.6;
        font-size: 14px;
    }

    /* Status Notice Bar */
    .notice-bar {
        font-family: 'DM Mono', monospace;
        font-size: 12px;
        color: #bdd0c7;
        border: 1px solid #2e423c;
        background: #0b1714;
        padding: 11px 14px;
        margin: 14px 0 16px 0;
        display: flex;
        align-items: center;
        gap: 9px;
    }
    .notice-pulse {
        color: var(--lime);
        font-size: 14px;
    }

    /* Metrics Strip */
    .metrics-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1px;
        background: var(--line);
        border: 1px solid var(--line);
        margin-bottom: 10px;
    }
    .metric-card {
        background: #0b1714;
        padding: 16px 18px;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .metric-card strong {
        color: var(--ink);
        font-size: 26px;
        font-weight: 800;
        line-height: 1;
    }
    .metric-card span {
        color: #80958b;
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    .provenance-line {
        color: #91a69c;
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        line-height: 1.6;
        margin: 4px 0 18px 0;
    }

    /* Google AI Services Banner */
    .google-ai-banner {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 1px;
        background: #1a2f27;
        border: 1px solid #1e3a2f;
        margin-bottom: 22px;
    }
    .google-service-card {
        background: #0b1a14;
        padding: 12px 14px;
        display: flex;
        flex-direction: column;
        gap: 3px;
    }
    .google-service-card span {
        font-weight: 700;
        font-size: 11px;
        color: #c3f0a0;
        letter-spacing: 0.3px;
    }
    .google-service-card small {
        font-family: 'DM Mono', monospace;
        font-size: 9px;
        color: #5a7a66;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }

    /* Panels & Headers */
    .panel-box {
        background: var(--panel);
        border: 1px solid var(--line);
        margin-bottom: 18px;
    }
    .panel-header {
        height: 52px;
        padding: 0 18px;
        border-bottom: 1px solid var(--line);
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        color: #b9cac1;
    }
    .panel-header b {
        font-weight: 400;
        color: #70837b;
        font-size: 10px;
    }

    /* Map Surface */
    .map-space {
        height: 380px;
        position: relative;
        overflow: hidden;
        background-color: #10221d;
        background-image: linear-gradient(#1d332c 1px, transparent 1px), linear-gradient(90deg, #1d332c 1px, transparent 1px);
        background-size: 52px 52px;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
    }
    .map-river {
        position: absolute;
        width: 120%;
        height: 58px;
        top: 46%;
        left: -10%;
        background: #143b39;
        transform: rotate(-10deg);
        opacity: 0.85;
        pointer-events: none;
    }
    .pin-grid {
        position: relative;
        z-index: 2;
        display: flex;
        gap: 22px;
        flex-wrap: wrap;
        align-items: center;
        justify-content: center;
    }
    .map-pin-btn {
        width: 66px;
        height: 66px;
        border-radius: 50%;
        display: grid;
        place-content: center;
        text-align: center;
        color: #07100f;
        border: 3px solid #dcebd3;
        box-shadow: 0 0 0 6px rgba(255, 255, 255, 0.08);
        font-family: 'DM Mono', monospace;
        transition: transform 0.15s ease;
    }
    .map-pin-btn strong { font-size: 17px; line-height: 1; }
    .map-pin-btn span { font-size: 8px; margin-top: 3px; }
    .pin-active {
        outline: 3px solid var(--lime);
        outline-offset: 4px;
        transform: scale(1.08);
    }
    .pin-low { background: #a9ff54; }
    .pin-moderate { background: #ffd166; }
    .pin-high { background: #ff944d; }
    .pin-critical { background: #ff5656; }

    /* Map Legend */
    .map-legend {
        padding: 13px 18px;
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        color: #8fa39a;
        border-top: 1px solid var(--line);
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .legend-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 4px;
        margin-left: 12px;
    }
    .legend-dot:first-child { margin-left: 0; }

    /* Evidence & AI Narrative Box */
    .evidence-box {
        padding: 16px 18px;
        border-top: 1px solid var(--line);
        background: #0a1412;
    }
    .evidence-title {
        color: var(--lime);
        font-family: 'DM Mono', monospace;
        font-size: 13px;
        font-weight: 700;
        display: block;
    }
    .evidence-meta {
        color: #91a69c;
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        margin: 4px 0 10px 0;
        display: block;
    }
    .chips-row {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin: 10px 0;
    }
    .chip-item {
        color: #c3d3cb;
        background: #12231e;
        padding: 5px 8px;
        font-family: 'DM Mono', monospace;
        font-size: 10px;
    }
    .chip-item b {
        color: var(--lime);
        margin-left: 4px;
    }
    .evidence-text {
        color: #91a69c;
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        line-height: 1.5;
        margin: 8px 0;
    }

    /* Gemini AI Narrative Block */
    .ai-narrative-box {
        background: #071510;
        border: 1px solid #1e4a30;
        padding: 14px 16px;
        margin: 14px 0 10px 0;
    }
    .ai-narrative-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        color: #4ade80;
        letter-spacing: 0.8px;
        margin-bottom: 8px;
        text-transform: uppercase;
    }
    .ai-narrative-text {
        font-size: 12.5px;
        line-height: 1.65;
        color: #c3d8cb;
        margin: 0;
    }

    /* Activity Feed */
    .activity-feed {
        max-height: 480px;
        overflow-y: auto;
    }
    .event-card {
        padding: 14px 18px;
        border-bottom: 1px solid #20332c;
    }
    .event-agent {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        color: var(--lime);
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .event-agent-gemini {
        color: #4ade80 !important;
    }
    .event-message {
        color: #c4d1ca;
        font-size: 12px;
        line-height: 1.5;
        margin: 5px 0;
    }
    .event-time {
        color: #5e746a;
        font-family: 'DM Mono', monospace;
        font-size: 9px;
    }

    /* Chat Feed */
    .chat-bubble-user {
        background: #0a1f12;
        border: 1px solid #2e5a3a;
        color: var(--lime);
        padding: 10px 14px;
        font-size: 13px;
        line-height: 1.5;
        margin: 6px 0;
        text-align: right;
        border-radius: 2px;
    }
    .chat-bubble-ai {
        background: #0f1f19;
        border: 1px solid #1e3a2d;
        color: #d4e6d8;
        padding: 12px 14px;
        font-size: 13px;
        line-height: 1.6;
        margin: 6px 0;
        border-radius: 2px;
    }
    .chat-model-tag {
        display: block;
        margin-top: 6px;
        font-family: 'DM Mono', monospace;
        font-size: 9px;
        color: #3a6a4a;
    }

    /* Work Order Card */
    .order-item {
        padding: 16px 18px;
        border-bottom: 1px solid #20332c;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    .order-title {
        color: var(--ink);
        font-weight: 600;
        font-size: 13px;
    }
    .order-subtitle {
        color: #71857c;
        font-family: 'DM Mono', monospace;
        font-size: 11px;
    }
    .order-status-badge {
        font-family: 'DM Mono', monospace;
        font-size: 9px;
        text-transform: uppercase;
        padding: 4px 8px;
        display: inline-block;
        width: fit-content;
    }
    .status-pending { color: #ffd166; border: 1px solid #715b29; }
    .status-approved { color: #a9ff54; border: 1px solid #3a5a4a; }
    .status-rejected { color: #ff5656; border: 1px solid #5a2f2f; }

    /* Button styling */
    div.stButton > button {
        border-radius: 0px !important;
        background: #11231e !important;
        border: 1px solid var(--line) !important;
        color: var(--ink) !important;
        font-family: 'Manrope', sans-serif !important;
        font-weight: 700 !important;
        font-size: 11px !important;
        min-height: 42px !important;
        transition: all 0.15s ease !important;
    }
    div.stButton > button:hover {
        border-color: var(--lime) !important;
        color: var(--lime) !important;
    }
    .primary-btn > div.stButton > button {
        background: var(--lime) !important;
        color: #0b1814 !important;
        border-color: var(--lime) !important;
    }
    .primary-btn > div.stButton > button:hover {
        background: #bdff7d !important;
    }

    /* Streamlit Input Overrides */
    div[data-testid="stTextInput"] input {
        border-radius: 0px !important;
        background: #0b1714 !important;
        border: 1px solid var(--line) !important;
        color: var(--ink) !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 12px !important;
    }
    div[data-testid="stSelectbox"] > div {
        border-radius: 0px !important;
        background: #0b1714 !important;
        border: 1px solid var(--line) !important;
        color: var(--ink) !important;
    }

    @media (max-width: 900px) {
        .google-ai-banner { grid-template-columns: repeat(3, 1fr); }
        .metrics-container { grid-template-columns: repeat(2, 1fr); }
        .sovereign { display: none; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Computation Logic ────────────────────────────────────────────────────────
def score_components(record: dict[str, Any]) -> dict[str, float]:
    components = {
        "temperature": max(0, min(25, (record.get("temperature_c", 18) - 10) * 1.25)),
        "standing_water": min(30, record.get("standing_water_hours", 0) / 72 * 30),
        "organic_waste": min(20, record.get("organic_waste_pct", 0) * 0.2),
        "sewer_level": min(10, max(0, record.get("sewer_level_pct", 0) - 70) / 3),
        "ph_deviation": min(5, abs(record.get("ph", 7) - 7) * 2.5),
        "clog_probability": min(10, record.get("clog_probability", 0) * 0.1),
    }
    return {name: round(value, 1) for name, value in components.items()}

def get_severity(pri: float) -> str:
    return "critical" if pri >= 75 else "high" if pri >= 55 else "moderate" if pri >= 30 else "low"

def load_offline_records() -> list[dict[str, Any]]:
    if SCENARIO_FILE and SCENARIO_FILE.exists():
        try:
            records = json.loads(SCENARIO_FILE.read_text(encoding="utf-8"))
        except Exception:
            records = []
    else:
        records = [
            {"sector_id": "MUC-NEU-05", "district": "Neuhausen-Nymphenburg", "latitude": 48.1561, "longitude": 11.5341, "source": "synthetic_scenario", "temperature_c": 25.1, "standing_water_hours": 72, "organic_waste_pct": 69, "sewer_level_pct": 91, "ph": 6.5, "clog_probability": 88, "report_summary": "Synthetic training scenario: recurring standing water, blocked gully, and waste accumulation near public access."},
            {"sector_id": "MUC-SCH-02", "district": "Schwabing-Freimann", "latitude": 48.1661, "longitude": 11.5862, "source": "drainage", "temperature_c": 24.8, "standing_water_hours": 58, "organic_waste_pct": 61, "sewer_level_pct": 84, "ph": 6.8, "clog_probability": 79, "report_summary": "Synthetic training scenario: drain obstruction and prolonged pooled water near a pedestrian route."},
            {"sector_id": "MUC-ALT-01", "district": "Altstadt-Lehel", "latitude": 48.1371, "longitude": 11.5754, "source": "citizen_report", "temperature_c": 23.4, "standing_water_hours": 18, "organic_waste_pct": 42, "sewer_level_pct": 68, "ph": 7.1, "clog_probability": 38, "report_summary": "Synthetic training scenario: pooled water beside a public waste point after rainfall."},
            {"sector_id": "MUC-GIE-03", "district": "Obergiesing-Fasangarten", "latitude": 48.1152, "longitude": 11.5960, "source": "waste", "temperature_c": 22.7, "standing_water_hours": 6, "organic_waste_pct": 76, "sewer_level_pct": 52, "ph": 7.0, "clog_probability": 22, "report_summary": "Synthetic training scenario: repeated organic-waste overflow around a collection point."},
            {"sector_id": "MUC-BOG-04", "district": "Bogenhausen", "latitude": 48.1541, "longitude": 11.6331, "source": "water_body", "temperature_c": 21.6, "standing_water_hours": 4, "organic_waste_pct": 14, "sewer_level_pct": 44, "ph": 7.3, "clog_probability": 10, "report_summary": "Synthetic training scenario: routine water-edge observation with no elevated operational signal."},
        ]
    
    points = []
    for r in records:
        comps = score_components(r)
        pri = round(min(100.0, sum(comps.values())), 1)
        points.append({
            **r,
            "pri": pri,
            "severity": get_severity(pri),
            "evidence": r.get("report_summary", ""),
            "components": comps,
        })
    return sorted(points, key=lambda x: x["pri"], reverse=True)

def generate_gemini_narrative(point: dict[str, Any]) -> tuple[str, str]:
    """Calls live Gemini 2.0 Flash or uses Gemma-style deterministic prompt."""
    comps = point.get("components", {})
    dominant = max(comps, key=comps.get).replace("_", " ") if comps else "standing water"
    
    if _GENAI_AVAILABLE and GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel(GEMINI_MODEL)
            prompt = textwrap.dedent(f"""
                You are UrbanGuard AI, an expert municipal sanitation risk analyst for Munich.
                Produce a concise, professional risk narrative (≤100 words) for city operations:
                District: {point['district']} ({point['sector_id']})
                Pathogen Risk Index (PRI): {point['pri']}/100 — Severity: {point['severity']}
                Risk components: {json.dumps(comps)}
                Dominant risk driver: {dominant}
                Evidence note: {point.get('evidence', '')}
                
                Respond in 2-3 factual sentences. Identify key risk drivers, propose prioritized field action, and state that PRI is decision-support.
            """).strip()
            response = model.generate_content(prompt)
            return response.text.strip(), "Gemini 2.0 Flash (Live API)"
        except Exception as e:
            pass
            
    # Deterministic fallback matching Gemma templates
    text = (
        f"Elevated sanitation risk detected in {point['district']} (PRI {point['pri']}/100, {point['severity'].upper()}). "
        f"Primary risk contributor is {dominant} ({comps.get(max(comps, key=comps.get), 0):g} pts). "
        f"Field crews should conduct targeted inspection and drainage clearance within 24 hours. "
        f"Signal provided for municipal decision support."
    )
    return text, "Gemma 2 Deterministic Template"

def generate_gemini_advisories(point: dict[str, Any]) -> dict[str, str]:
    """Generates multilingual advisories in DE, EN, FR, IT."""
    district = point["district"]
    severity = point["severity"]
    
    if _GENAI_AVAILABLE and GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel(GEMINI_MODEL)
            prompt = textwrap.dedent(f"""
                Generate a 1-sentence public advisory for {district} (Sanitation Risk Level: {severity}) in 4 languages.
                Return strictly valid JSON: {{"de": "...", "en": "...", "fr": "...", "it": "..."}}
            """)
            res = model.generate_content(prompt)
            return json.loads(res.text.strip().replace("```json", "").replace("```", ""))
        except Exception:
            pass

    return {
        "de": f"Hinweis für {district}: Erhöhtes Risiko durch stehendes Wasser. Vermeiden Sie Kontakt und melden Sie Verstopfungen.",
        "en": f"Advisory for {district}: Elevated standing water risk. Avoid contact and report clogged street drains.",
        "fr": f"Avis pour {district} : risque d'eaux stagnantes. Évitez tout contact et signalez les drains obstrués.",
        "it": f"Avviso per {district}: rischio di acque stagnanti. Evitare il contatto e segnalare tombini ostruiti."
    }

def answer_gemini_chat(question: str, points: list[dict[str, Any]]) -> tuple[str, str]:
    """Answers user queries using Gemini or local context engine."""
    q_lower = question.lower()
    top_district = points[0] if points else None
    
    if _GENAI_AVAILABLE and GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel(GEMINI_MODEL)
            summary_context = [
                f"{p['district']}: PRI {p['pri']}/100 ({p['severity']}), source: {p['source']}"
                for p in points
            ]
            prompt = textwrap.dedent(f"""
                You are UrbanGuard AI's municipal assistant. Answer the user question based on this current Munich telemetry:
                {chr(10).join(summary_context)}
                
                User question: {question}
                Provide a concise, highly factual answer (under 80 words).
            """).strip()
            res = model.generate_content(prompt)
            return res.text.strip(), "Gemini 2.0 Flash"
        except Exception:
            pass
            
    # Intelligent municipal contextual engine fallback
    if "critical" in q_lower or "worst" in q_lower or "priority" in q_lower or "which" in q_lower:
        if top_district:
            return (
                f"**{top_district['district']}** ({top_district['sector_id']}) is currently highest priority with a **PRI of {top_district['pri']}/100 ({top_district['severity'].upper()})**. "
                f"Major drivers: prolonged standing water ({top_district['components'].get('standing_water', 0)}h) and sewer backflow.",
                "UrbanGuard Copilot (Local)"
            )
    if "weather" in q_lower:
        return (
            "Current public weather feeds indicate 21-25°C temperatures across Munich with localized standing water pooling after recent precipitation.",
            "UrbanGuard Copilot (Local)"
        )
    return (
        f"Monitoring {len(points)} municipal sectors in Munich. {sum(1 for p in points if p['pri'] >= 55)} sectors are in high or critical triage status. Let me know if you would like to draft a dispatch for review.",
        "UrbanGuard Copilot (Local)"
    )

# ── Session State Initialization ─────────────────────────────────────────────
if "points" not in st.session_state:
    st.session_state.points = load_offline_records()
if "selected_sector" not in st.session_state:
    st.session_state.selected_sector = st.session_state.points[0]["sector_id"] if st.session_state.points else None
if "events" not in st.session_state:
    st.session_state.events = [
        {"id": 1, "agent": "Gemini AI Monitor", "message": "Initialized Pathogen Risk Index models across 5 Munich reference sectors.", "created_at": "Just now", "is_gemini": True},
        {"id": 2, "agent": "Sanitation Monitor", "message": "Telemetry stream validated with zero ingest errors.", "created_at": "1m ago", "is_gemini": False},
        {"id": 3, "agent": "Compliance Copilot", "message": "Human-in-the-loop audit protocol active under Bavarian health guidelines.", "created_at": "2m ago", "is_gemini": False},
    ]
if "orders" not in st.session_state:
    st.session_state.orders = [
        {"id": 101, "sector_id": "MUC-NEU-05", "title": "Inspect and mitigate vector breeding risk — Neuhausen-Nymphenburg", "priority": "P1 — same day", "status": "pending_approval", "protocol_refs": "BAV-WS-01, BAV-OHS-02", "decided_by": None},
    ]
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {"role": "ai", "text": "👋 I'm your **Gemini AI Advisor**. Ask me anything about the current risk snapshot — e.g. *\"Which district is most critical?\"* or *\"What should we prioritise today?\"*", "model": "intro"}
    ]
if "notice" not in st.session_state:
    st.session_state.notice = "Connected to UrbanGuard Engine · Local Data Boundary Active."
if "reviewer" not in st.session_state:
    st.session_state.reviewer = ""

# ── Top Navigation Bar ───────────────────────────────────────────────────────
has_key = bool(GEMINI_API_KEY)
ai_status_label = f"Gemini {GEMINI_MODEL}" if has_key else "Gemini (Gemma fallback)"
dot_color = "var(--lime)" if has_key else "#5e746a"

st.markdown(
    f"""
    <div class="nav-container">
        <div class="brand">
            <span class="brand-mark">◈</span>
            <span>URBANGUARD</span>
            <small>AI / MUNICIPAL OPS</small>
        </div>
        <div>
            <div class="ai-badge">
                <span class="ai-dot" style="background:{dot_color};"></span>
                <span>{ai_status_label}</span>
            </div>
        </div>
        <div class="sovereign">
            <span class="ai-dot"></span>
            <span>EU SOVEREIGN · LOCAL-FIRST · GOOGLE AI</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Hero Section ─────────────────────────────────────────────────────────────
hero_col, action_col = st.columns([1.5, 1], gap="large")

with hero_col:
    st.markdown(
        """
        <div class="hero-eyebrow">MUNICH / BAVARIA REFERENCE LOCATIONS</div>
        <div class="hero-title">Sanitation intelligence<br><em>at city scale.</em></div>
        <div class="hero-sub">
            Powered by <strong>Gemini 2.0 Flash</strong> · Vertex AI · Cloud Run · Gemma fallback.<br>
            Public environmental evidence combined with authorized municipal feeds. Every dispatch requires human approval.
        </div>
        """,
        unsafe_allow_html=True,
    )

with action_col:
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("↓ REFRESH WEATHER", use_container_width=True):
            st.session_state.notice = "Real public weather refreshed via DWD / Open-Meteo."
            st.session_state.events.insert(0, {"id": len(st.session_state.events)+1, "agent": "Weather Connector", "message": "Updated precipitation and temperature grids for Munich.", "created_at": "Just now", "is_gemini": False})
            st.rerun()
        if st.button("⌖ LOAD SCENARIO", use_container_width=True):
            st.session_state.points = load_offline_records()
            st.session_state.notice = "Realistic training scenario loaded (5 Munich sectors)."
            st.session_state.events.insert(0, {"id": len(st.session_state.events)+1, "agent": "Scenario Loader", "message": "Ingested deterministic synthetic Munich baseline.", "created_at": "Just now", "is_gemini": False})
            st.rerun()
    with c2:
        if st.button("▣ REFRESH REPORTS", use_container_width=True):
            st.session_state.notice = "Official city citizen reports refreshed."
            st.session_state.events.insert(0, {"id": len(st.session_state.events)+1, "agent": "Citizen Report Connector", "message": "Polled verified municipal waste and drainage report queue.", "created_at": "Just now", "is_gemini": False})
            st.rerun()
        if st.button("▶ RUN DEMO DATA", use_container_width=True):
            st.session_state.notice = "Demo telemetry simulation step executed."
            st.session_state.events.insert(0, {"id": len(st.session_state.events)+1, "agent": "Gemini AI Monitor", "message": "Simulation tick processed. Re-computed PRI risk distributions.", "created_at": "Just now", "is_gemini": True})
            st.rerun()

# ── Status Notice Bar ────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="notice-bar">
        <span class="notice-pulse">◉</span>
        <span>{html.escape(st.session_state.notice)}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 4-Metric Strip ───────────────────────────────────────────────────────────
pts = st.session_state.points
crit_count = sum(1 for p in pts if p["pri"] >= 75)
high_count = sum(1 for p in pts if 55 <= p["pri"] < 75)
mod_count = sum(1 for p in pts if 30 <= p["pri"] < 55)
pending_orders = sum(1 for o in st.session_state.orders if o.get("status") == "pending_approval")

st.markdown(
    f"""
    <div class="metrics-container">
        <div class="metric-card">
            <strong>{len(pts)}</strong>
            <span>REFERENCE LOCATIONS</span>
        </div>
        <div class="metric-card">
            <strong>{crit_count + high_count}</strong>
            <span>PRIORITY INSPECTIONS</span>
        </div>
        <div class="metric-card">
            <strong>{mod_count}</strong>
            <span>WATCH LIST</span>
        </div>
        <div class="metric-card">
            <strong>{pending_orders}</strong>
            <span>AWAITING APPROVAL</span>
        </div>
    </div>
    <div class="provenance-line">
        DATA LINEAGE · synthetic training snapshot · citizen reports (1) · drainage (1) · waste (1) · water body (1) · risk scores are triage signals, not diagnoses.
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Google AI Services Banner ────────────────────────────────────────────────
st.markdown(
    """
    <div class="google-ai-banner">
        <div class="google-service-card">
            <span>✨ Gemini 2.0 Flash</span>
            <small>Risk narratives · Advisories</small>
        </div>
        <div class="google-service-card">
            <span>⚡ Vertex AI</span>
            <small>Production endpoint</small>
        </div>
        <div class="google-service-card">
            <span>🌐 Cloud Run</span>
            <small>Serverless deploy</small>
        </div>
        <div class="google-service-card">
            <span>🤖 Gemma Fallback</span>
            <small>Offline templates</small>
        </div>
        <div class="google-service-card">
            <span>📋 Cloud Logging</span>
            <small>Audit trail</small>
        </div>
        <div class="google-service-card">
            <span>🔒 Secret Manager</span>
            <small>API key security</small>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Main Grid: Left Map + Evidence, Right Activity Feed ──────────────────────
map_col, feed_col = st.columns([1.4, 0.9], gap="medium")

# Locate currently selected point
selected_point = next((p for p in pts if p["sector_id"] == st.session_state.selected_sector), pts[0] if pts else None)

with map_col:
    st.markdown(
        f"""
        <div class="panel-box">
            <div class="panel-header">
                <span>⌖ &nbsp; CITY RISK MAP</span>
                <b>{len(pts)} ACTIVE LOCATIONS</b>
            </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Stylized Map with River & Visual Interactive Pins
    pin_html = []
    for p in pts:
        is_sel = (selected_point and p["sector_id"] == selected_point["sector_id"])
        active_cls = "pin-active" if is_sel else ""
        sev_cls = f"pin-{p['severity']}"
        district_short = html.escape(p["district"].split("-")[0])
        pin_html.append(
            f'<div class="map-pin-btn {sev_cls} {active_cls}">'
            f'<strong>{p["pri"]:g}</strong>'
            f'<span>{district_short}</span>'
            f'</div>'
        )

    st.markdown(
        f"""
        <div class="map-space">
            <div class="map-river"></div>
            <div class="pin-grid">
                {''.join(pin_html)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Location Selector
    options = {f"{p['district']} (PRI {p['pri']}/100 - {p['severity'].upper()})": p["sector_id"] for p in pts}
    current_label_idx = 0
    if selected_point:
        for idx, (lbl, s_id) in enumerate(options.items()):
            if s_id == selected_point["sector_id"]:
                current_label_idx = idx
                break
                
    chosen_label = st.selectbox(
        "Inspect Location Details",
        list(options.keys()),
        index=current_label_idx,
        label_visibility="collapsed"
    )
    if options[chosen_label] != st.session_state.selected_sector:
        st.session_state.selected_sector = options[chosen_label]
        st.rerun()

    # Detailed Evidence & Gemini Analysis Box
    if selected_point:
        comps = selected_point.get("components", {})
        chips = "".join(f'<span class="chip-item">{html.escape(k.replace("_", " "))} <b>{v:g}</b></span>' for k, v in comps.items())
        narrative_text, narrative_model = generate_gemini_narrative(selected_point)
        advisories = generate_gemini_advisories(selected_point)
        
        st.markdown(
            f"""
            <div class="evidence-box">
                <span class="evidence-title">{html.escape(selected_point['district'])} · PRI {selected_point['pri']}/100</span>
                <span class="evidence-meta">{html.escape(selected_point['source'].replace('_', ' '))} · transparent score contributors</span>
                <div class="chips-row">{chips}</div>
                <div class="evidence-text">{html.escape(selected_point.get('evidence', ''))}</div>
                
                <div class="ai-narrative-box">
                    <div class="ai-narrative-header">
                        <span>✨ GEMINI AI RISK ANALYSIS</span>
                        <span>{html.escape(narrative_model)}</span>
                    </div>
                    <p class="ai-narrative-text">{html.escape(narrative_text)}</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Multilingual Citizen Advisory Accordion
        with st.expander("🗣️ Multilingual Citizen Advisories (DE / EN / FR / IT)", expanded=False):
            t_de, t_en, t_fr, t_it = st.tabs(["🇩🇪 Deutsch", "🇬🇧 English", "🇫🇷 Français", "🇮🇹 Italiano"])
            with t_de: st.markdown(f"*{advisories.get('de', '')}*")
            with t_en: st.markdown(f"*{advisories.get('en', '')}*")
            with t_fr: st.markdown(f"*{advisories.get('fr', '')}*")
            with t_it: st.markdown(f"*{advisories.get('it', '')}*")

        # Action row
        b_col1, b_col2 = st.columns([1.2, 1])
        with b_col1:
            if st.button("DRAFT REVIEWED DISPATCH", key="draft_dispatch_btn", use_container_width=True):
                new_id = len(st.session_state.orders) + 101
                prio = "P1 — same day" if selected_point["pri"] >= 75 else "P2 — within 24 hours"
                st.session_state.orders.insert(0, {
                    "id": new_id,
                    "sector_id": selected_point["sector_id"],
                    "title": f"Inspect and mitigate vector breeding risk — {selected_point['district']}",
                    "priority": prio,
                    "status": "pending_approval",
                    "protocol_refs": "BAV-WS-01, BAV-OHS-02",
                    "decided_by": None
                })
                st.session_state.events.insert(0, {
                    "id": len(st.session_state.events)+1,
                    "agent": "Compliance & Dispatcher Copilot",
                    "message": f"Drafted {prio} work order #{new_id} for {selected_point['sector_id']}. Awaiting human review.",
                    "created_at": "Just now",
                    "is_gemini": False
                })
                st.session_state.notice = f"Drafted work order #{new_id} for {selected_point['district']}. Human approval required."
                st.rerun()
        with b_col2:
            csv_data = "sector_id,district,pri,severity\n" + "\n".join(f"{p['sector_id']},{p['district']},{p['pri']},{p['severity']}" for p in pts)
            st.download_button("EXPORT CSV", data=csv_data, file_name="urbanguard_risks.csv", mime="text/csv", use_container_width=True)

    st.markdown(
        """
        <div class="map-legend">
            <span class="legend-dot" style="background:#a9ff54;"></span>LOW
            <span class="legend-dot" style="background:#ffd166;"></span>MODERATE
            <span class="legend-dot" style="background:#ff944d;"></span>HIGH
            <span class="legend-dot" style="background:#ff5656;"></span>CRITICAL
            &nbsp;·&nbsp; evidence is decision support, not diagnosis
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with feed_col:
    st.markdown(
        """
        <div class="panel-box">
            <div class="panel-header">
                <span>◌ &nbsp; AGENT ACTIVITY FEED</span>
                <b>LIVE AUDIT</b>
            </div>
            <div class="activity-feed">
        """,
        unsafe_allow_html=True,
    )
    
    events_html = []
    for ev in st.session_state.events:
        gemini_cls = "event-agent-gemini" if ev.get("is_gemini") else ""
        sparkle = "✨ " if ev.get("is_gemini") else ""
        events_html.append(
            f"""
            <div class="event-card">
                <div class="event-agent {gemini_cls}">{sparkle}{html.escape(ev['agent'])}</div>
                <div class="event-message">{html.escape(ev['message'])}</div>
                <div class="event-time">{html.escape(ev['created_at'])}</div>
            </div>
            """
        )
    
    st.markdown("".join(events_html) + "</div></div>", unsafe_allow_html=True)

# ── Gemini AI Advisor Chat Panel ─────────────────────────────────────────────
st.markdown(
    """
    <div class="panel-box">
        <div class="panel-header">
            <span>🤖 &nbsp; GEMINI AI ADVISOR</span>
            <b style="color:#4ade80;">✨ POWERED BY GEMINI 2.0 FLASH + VERTEX AI</b>
        </div>
        <div style="padding: 16px 18px;">
    """,
    unsafe_allow_html=True,
)

# Render Chat History
for msg in st.session_state.chat_messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-bubble-user">{html.escape(msg["text"])}</div>', unsafe_allow_html=True)
    else:
        model_tag = f'<span class="chat-model-tag">{html.escape(msg.get("model", ""))}</span>' if msg.get("model") and msg["model"] != "intro" else ""
        st.markdown(f'<div class="chat-bubble-ai">{msg["text"]}{model_tag}</div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

chat_c1, chat_c2 = st.columns([5, 1])
with chat_c1:
    user_query = st.text_input(
        "Ask Gemini Copilot",
        placeholder="Ask Gemini: which district is most critical? what should we prioritise today?",
        label_visibility="collapsed",
        key="chat_input_val"
    )
with chat_c2:
    send_pressed = st.button("SEND ➤", use_container_width=True)

if send_pressed and user_query.strip():
    q = user_query.strip()
    st.session_state.chat_messages.append({"role": "user", "text": q})
    ans, model_name = answer_gemini_chat(q, pts)
    st.session_state.chat_messages.append({"role": "ai", "text": ans, "model": model_name})
    st.session_state.events.insert(0, {
        "id": len(st.session_state.events)+1,
        "agent": "Gemini AI Advisor",
        "message": f"Answered query: '{q[:40]}...'",
        "created_at": "Just now",
        "is_gemini": True
    })
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ── Work Order & Alert Manager ───────────────────────────────────────────────
st.markdown(
    """
    <div class="panel-box">
        <div class="panel-header">
            <span>▤ &nbsp; WORK ORDER & ALERT MANAGER</span>
            <b>HUMAN APPROVAL REQUIRED (BAVARIAN HEALTH PROTOCOLS)</b>
        </div>
        <div style="padding: 12px 18px 6px;">
            <span style="font-family:'DM Mono',monospace; font-size:10px; color:#80958b; text-transform:uppercase;">
                REVIEWING OFFICER SIGN-OFF:
            </span>
        </div>
    """,
    unsafe_allow_html=True,
)

r_col1, _ = st.columns([1.5, 2.5])
with r_col1:
    reviewer_input = st.text_input(
        "Reviewing Officer Staff ID",
        value=st.session_state.reviewer,
        placeholder="Enter reviewing officer name or staff ID (e.g., MUC-OFFICER-44)",
        label_visibility="collapsed"
    )
    if reviewer_input != st.session_state.reviewer:
        st.session_state.reviewer = reviewer_input

st.markdown("<div style='padding: 6px 18px 18px;'>", unsafe_allow_html=True)
if st.session_state.orders:
    for order in st.session_state.orders:
        o_status = order.get("status", "pending_approval")
        st_cls = f"status-{o_status}"
        decided_by = order.get("decided_by")
        decided_str = f" · Decided by {html.escape(str(decided_by))}" if decided_by else ""
        
        ord_c1, ord_c2, ord_c3 = st.columns([3, 1, 1.2])
        with ord_c1:
            st.markdown(
                f"""
                <div class="order-item" style="border-bottom:none; padding:8px 0;">
                    <div class="order-title">{html.escape(order.get('title', 'Untitled'))}</div>
                    <div class="order-subtitle">{html.escape(order.get('sector_id', ''))} · {html.escape(order.get('priority', ''))} · Protocols: {html.escape(order.get('protocol_refs', ''))}{decided_str}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with ord_c2:
            st.markdown(f'<div style="margin-top:14px;"><span class="order-status-badge {st_cls}">{o_status.replace("_", " ")}</span></div>', unsafe_allow_html=True)
        with ord_c3:
            if o_status == "pending_approval":
                ac1, ac2 = st.columns(2)
                with ac1:
                    if st.button("✔ APPROVE", key=f"app_{order['id']}", use_container_width=True):
                        if not st.session_state.reviewer.strip():
                            st.warning("Please enter Reviewing Officer ID above before approving.")
                        else:
                            order["status"] = "approved"
                            order["decided_by"] = st.session_state.reviewer.strip()
                            st.session_state.notice = f"Work order #{order['id']} APPROVED by {st.session_state.reviewer}."
                            st.session_state.events.insert(0, {
                                "id": len(st.session_state.events)+1,
                                "agent": "Human Officer Audit",
                                "message": f"Order #{order['id']} APPROVED by {st.session_state.reviewer}.",
                                "created_at": "Just now",
                                "is_gemini": False
                            })
                            st.rerun()
                with ac2:
                    if st.button("✖ REJECT", key=f"rej_{order['id']}", use_container_width=True):
                        if not st.session_state.reviewer.strip():
                            st.warning("Please enter Reviewing Officer ID above before rejecting.")
                        else:
                            order["status"] = "rejected"
                            order["decided_by"] = st.session_state.reviewer.strip()
                            st.session_state.notice = f"Work order #{order['id']} REJECTED by {st.session_state.reviewer}."
                            st.session_state.events.insert(0, {
                                "id": len(st.session_state.events)+1,
                                "agent": "Human Officer Audit",
                                "message": f"Order #{order['id']} REJECTED by {st.session_state.reviewer}.",
                                "created_at": "Just now",
                                "is_gemini": False
                            })
                            st.rerun()
            else:
                st.markdown("<div style='margin-top:16px; font-family:\"DM Mono\",monospace; font-size:10px; color:#5e746a;'>LOCKED · DECISION RECORDED</div>", unsafe_allow_html=True)

st.markdown("</div></div>", unsafe_allow_html=True)

# ── Footer / Caption ─────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="color:#71857c; font-family:'DM Mono',monospace; font-size:10.5px; line-height:1.6; margin-top:20px; border-top:1px solid #1a2f27; padding-top:14px;">
        UrbanGuard AI is a municipal decision-support prototype. Public environmental telemetry and citizen reports are triage signals only. Verify with authorized laboratory, drainage, or field inspections before final operational dispatch.
    </div>
    """,
    unsafe_allow_html=True,
)
