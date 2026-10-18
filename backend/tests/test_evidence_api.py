from io import BytesIO

from PIL import Image

HIGH = dict(
    sector_id="MUC-MM-01", district="Test", latitude=48.1, longitude=11.5, source="drainage",
    temperature_c=30, standing_water_hours=72, organic_waste_pct=100,
    sewer_level_pct=100, ph=5, clog_probability=100,
)


def water_png():
    buffer = BytesIO()
    Image.new("RGB", (80, 80), (100, 110, 150)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_text_evidence_endpoint(client):
    response = client.post("/api/v1/evidence/text", json={
        "sector_id": "MUC-MM-01",
        "text": "Blocked drain with standing water and a bad smell and rats",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["modality"] == "text"
    assert body["score"] == 70
    assert "standing_water" in body["features"]["categories"]


def test_image_evidence_endpoint(client):
    response = client.post(
        "/api/v1/evidence/image",
        data={"sector_id": "MUC-MM-01", "caption": "crew photo"},
        files={"file": ("evidence.png", water_png(), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["modality"] == "image"
    assert body["score"] == 100

    listed = client.get("/api/v1/evidence/MUC-MM-01").json()
    assert len(listed) == 1


def test_image_endpoint_rejects_non_image(client):
    response = client.post(
        "/api/v1/evidence/image",
        data={"sector_id": "MUC-MM-01"},
        files={"file": ("notes.txt", b"just text", "text/plain")},
    )
    assert response.status_code == 415


def test_fusion_combines_telemetry_and_evidence(client):
    client.post("/api/v1/telemetry/ingest", json=HIGH)
    client.post("/api/v1/evidence/text", json={"sector_id": "MUC-MM-01", "text": "sewage overflow and rats"})
    fused = client.post("/api/v1/evidence/fuse/MUC-MM-01").json()
    assert fused["sector_id"] == "MUC-MM-01"
    assert set(fused["modalities"]) == {"telemetry", "text"}
    assert 0 <= fused["score"] <= 100


def test_fusion_unknown_sector_is_404(client):
    assert client.post("/api/v1/evidence/fuse/MUC-NOPE").status_code == 404
