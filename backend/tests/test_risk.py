from app.models import TelemetryIn
from app.risk import calculate_pri, risk_components, severity


def reading(**overrides):
    data = dict(sector_id="MUC-T-01", district="Test", latitude=48.1, longitude=11.5, source="drainage")
    data.update(overrides)
    return TelemetryIn(**data)


def test_pri_is_bounded_and_transparent():
    assert 0 <= calculate_pri(reading()) <= 100
    worst_case = reading(
        temperature_c=30, standing_water_hours=72, organic_waste_pct=100,
        sewer_level_pct=100, ph=5, clog_probability=100,
    )
    assert calculate_pri(worst_case) == 100


def test_component_keys_are_stable():
    assert set(risk_components(reading())) == {
        "temperature", "standing_water", "organic_waste",
        "sewer_level", "ph_deviation", "clog_probability",
    }


def test_components_clamp_at_bounds():
    assert risk_components(reading(temperature_c=60))["temperature"] == 25
    assert risk_components(reading(temperature_c=-10))["temperature"] == 0
    assert risk_components(reading(ph=7))["ph_deviation"] == 0
    assert risk_components(reading(standing_water_hours=1000))["standing_water"] == 30


def test_severity_thresholds():
    assert severity(75) == "critical"
    assert severity(74.9) == "high"
    assert severity(55) == "high"
    assert severity(30) == "moderate"
    assert severity(29.9) == "low"
