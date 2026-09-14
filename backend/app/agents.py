import json
from pathlib import Path
from .risk import severity
from . import store

REGULATIONS = json.loads((Path(__file__).parent.parent / "data" / "regulations.json").read_text())
async def run_dispatch(sector_id: str):
    rows = [r for r in store.latest_points() if r["sector_id"] == sector_id]
    if not rows: raise ValueError("No telemetry exists for this sector")
    point=rows[0]; pri=point["pri"]; level=severity(pri)
    store.log("Sanitation Monitor", f"Analysed {sector_id}: PRI {pri}/100 ({level}).")
    if pri < 30:
        store.log("Sanitation Monitor", "No dispatch created: risk remains below operational threshold.")
        return {"sector_id":sector_id,"pri":pri,"action":"monitor","work_order":None,"advisories":{}}
    refs = [r["id"] for r in REGULATIONS if ("Standing" in r["title"] or "Sewer" in r["title"])]
    priority="P1 — same day" if pri >= 75 else "P2 — within 24 hours"
    title=f"Inspect and mitigate vector breeding risk — {point['district']}"
    store.log("Dispatcher & Compliance Copilot", f"Drafted {priority} work order; applied {', '.join(refs)}. Awaiting human approval.")
    store.create_order(sector_id,title,priority,refs)
    advisories={
      "de":"Hinweis: Erhöhtes Risiko durch stehendes Wasser in Ihrem Bezirk. Bitte melden Sie Ansammlungen und vermeiden Sie Kontakt mit belastetem Wasser.",
      "en":"Advisory: Elevated standing-water risk in your district. Report pooled water and avoid contact with contaminated water.",
      "fr":"Alerte : risque accru lié aux eaux stagnantes dans votre quartier. Signalez les accumulations d'eau.",
      "it":"Avviso: rischio elevato di acqua stagnante nel quartiere. Segnalate i ristagni d'acqua."
    }
    store.log("Public Communication Agent", "Prepared DE/EN/FR/IT citizen advisories for human review; nothing published automatically.")
    return {"sector_id":sector_id,"pri":pri,"action":"dispatch_drafted","work_order":{"title":title,"priority":priority,"status":"pending_approval","protocol_refs":refs},"advisories":advisories}
