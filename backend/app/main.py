import csv
import io
import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from .models import TelemetryIn, HeatPoint, DispatchRequest, DataRefreshResult, OrderDecision, TextEvidenceIn, EvidenceResult, FusionResult
from .risk import calculate_pri, risk_components, severity
from . import store
from .simulation import readings
from .scenario_data import realistic_scenario
from .agents import run_dispatch
from .multimodal import analyse_image, analyse_text, fuse_modalities
from .real_data import weather_observations, munich_report_observations, retrieved_at

DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"

def cors_origins():
    configured = os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    return origins or ["*"]

@asynccontextmanager
async def lifespan(app):
    store.init_db()
    scenario = realistic_scenario()
    missing = [item for item in scenario if item.sector_id not in store.sector_ids()]
    if missing:
        for item in missing:
            store.add_telemetry(item, calculate_pri(item), synthetic=True)
        store.log("Scenario Data Layer", f"Added {len(missing)} missing Munich reference locations to the stakeholder snapshot; records are synthetic and require field verification.")
    yield
app=FastAPI(title="UrbanGuard AI", version="1.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=cors_origins(), allow_methods=["*"], allow_headers=["*"])
@app.get("/health")
def health():
    summary = store.summary()
    return {
        "status": "healthy",
        "mode": "local-first",
        "version": app.version,
        "data_mode": summary["data_mode"],
        "locations": summary["locations"],
        "pending_approval": summary["pending_approval"],
    }
def store_reading(t: TelemetryIn, synthetic: bool = False):
    pri=calculate_pri(t); store.add_telemetry(t,pri,synthetic=synthetic); store.log("Ingestion Engine",f"Received {t.source} telemetry for {t.sector_id}; calculated PRI {pri}."); return {"accepted":True,"pri":pri,"severity":severity(pri)}
@app.post("/api/v1/telemetry/ingest")
def ingest(t:TelemetryIn):
    return store_reading(t, synthetic=False)
@app.get("/api/v1/risks/heatmap",response_model=list[HeatPoint])
def heatmap():
    points = []
    for row in store.latest_points():
        telemetry = TelemetryIn.model_validate_json(row["payload"])
        points.append(HeatPoint(sector_id=row["sector_id"], district=row["district"], latitude=row["latitude"], longitude=row["longitude"], pri=row["pri"], severity=severity(row["pri"]), source=row["source"], observed_at=row["observed_at"], evidence=store.evidence_for(row), components=risk_components(telemetry)))
    return points
@app.get("/api/v1/risks/export.csv")
def export_heatmap_csv():
    """Download the current triage snapshot as CSV for offline review and FOI requests."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["sector_id", "district", "latitude", "longitude", "pri", "severity", "source", "observed_at", "evidence"])
    for point in heatmap():
        writer.writerow([point.sector_id, point.district, point.latitude, point.longitude, point.pri, point.severity, point.source, point.observed_at.isoformat(), point.evidence or ""])
    filename = f"urbanguard-risk-snapshot-{retrieved_at().date().isoformat()}.csv"
    return Response(content=buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
@app.get("/api/v1/dashboard/summary")
def dashboard_summary():
    return store.summary()
@app.post("/api/v1/data/refresh-weather", response_model=DataRefreshResult)
def refresh_weather():
    """Fetch real public weather data; never manufacture municipal measurements."""
    try: observations, source_urls = weather_observations()
    except RuntimeError as error: raise HTTPException(502, str(error))
    for item in observations: store.add_telemetry(item, calculate_pri(item))
    store.log("Public Data Connector", f"Ingested {len(observations)} Open-Meteo observations; source URLs: {' | '.join(source_urls)}")
    return DataRefreshResult(ingested=len(observations), provider="Open-Meteo Forecast API", retrieved_at=retrieved_at(), limitation="Weather is an environmental exposure proxy only; confirm with authorised municipal drainage, waste, or laboratory data before action.")
@app.post("/api/v1/data/refresh-munich-reports", response_model=DataRefreshResult)
def refresh_munich_reports():
    try: observations, source_url = munich_report_observations()
    except RuntimeError as error: raise HTTPException(502, str(error))
    for item in observations: store.add_telemetry(item, calculate_pri(item))
    store.log("Munich Open Data Connector", f"Ingested {len(observations)} sanitation-relevant anonymised Open311 reports from {source_url}")
    return DataRefreshResult(ingested=len(observations), provider="Munich Open Data / Open311", retrieved_at=retrieved_at(), limitation="Report-derived signals are triage evidence only, not verified inspections or measurements. Confirm location, recency, and severity before action.")
@app.post("/api/v1/simulation/tick")
def tick():
    output=[]
    for item in readings(): output.append(store_reading(item, synthetic=True))
    return {"simulated":len(output),"results":output}
@app.post("/api/v1/data/load-realistic-scenario", response_model=DataRefreshResult)
def load_realistic_scenario():
    observations = realistic_scenario()
    for item in observations: store.add_telemetry(item, calculate_pri(item), synthetic=True)
    store.log("Scenario Data Loader", f"Loaded {len(observations)} deterministic Munich sanitation training records; all are synthetic and require field verification.")
    return DataRefreshResult(ingested=len(observations), provider="UrbanGuard realistic training scenario", retrieved_at=retrieved_at(), limitation="This scenario is synthetic, based on plausible municipal conditions, and must never be treated as a live municipal record or used for operational action without verification.")
@app.post("/api/v1/agents/trigger-dispatch")
async def dispatch(request:DispatchRequest):
    try: return await run_dispatch(request.sector_id)
    except ValueError as e: raise HTTPException(404,str(e))
@app.get("/api/v1/work-orders/{order_id}")
def work_order(order_id: int):
    row = store.order_by_id(order_id)
    if row is None: raise HTTPException(404, "Work order not found")
    return dict(row)
@app.post("/api/v1/work-orders/{order_id}/decision")
def decide_work_order(order_id: int, decision: OrderDecision):
    row = store.order_by_id(order_id)
    if row is None: raise HTTPException(404, "Work order not found")
    if row["status"] != "pending_approval": raise HTTPException(409, f"Work order is already {row['status']}")
    store.decide_order(order_id, decision.decision, decision.actor)
    verb = "approved" if decision.decision == "approve" else "rejected"
    note = f" Note: {decision.note}" if decision.note else ""
    store.log("Human Review", f"Work order #{order_id} for {row['sector_id']} {verb} by {decision.actor}.{note}")
    return dict(store.order_by_id(order_id))
@app.get("/api/v1/activity")
def activity(): return [dict(x) for x in store.activities()]

def evidence_response(row):
    return EvidenceResult(id=row["id"], sector_id=row["sector_id"], modality=row["modality"], score=row["score"], summary=row["caption"] or "", features=json.loads(row["features"]), observed_at=row["observed_at"])

@app.post("/api/v1/evidence/image", response_model=EvidenceResult)
async def evidence_image(file: UploadFile = File(...), sector_id: str = Form(...), caption: str = Form(""), latitude: float | None = Form(None), longitude: float | None = Form(None)):
    """Ingest a photo as visual triage evidence. Inference stays inside the deployment boundary."""
    data = await file.read()
    if not data: raise HTTPException(400, "Empty image upload")
    if len(data) > 8_000_000: raise HTTPException(413, "Image exceeds the 8 MB evidence limit")
    try: features = analyse_image(data)
    except ValueError as error: raise HTTPException(415, str(error))
    score = max(features["visual_water_score"], features["visual_waste_score"])
    evidence_id = store.add_evidence(sector_id, "image", latitude, longitude, caption or (file.filename or "image evidence"), features, score)
    store.log("Multimodal Evidence Agent", f"Analysed image evidence for {sector_id}: visual water {features['visual_water_score']}, waste {features['visual_waste_score']}, quality {features['quality']}.")
    return evidence_response(store.evidence_by_id(evidence_id))
@app.post("/api/v1/evidence/text", response_model=EvidenceResult)
def evidence_text(payload: TextEvidenceIn):
    features = analyse_text(payload.text)
    score = features["text_signal_score"]
    evidence_id = store.add_evidence(payload.sector_id, "text", payload.latitude, payload.longitude, payload.text[:280], features, score)
    categories = ", ".join(features["categories"]) or "none"
    store.log("Multimodal Evidence Agent", f"Analysed text evidence for {payload.sector_id}: signal {score}, categories {categories}.")
    return evidence_response(store.evidence_by_id(evidence_id))
@app.get("/api/v1/evidence/{sector_id}", response_model=list[EvidenceResult])
def evidence_list(sector_id: str):
    return [evidence_response(row) for row in store.evidence_by_sector(sector_id)]
@app.post("/api/v1/evidence/fuse/{sector_id}", response_model=FusionResult)
def evidence_fuse(sector_id: str):
    """Fuse telemetry PRI with the latest image and text evidence into one explainable score."""
    telemetry_pri = next((row["pri"] for row in store.latest_points() if row["sector_id"] == sector_id), None)
    image_row = next((row for row in store.evidence_by_sector(sector_id) if row["modality"] == "image"), None)
    text_row = next((row for row in store.evidence_by_sector(sector_id) if row["modality"] == "text"), None)
    if telemetry_pri is None and image_row is None and text_row is None: raise HTTPException(404, "No telemetry or evidence exists for this sector")
    fusion = fuse_modalities(telemetry_pri, image_row["score"] if image_row else None, text_row["score"] if text_row else None)
    store.log("Evidence Fusion Agent", f"Fused modalities for {sector_id}: score {fusion['score']}. {fusion['explanation']}")
    return FusionResult(sector_id=sector_id, **fusion)
@app.get("/api/v1/work-orders")
def work_orders(): return [dict(x) for x in store.orders()]
