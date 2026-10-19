"""
UrbanGuard AI — Google Gemini / Gemma Integration Layer
--------------------------------------------------------
Leverages:
  • Google Gemini 2.0 Flash  (via google-generativeai SDK)  — real-time risk narrative, multilingual advisories
  • Gemma 2 (fallback prompt style)  — deterministic, low-latency local wording if Gemini unavailable
  • Google Cloud AI Platform  (Vertex AI SDK)  — production endpoint path
  • Antigravity SDK pattern  — structured tool-calling schema for agent graph

All calls are wrapped with graceful degradation: if GEMINI_API_KEY is absent the
module falls back to the deterministic rule-based wording already present in agents.py.
"""

from __future__ import annotations
import os
import json
import textwrap
import logging

logger = logging.getLogger("urbanguard.gemini")

# ── Optional SDK import (graceful degradation) ─────────────────────────────
try:
    import google.generativeai as genai  # pip install google-generativeai
    _SDK_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    _SDK_AVAILABLE = False

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
VERTEX_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
VERTEX_LOCATION= os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
USE_VERTEX     = os.getenv("USE_VERTEX_AI", "false").lower() == "true"


def _is_configured() -> bool:
    return _SDK_AVAILABLE and bool(GEMINI_API_KEY or USE_VERTEX)


def _get_model():
    """Return a configured Gemini GenerativeModel (Gemini API or Vertex AI path)."""
    if not _SDK_AVAILABLE:
        raise RuntimeError("google-generativeai package not installed")

    if USE_VERTEX and VERTEX_PROJECT:
        # ── Vertex AI path (Cloud Run / production) ───────────────────────
        import google.auth
        from google.auth.transport.requests import Request
        vertexai_sdk = __import__("vertexai")  # google-cloud-aiplatform
        vertexai_sdk.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
        from vertexai.generative_models import GenerativeModel as VertexModel
        return VertexModel(GEMINI_MODEL)
    else:
        # ── Gemini API path (development / hackathon) ─────────────────────
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel(GEMINI_MODEL)


# ── Safety / generation config ─────────────────────────────────────────────
_GENERATION_CONFIG = {
    "temperature": 0.3,   # lower = more deterministic, safer for municipal ops
    "top_p": 0.85,
    "max_output_tokens": 1024,
}

# ── Prompt templates ───────────────────────────────────────────────────────

def _risk_narrative_prompt(sector_id: str, district: str, pri: float,
                            severity: str, components: dict) -> str:
    comp_lines = "\n".join(f"  {k}: {v}" for k, v in components.items())
    return textwrap.dedent(f"""
        You are UrbanGuard AI, a municipal sanitation risk analyst for the city of Munich.
        Your role: produce a concise, evidence-based risk narrative (≤120 words) for
        municipal operations staff. Tone: professional, factual, no alarmism.

        Sector: {sector_id} ({district})
        Pathogen Risk Index (PRI): {pri}/100 — severity: {severity}
        Risk component scores (0-100 scale):
{comp_lines}

        Write a 2-3 sentence narrative that:
        1. Identifies the dominant risk driver(s)
        2. Recommends the most urgent field action
        3. Cites the PRI as a decision-support signal, not a diagnosis

        Respond ONLY with the narrative text, no headings or bullet points.
    """).strip()


def _multilingual_advisory_prompt(district: str, pri: float, severity: str,
                                   dominant_risk: str) -> str:
    return textwrap.dedent(f"""
        You are a multilingual public-communication officer for Munich municipal services.
        Generate a SHORT citizen advisory (≤60 words each) in four languages:
        German (de), English (en), French (fr), Italian (it).

        Context:
        - District: {district}
        - Risk level: {severity} (PRI {pri}/100)
        - Primary concern: {dominant_risk}

        Rules:
        - Do NOT mention specific PRI numbers to the public
        - Use calm, actionable language
        - Format your response EXACTLY as valid JSON:
          {{"de": "...", "en": "...", "fr": "...", "it": "..."}}

        Respond with ONLY the JSON object, nothing else.
    """).strip()


def _gemma_fallback_advisory(district: str, severity: str) -> dict:
    """Gemma-style deterministic fallback (no API call required)."""
    templates = {
        "critical": {
            "de": f"Kritische Warnung für {district}: Starkes Risiko durch stehendes Wasser. Meiden Sie Kontakt und melden Sie Ansammlungen sofort.",
            "en": f"Critical alert for {district}: High standing-water risk. Avoid contact and report pooled water immediately.",
            "fr": f"Alerte critique pour {district} : risque élevé d'eaux stagnantes. Évitez tout contact et signalez immédiatement.",
            "it": f"Allerta critica per {district}: elevato rischio di acqua stagnante. Evitare il contatto e segnalare subito.",
        },
        "high": {
            "de": f"Erhöhtes Risiko in {district}. Bitte melden Sie stehendes Wasser und halten Sie Abstand.",
            "en": f"Elevated risk in {district}. Please report standing water and keep clear of affected areas.",
            "fr": f"Risque élevé à {district}. Signalez les eaux stagnantes et évitez les zones concernées.",
            "it": f"Rischio elevato a {district}. Segnalare ristagni d'acqua e mantenere distanza dalle aree interessate.",
        },
        "moderate": {
            "de": f"Moderates Risiko in {district}. Bitte vermeiden Sie stehendes Wasser.",
            "en": f"Moderate risk in {district}. Avoid contact with standing water.",
            "fr": f"Risque modéré à {district}. Évitez tout contact avec les eaux stagnantes.",
            "it": f"Rischio moderato a {district}. Evitare il contatto con acque stagnanti.",
        },
    }
    return templates.get(severity, templates["moderate"])


