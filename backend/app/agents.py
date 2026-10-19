import json
from pathlib import Path
from .risk import severity
from . import store
from .gemini_agent import generate_risk_narrative, generate_multilingual_advisories

REGULATIONS = json.loads((Path(__file__).parent.parent / "data" / "regulations.json").read_text())

async def run_dispatch(sector_id: str):
    rows = [r for r in store.latest_points() if r["sector_id"] == sector_id]
    if not rows:
        raise ValueError("No telemetry exists for this sector")

    point = rows[0]
    pri   = point["pri"]
    level = severity(pri)

    store.log("Sanitation Monitor", f"Analysed {sector_id}: PRI {pri}/100 ({level}).")

    if pri < 30:
        store.log("Sanitation Monitor", "No dispatch created: risk remains below operational threshold.")
        return {"sector_id": sector_id, "pri": pri, "action": "monitor", "work_order": None, "advisories": {}}

    # ── Google Gemini: AI-powered risk narrative ──────────────────────────
    from .gemini_agent import generate_risk_narrative
    from json import loads as _jloads
    try:
        payload   = _jloads(point["payload"])
        components = {k: payload.get(k, 0) for k in
                      ["temperature", "standing_water_hours", "organic_waste_kg",
                       "sewer_level_pct", "ph_deviation", "clog_probability"]}
    except Exception:
        components = {}

    narrative_result = await generate_risk_narrative(
        sector_id, point["district"], pri, level, components
    )
    ai_narrative = narrative_result["narrative"]
    ai_model     = narrative_result["powered_by"]
    store.log("Gemini AI Monitor",
              f"[{ai_model}] Risk narrative generated for {sector_id}: {ai_narrative[:120]}…")

    # ── Work order + compliance refs ──────────────────────────────────────
    refs     = [r["id"] for r in REGULATIONS if ("Standing" in r["title"] or "Sewer" in r["title"])]
    priority = "P1 — same day" if pri >= 75 else "P2 — within 24 hours"
    title    = f"Inspect and mitigate vector breeding risk — {point['district']}"

    store.log("Dispatcher & Compliance Copilot",
              f"Drafted {priority} work order; applied {', '.join(refs)}. Awaiting human approval.")
    order_id = store.create_order(sector_id, title, priority, refs)

    # ── Google Gemini: multilingual citizen advisories ────────────────────
    advisory_result = await generate_multilingual_advisories(
        point["district"], pri, level, components or {"standing_water": 50}
    )
    advisories = advisory_result["advisories"]
    adv_model  = advisory_result["powered_by"]

    store.log("Public Communication Agent",
              f"[{adv_model}] Prepared DE/EN/FR/IT citizen advisories for human review; nothing published automatically.")

    return {
        "sector_id":   sector_id,
        "pri":         pri,
        "action":      "dispatch_drafted",
        "ai_narrative": ai_narrative,
        "ai_model":    ai_model,
        "work_order": {
            "id":           order_id,
            "title":        title,
            "priority":     priority,
            "status":       "pending_approval",
            "protocol_refs": refs,
        },
        "advisories": advisories,
    }
