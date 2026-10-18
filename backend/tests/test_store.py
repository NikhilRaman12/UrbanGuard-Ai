from app.models import TelemetryIn


def sample(sector_id="MUC-T-01", source="drainage", **overrides):
    data = dict(sector_id=sector_id, district="Test", latitude=48.1, longitude=11.5, source=source)
    data.update(overrides)
    return TelemetryIn(**data)


def test_latest_points_keeps_most_recent_per_sector(store_db):
    store_db.add_telemetry(sample(), 10)
    store_db.add_telemetry(sample(), 80)
    rows = store_db.latest_points()
    assert len(rows) == 1
    assert rows[0]["pri"] == 80


def test_summary_data_mode_tracks_synthetic_sources(store_db):
    store_db.add_telemetry(sample(sector_id="MUC-T-A"), 10, synthetic=True)
    assert store_db.summary()["data_mode"] == "synthetic_training_snapshot"

    store_db.add_telemetry(sample(sector_id="MUC-T-B", source="open_meteo"), 10, synthetic=False)
    summary = store_db.summary()
    assert summary["data_mode"] == "mixed_sources"
    assert summary["synthetic_locations"] == 1


def test_work_order_decision_workflow(store_db):
    order_id = store_db.create_order("MUC-T-01", "Draft intervention", "P1 — same day", ["BAV-WS-01"])
    assert order_id
    assert store_db.order_by_id(order_id)["status"] == "pending_approval"
    assert store_db.summary()["pending_approval"] == 1

    assert store_db.decide_order(order_id, "approve", "officer.a") is True
    row = store_db.order_by_id(order_id)
    assert row["status"] == "approved"
    assert row["decided_by"] == "officer.a"
    assert row["decided_at"]

    # A decided order cannot be decided a second time.
    assert store_db.decide_order(order_id, "reject", "officer.b") is False
    assert store_db.order_by_id(order_id)["status"] == "approved"


def test_evidence_for_returns_report_summary(store_db):
    store_db.add_telemetry(sample(report_summary="pooled water near school"), 42)
    row = store_db.latest_points()[0]
    assert store_db.evidence_for(row) == "pooled water near school"
