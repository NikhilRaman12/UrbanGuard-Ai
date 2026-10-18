import asyncio

import pytest

from app.agents import run_dispatch
from app.models import TelemetryIn
from app.risk import calculate_pri

CRITICAL = dict(
    temperature_c=30, standing_water_hours=72, organic_waste_pct=100,
    sewer_level_pct=100, ph=5, clog_probability=100,
)


def ingest(store_db, sector_id, **overrides):
    data = dict(sector_id=sector_id, district="Test", latitude=48.1, longitude=11.5, source="drainage")
    data.update(overrides)
    telemetry = TelemetryIn(**data)
    store_db.add_telemetry(telemetry, calculate_pri(telemetry), synthetic=True)
    return telemetry


def test_low_risk_stays_in_monitoring(store_db):
    ingest(store_db, "MUC-T-01")
    result = asyncio.run(run_dispatch("MUC-T-01"))
    assert result["action"] == "monitor"
    assert result["work_order"] is None


def test_high_risk_drafts_order_with_id(store_db):
    ingest(store_db, "MUC-T-02", **CRITICAL)
    result = asyncio.run(run_dispatch("MUC-T-02"))
    assert result["action"] == "dispatch_drafted"
    assert result["work_order"]["id"]
    assert result["work_order"]["status"] == "pending_approval"
    assert result["work_order"]["priority"].startswith("P1")
    assert set(result["advisories"]) == {"de", "en", "fr", "it"}


def test_unknown_sector_raises(store_db):
    with pytest.raises(ValueError):
        asyncio.run(run_dispatch("MUC-DOES-NOT-EXIST"))
