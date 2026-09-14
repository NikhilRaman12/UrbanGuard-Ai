from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import TelemetryIn, HeatPoint, DispatchRequest, DataRefreshResult
from .risk import calculate_pri, risk_components, severity
from . import store
from .simulation import readings
from .scenario_data import realistic_scenario
from .agents import run_dispatch
from .real_data import weather_observations, munich_report_observations, retrieved_at

@asynccontextmanager
async def lifespan(app):
    store.init_db(); yield
app=FastAPI(title="UrbanGuard AI", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:3000"],allow_methods=["*"],allow_headers=["*"])
@app.get("/health")
def health(): return {"status":"healthy","mode":"local-first"}
@app.post("/api/v1/telemetry/ingest")
def ingest(t:TelemetryIn):
    pri=calculate_pri(t); store.add_telemetry(t,pri); store.log("Ingestion Engine",f"Received {t.source} telemetry for {t.sector_id}; calculated PRI {pri}."); return {"accepted":True,"pri":pri,"severity":severity(pri)}
@app.get("/api/v1/risks/heatmap",response_model=list[HeatPoint])
def heatmap():
    points = []
    for row in store.latest_points():
        telemetry = TelemetryIn.model_validate_json(row["payload"])
        points.append(HeatPoint(sector_id=row["sector_id"], district=row["district"], latitude=row["latitude"], longitude=row["longitude"], pri=row["pri"], severity=severity(row["pri"]), source=row["source"], observed_at=row["observed_at"], evidence=store.evidence_for(row), components=risk_components(telemetry)))
    return points
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
    for item in readings(): output.append(ingest(item))
    return {"simulated":len(output),"results":output}
@app.post("/api/v1/data/load-realistic-scenario", response_model=DataRefreshResult)
def load_realistic_scenario():
    observations = realistic_scenario()
    for item in observations: store.add_telemetry(item, calculate_pri(item))
    store.log("Scenario Data Loader", f"Loaded {len(observations)} deterministic Munich sanitation training records; all are synthetic and require field verification.")
    return DataRefreshResult(ingested=len(observations), provider="UrbanGuard realistic training scenario", retrieved_at=retrieved_at(), limitation="This scenario is synthetic, based on plausible municipal conditions, and must never be treated as a live municipal record or used for operational action without verification.")
@app.post("/api/v1/agents/trigger-dispatch")
async def dispatch(request:DispatchRequest):
    try: return await run_dispatch(request.sector_id)
    except ValueError as e: raise HTTPException(404,str(e))
@app.get("/api/v1/activity")
def activity(): return [dict(x) for x in store.activities()]
@app.get("/api/v1/work-orders")
def work_orders(): return [dict(x) for x in store.orders()]
