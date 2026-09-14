"""Deterministic synthetic scenario for demonstrations when live feeds are unavailable."""
import json
from pathlib import Path
from .models import TelemetryIn

SCENARIO_FILE = Path(__file__).parent.parent / "data" / "realistic_scenario.json"

def realistic_scenario() -> list[TelemetryIn]:
    return [TelemetryIn.model_validate(item) for item in json.loads(SCENARIO_FILE.read_text(encoding="utf-8"))]
