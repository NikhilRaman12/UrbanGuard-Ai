from io import BytesIO

import pytest
from PIL import Image

from app.multimodal import analyse_image, analyse_text, fuse_modalities


def png_bytes(color, size=(80, 80)):
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_water_like_image_scores_high_on_water():
    features = analyse_image(png_bytes((100, 110, 150)))
    assert features["visual_water_score"] == 100
    assert features["quality"] == "ok"
    assert features["modality"] == "image"


def test_dark_clutter_image_scores_high_on_waste():
    features = analyse_image(png_bytes((30, 30, 30)))
    assert features["visual_waste_score"] == 100
    assert features["visual_water_score"] == 0


def test_corrupt_image_is_rejected():
    with pytest.raises(ValueError):
        analyse_image(b"not an image")


def test_text_taxonomy_extracts_categories():
    features = analyse_text("Blocked drain with standing water and a bad smell and rats near the school")
    assert features["text_signal_score"] == 70
    assert set(features["categories"]) == {"standing_water", "drainage_blockage", "odor", "rodent"}


def test_fusion_weights_favour_telemetry():
    strong = fuse_modalities(100, 0, 0)
    assert strong["score"] == 60.0
    assert strong["contributions"]["telemetry"] == 60.0

    telemetry_only = fuse_modalities(telemetry_pri=50)
    assert telemetry_only["score"] == 50.0
    assert telemetry_only["modalities"] == ["telemetry"]


def test_fusion_without_evidence_is_zero():
    empty = fuse_modalities()
    assert empty["score"] == 0.0
    assert empty["modalities"] == []
