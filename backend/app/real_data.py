"""Public, non-personal environmental data adapters."""
from datetime import datetime, timezone
import json
import os
import re
from urllib.parse import urlencode
from urllib.request import urlopen
from .models import TelemetryIn

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
MUNICH_OPEN311_URL = os.getenv("MUNICH_OPEN311_URL", "https://machmuenchenbesser.de/georeport/v2/requests.json")
SANITATION_TERMS = re.compile(r"abfall|container|drain|gully|kanal|m.ll|rubbish|sewer|trash|verunreinig|verschmutz|wasser", re.IGNORECASE)
REFERENCE_LOCATIONS = [
    ("MUC-ALT-01", "Altstadt-Lehel", 48.137, 11.576),
    ("MUC-SCH-02", "Schwabing", 48.166, 11.586),
    ("MUC-GIE-03", "Giesing", 48.115, 11.596),
    ("MUC-BOG-04", "Bogenhausen", 48.154, 11.633),
    ("MUC-NEU-05", "Neuhausen", 48.155, 11.531),
]

def fetch_open_meteo(latitude: float, longitude: float) -> tuple[dict, str]:
    query = urlencode({"latitude": latitude, "longitude": longitude, "current": "temperature_2m", "hourly": "precipitation", "past_hours": 24, "forecast_hours": 1, "timezone": "Europe/Berlin"})
    url = f"{OPEN_METEO_URL}?{query}"
    try:
        with urlopen(url, timeout=10) as response:  # nosec B310: fixed HTTPS provider URL
            return json.loads(response.read().decode("utf-8")), url
    except Exception as error:
        raise RuntimeError("Open-Meteo data could not be retrieved") from error

def recent_precipitation_hours(hourly: dict) -> float:
    """Exposure proxy, not a standing-water measurement."""
    return float(sum(1 for value in hourly.get("precipitation", [])[-24:] if (value or 0) >= 0.2))

def weather_observations() -> tuple[list[TelemetryIn], list[str]]:
    observations, source_urls = [], []
    for sector_id, district, latitude, longitude in REFERENCE_LOCATIONS:
        payload, source_url = fetch_open_meteo(latitude, longitude)
        temperature = payload.get("current", {}).get("temperature_2m")
        if temperature is None:
            raise RuntimeError("Open-Meteo response omitted current temperature")
        wet_hours = recent_precipitation_hours(payload.get("hourly", {}))
        observations.append(TelemetryIn(sector_id=sector_id, district=district, latitude=latitude, longitude=longitude, source="open_meteo", temperature_c=float(temperature), standing_water_hours=wet_hours, report_summary=(f"Public weather-derived exposure proxy: {wet_hours:.0f} wet hours in the preceding 24-hour window. Not a drainage, water-quality, or pathogen measurement.")))
        source_urls.append(source_url)
    return observations, source_urls

def munich_report_observations() -> tuple[list[TelemetryIn], str]:
    """Import anonymised Open311 reports as reported evidence, not measurements."""
    try:
        with urlopen(MUNICH_OPEN311_URL, timeout=10) as response:  # nosec B310: operator-configured public feed
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise RuntimeError("Munich Open311 reports could not be retrieved; verify MUNICH_OPEN311_URL with the city data owner") from error

    reports = payload.get("service_requests", payload) if isinstance(payload, dict) else payload
    if not isinstance(reports, list):
        raise RuntimeError("Munich Open311 response did not contain a request list")

    observations = []
    for report in reports[:100]:
        if not isinstance(report, dict):
            continue
        description = " ".join(str(report.get(field, "")) for field in ("service_name", "description", "status"))
        if not SANITATION_TERMS.search(description):
            continue
        latitude, longitude = report.get("lat"), report.get("long", report.get("lon"))
        if latitude is None or longitude is None:
            continue
        try:
            latitude, longitude = float(latitude), float(longitude)
        except (TypeError, ValueError):
            continue
        request_id = str(report.get("service_request_id") or report.get("id") or len(observations) + 1)
        lowered = description.lower()
        water_signal = 48 if any(term in lowered for term in ("water", "wasser", "drain", "gully", "kanal", "sewer")) else 0
        waste_signal = 65 if any(term in lowered for term in ("abfall", "müll", "muell", "trash", "rubbish", "container", "verschmutz", "verunreinig")) else 0
        observations.append(TelemetryIn(
            sector_id=f"MUC-311-{request_id}", district="Munich public report", latitude=latitude, longitude=longitude,
            source="munich_open311", temperature_c=10, standing_water_hours=water_signal,
            organic_waste_pct=waste_signal, clog_probability=80 if water_signal else 0,
            report_summary=f"Anonymised Munich Open311 report ({report.get('status', 'unknown status')}): {description[:180]}. Report-derived indicators require field verification.",
        ))
    return observations, MUNICH_OPEN311_URL

def retrieved_at() -> datetime:
    return datetime.now(timezone.utc)