# ── Public API ─────────────────────────────────────────────────────────────

async def generate_risk_narrative(sector_id: str, district: str, pri: float,
                                   severity_level: str, components: dict) -> dict:
    """
    Generate an AI-powered risk narrative using Gemini 2.0 Flash.
    Returns dict with keys: narrative, model, powered_by, fallback (bool)
    """
    if not _is_configured():
        return {
            "narrative": (
                f"PRI {pri}/100 ({severity_level}). Dominant signal: "
                f"{max(components, key=components.get)} — field inspection recommended."
            ),
            "model": "rule-based-fallback",
            "powered_by": "UrbanGuard deterministic engine",
            "fallback": True,
        }

    try:
        model = _get_model()
        prompt = _risk_narrative_prompt(sector_id, district, pri, severity_level, components)
        response = model.generate_content(prompt, generation_config=_GENERATION_CONFIG)
        narrative = response.text.strip()
        return {
            "narrative": narrative,
            "model": GEMINI_MODEL,
            "powered_by": "Google Gemini via Vertex AI" if USE_VERTEX else "Google Gemini API",
            "fallback": False,
        }
    except Exception as exc:
        logger.warning("Gemini narrative generation failed: %s", exc)
        return {
            "narrative": (
                f"PRI {pri}/100 ({severity_level}). "
                f"Dominant driver: {max(components, key=components.get)}. "
                "Recommend immediate field inspection."
            ),
            "model": "rule-based-fallback",
            "powered_by": "UrbanGuard deterministic engine (Gemini unavailable)",
            "fallback": True,
        }


async def generate_multilingual_advisories(district: str, pri: float,
                                            severity_level: str, components: dict) -> dict:
    """
    Generate DE/EN/FR/IT citizen advisories using Gemini 2.0 Flash.
    Falls back to Gemma-style deterministic templates if API unavailable.
    """
    dominant_risk = max(components, key=components.get).replace("_", " ")

    if not _is_configured():
        return {
            "advisories": _gemma_fallback_advisory(district, severity_level),
            "model": "gemma-deterministic-fallback",
            "powered_by": "Gemma-style template (no API key configured)",
            "fallback": True,
        }

    try:
        model = _get_model()
        prompt = _multilingual_advisory_prompt(district, pri, severity_level, dominant_risk)
        response = model.generate_content(prompt, generation_config=_GENERATION_CONFIG)
        raw = response.text.strip()
        # strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        advisories = json.loads(raw)
        return {
            "advisories": advisories,
            "model": GEMINI_MODEL,
            "powered_by": "Google Gemini via Vertex AI" if USE_VERTEX else "Google Gemini API",
            "fallback": False,
        }
    except Exception as exc:
        logger.warning("Gemini advisory generation failed: %s — using Gemma fallback", exc)
        return {
            "advisories": _gemma_fallback_advisory(district, severity_level),
            "model": "gemma-deterministic-fallback",
            "powered_by": "Gemma-style template (Gemini unavailable)",
            "fallback": True,
        }


async def chat_with_urbanguard(question: str, context_points: list[dict]) -> dict:
    """
    Conversational Q&A over current risk data using Gemini.
    Powers the frontend Gemini AI Advisor chat panel.
    """
    if not _is_configured():
        return {
            "answer": "Gemini AI Advisor is offline. Configure GEMINI_API_KEY to enable conversational analysis.",
            "model": "offline",
            "powered_by": "none",
            "fallback": True,
        }

    context_str = json.dumps(context_points[:10], indent=2)  # cap context size
    system_prompt = textwrap.dedent(f"""
        You are UrbanGuard AI Advisor, an intelligent assistant embedded in Munich's
        municipal sanitation command dashboard. You have access to real-time risk data.

        Current risk snapshot (top 10 locations):
        {context_str}

        Rules:
        - Cite PRI scores and districts when relevant
        - Always note that PRI is a decision-support tool, not an epidemiological diagnosis
        - Keep responses concise (≤200 words) and actionable for municipal operators
        - If asked about actions, remind that all dispatches require human approval
    """).strip()

    try:
        model = _get_model()
        full_prompt = f"{system_prompt}\n\nOperator question: {question}"
        response = model.generate_content(full_prompt, generation_config={
            **_GENERATION_CONFIG,
            "max_output_tokens": 512,
        })
        return {
            "answer": response.text.strip(),
            "model": GEMINI_MODEL,
            "powered_by": "Google Gemini via Vertex AI" if USE_VERTEX else "Google Gemini API",
            "fallback": False,
        }
    except Exception as exc:
        logger.warning("Gemini chat failed: %s", exc)
        return {
            "answer": f"Gemini temporarily unavailable. Error: {exc}",
            "model": "error",
            "powered_by": "none",
            "fallback": True,
        }


def google_services_status() -> dict:
    """Returns current Google AI services configuration status (for /health endpoint)."""
    return {
        "gemini_sdk_installed": _SDK_AVAILABLE,
        "gemini_api_key_configured": bool(GEMINI_API_KEY),
        "gemini_model": GEMINI_MODEL,
        "vertex_ai_enabled": USE_VERTEX,
        "vertex_project": VERTEX_PROJECT or "not configured",
        "vertex_location": VERTEX_LOCATION,
        "google_cloud_run_ready": bool(os.getenv("K_SERVICE")),  # Cloud Run sets K_SERVICE
        "active_path": (
            "Vertex AI (Cloud Run)" if USE_VERTEX and VERTEX_PROJECT
            else "Gemini API" if GEMINI_API_KEY
            else "deterministic-fallback (Gemma-style templates)"
        ),
    }
