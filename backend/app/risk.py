from .models import TelemetryIn

def calculate_pri(t: TelemetryIn) -> float:
    return round(min(100, sum(risk_components(t).values())), 1)

def risk_components(t: TelemetryIn) -> dict[str, float]:
    temperature = max(0, min(25, (t.temperature_c - 10) * 1.25))
    standing = min(30, t.standing_water_hours / 72 * 30)
    waste = min(20, t.organic_waste_pct * .2)
    sewer = min(10, max(0, t.sewer_level_pct - 70) / 3)
    ph = min(5, abs(t.ph - 7) * 2.5)
    clog = min(10, t.clog_probability * .1)
    return {
        "temperature": round(temperature, 1),
        "standing_water": round(standing, 1),
        "organic_waste": round(waste, 1),
        "sewer_level": round(sewer, 1),
        "ph_deviation": round(ph, 1),
        "clog_probability": round(clog, 1),
    }

def severity(pri: float): return "critical" if pri >= 75 else "high" if pri >= 55 else "moderate" if pri >= 30 else "low"
