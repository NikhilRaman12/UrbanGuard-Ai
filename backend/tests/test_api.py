HIGH = dict(
    sector_id="MUC-API-01", district="Test", latitude=48.1, longitude=11.5, source="drainage",
    temperature_c=30, standing_water_hours=72, organic_waste_pct=100,
    sewer_level_pct=100, ph=5, clog_probability=100,
)
LOW = dict(sector_id="MUC-API-02", district="Calm", latitude=48.2, longitude=11.6, source="drainage")


def test_health_reports_mode_and_version(client):
    body = client.get("/health").json()
    assert body["status"] == "healthy"
    assert body["mode"] == "local-first"
    assert "data_mode" in body


def test_ingest_scores_and_appears_in_heatmap(client):
    accepted = client.post("/api/v1/telemetry/ingest", json=HIGH).json()
    assert accepted["pri"] == 100
    assert accepted["severity"] == "critical"
    points = client.get("/api/v1/risks/heatmap").json()
    assert any(point["sector_id"] == "MUC-API-01" for point in points)


def test_heatmap_csv_export(client):
    client.post("/api/v1/telemetry/ingest", json=HIGH)
    response = client.get("/api/v1/risks/export.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert "sector_id" in response.text
    assert "MUC-API-01" in response.text


def test_dispatch_then_human_decision_flow(client):
    client.post("/api/v1/telemetry/ingest", json=HIGH)
    drafted = client.post("/api/v1/agents/trigger-dispatch", json={"sector_id": "MUC-API-01"}).json()
    order_id = drafted["work_order"]["id"]

    approved = client.post(
        f"/api/v1/work-orders/{order_id}/decision",
        json={"decision": "approve", "actor": "officer.a", "note": "crew scheduled"},
    ).json()
    assert approved["status"] == "approved"
    assert approved["decided_by"] == "officer.a"

    conflict = client.post(
        f"/api/v1/work-orders/{order_id}/decision",
        json={"decision": "reject", "actor": "officer.b"},
    )
    assert conflict.status_code == 409


def test_decision_for_unknown_order_is_404(client):
    response = client.post(
        "/api/v1/work-orders/999999/decision",
        json={"decision": "approve", "actor": "officer.a"},
    )
    assert response.status_code == 404


def test_low_risk_dispatch_monitors(client):
    client.post("/api/v1/telemetry/ingest", json=LOW)
    result = client.post("/api/v1/agents/trigger-dispatch", json={"sector_id": "MUC-API-02"}).json()
    assert result["action"] == "monitor"


def test_realistic_scenario_is_labelled_synthetic(client):
    loaded = client.post("/api/v1/data/load-realistic-scenario").json()
    assert loaded["ingested"] > 0
    summary = client.get("/api/v1/dashboard/summary").json()
    assert summary["synthetic_locations"] > 0
    assert summary["data_mode"] in {"synthetic_training_snapshot", "mixed_sources"}
