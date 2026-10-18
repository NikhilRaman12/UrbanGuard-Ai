from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class TelemetryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sector_id: str = Field(examples=["MUC-ALT-01"])
    district: str
    latitude: float = Field(ge=47.5, le=49.0)
    longitude: float = Field(ge=10.5, le=12.5)
    source: Literal["drainage", "waste", "water_body", "weather", "open_meteo", "citizen_report", "munich_open311"]
    temperature_c: float = Field(18, ge=-40, le=60)
    standing_water_hours: float = Field(0, ge=0, le=720)
    organic_waste_pct: float = Field(0, ge=0, le=100)
    sewer_level_pct: float = Field(0, ge=0, le=100)
    ph: float = Field(7, ge=0, le=14)
    clog_probability: float = Field(0, ge=0, le=100)
    report_summary: str | None = Field(default=None, max_length=280)

class HeatPoint(BaseModel):
    sector_id: str
    district: str
    latitude: float
    longitude: float
    pri: float
    severity: str
    source: str
    observed_at: datetime
    evidence: str | None = None
    components: dict[str, float]

class DataRefreshResult(BaseModel):
    ingested: int
    provider: str
    retrieved_at: datetime
    limitation: str

class DispatchRequest(BaseModel):
    sector_id: str

class OrderDecision(BaseModel):
    decision: Literal["approve", "reject"]
    actor: str = Field(min_length=1, max_length=120, examples=["ops.lead@muenchen.de"])
    note: str | None = Field(default=None, max_length=280)

class TextEvidenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sector_id: str
    district: str | None = None
    latitude: float | None = Field(default=None, ge=47.5, le=49.0)
    longitude: float | None = Field(default=None, ge=10.5, le=12.5)
    text: str = Field(min_length=3, max_length=2000)

class EvidenceResult(BaseModel):
    id: int
    sector_id: str
    modality: str
    score: float
    summary: str
    features: dict
    observed_at: datetime

class FusionResult(BaseModel):
    sector_id: str
    score: float
    contributions: dict[str, float]
    modalities: list[str]
    explanation: str
