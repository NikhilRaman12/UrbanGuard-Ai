"""Multimodal evidence analysis for sanitation triage.

This module fuses three evidence modalities into an explainable decision-support
signal:

* tabular telemetry (the existing PRI)
* image evidence (citizen/crew photos of standing water, waste, or flooding)
* text evidence (free-text citizen reports)

Every output is a transparent, deterministic triage proxy. These are NOT
classifiers and NOT diagnoses: they prioritise where a human should look first.
No image or text leaves the deployment boundary for inference.
"""
from io import BytesIO

from PIL import Image, UnidentifiedImageError

MAX_EDGE = 256
MIN_PIXELS = 4096

TEXT_TAXONOMY = {
    "standing_water": (["standing water", "stagnant", "pooled", "puddle", "stehendes wasser", "eaux stagnantes", "ristagn", "water accumulation"], 22),
    "waste": (["waste", "trash", "rubbish", "garbage", "abfall", "müll", "muell", "litter", "dumping", "overflowing bin"], 20),
    "sewage": (["sewage", "sewer overflow", "faeces", "fecal", "effluent", "kanal", "sewerage"], 26),
    "drainage_blockage": (["blocked drain", "clogged", "gully", "verstopft", "drain blocked"], 18),
    "odor": (["smell", "odour", "odor", "stench", "geruch", "gestank"], 12),
    "rodent": (["rat", "rats", "rodent", "mice", "ratt", "maus"], 18),
    "contamination": (["contaminat", "pollut", "verunreinig", "verschmutz", "hazard", "toxic"], 24),
}


def analyse_image(data: bytes) -> dict:
    """Extract deterministic colour/texture triage features from an image."""
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("Unsupported or corrupt image file") from error

    image = image.convert("RGB")
    image.thumbnail((MAX_EDGE, MAX_EDGE))
    total = image.width * image.height
    raw = image.tobytes()

    water = green = dark = 0
    brightness_sum = 0.0
    for r, g, b in zip(raw[0::3], raw[1::3], raw[2::3]):
        brightness = (r + g + b) / 3
        brightness_sum += brightness
        maximum, minimum = max(r, g, b), min(r, g, b)
        saturation = 0.0 if maximum == 0 else (maximum - minimum) / maximum
        if b >= r + 4 and b >= g and 25 <= brightness <= 205 and saturation <= 0.5:
            water += 1
        elif g >= r + 12 and g >= b + 12:
            green += 1
        if brightness < 60 and saturation <= 0.35:
            dark += 1

    mean_brightness = brightness_sum / total if total else 0.0
    water_fraction = water / total if total else 0.0
    green_fraction = green / total if total else 0.0
    dark_fraction = dark / total if total else 0.0

    quality = "low" if total < MIN_PIXELS or mean_brightness < 25 else "ok"
    return {
        "modality": "image",
        "width": image.width,
        "height": image.height,
        "mean_brightness": round(mean_brightness, 1),
        "water_like_fraction": round(water_fraction, 4),
        "vegetation_fraction": round(green_fraction, 4),
        "dark_low_saturation_fraction": round(dark_fraction, 4),
        "visual_water_score": min(100.0, round(water_fraction * 250, 1)),
        "visual_waste_score": min(100.0, round(dark_fraction * 180, 1)),
        "quality": quality,
        "note": "Colour/texture triage proxy only; confirm with a field inspection. Not a classification of pathogens or contamination.",
    }


def analyse_text(text: str) -> dict:
    """Map free-text reports onto a fixed sanitation taxonomy."""
    lowered = text.lower()
    categories: dict[str, int] = {}
    matched: list[str] = []
    score = 0.0
    for category, (terms, weight) in TEXT_TAXONOMY.items():
        hits = [term for term in terms if term in lowered]
        if hits:
            categories[category] = len(hits)
            matched.extend(hits)
            score += weight
    return {
        "modality": "text",
        "categories": categories,
        "matched_terms": sorted(set(matched)),
        "text_signal_score": min(100.0, round(score, 1)),
        "note": "Keyword taxonomy triage only; citizen wording is operational evidence, not a verified measurement.",
    }


def fuse_modalities(telemetry_pri: float | None = None, visual: float | None = None, text: float | None = None) -> dict:
    """Weighted, explainable fusion of the available modality signals."""
    signals = []
    if telemetry_pri is not None:
        signals.append(("telemetry", float(telemetry_pri), 0.60))
    if visual is not None:
        signals.append(("visual", float(visual), 0.25))
    if text is not None:
        signals.append(("text", float(text), 0.15))

    total_weight = sum(weight for _, _, weight in signals)
    if total_weight == 0:
        return {"score": 0.0, "contributions": {}, "modalities": [], "explanation": "No evidence available."}

    score = round(sum(value * weight for _, value, weight in signals) / total_weight, 1)
    contributions = {name: round(value * weight / total_weight, 1) for name, value, weight in signals}
    explanation = (
        "Fused score from " + ", ".join(f"{name} ({value:g} @ {weight:.0%})" for name, value, weight in signals)
        + ". Telemetry dominates; image and text evidence adjust the ranking. Human verification remains mandatory."
    )
    return {
        "score": score,
        "contributions": contributions,
        "modalities": [name for name, _, _ in signals],
        "explanation": explanation,
    }
