import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import streamlit as st

st.set_page_config(
    page_title="UrbanGuard AI | Municipal Operations",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

try:
    configured_api = st.secrets.get("URBANGUARD_API_URL")
except FileNotFoundError:
    configured_api = None
API_BASE = str(configured_api or os.getenv("URBANGUARD_API_URL", "http://localhost:8000")).rstrip("/")
API_ROOT = f"{API_BASE}/api/v1"
SCENARIO_FILE = Path(__file__).resolve().parent.parent / "backend" / "data" / "realistic_scenario.json"

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root { --ink:#e3eadd; --muted:#91a69c; --line:#293c36; --panel:#0c1714; --lime:#a9ff54; --bg:#07100f; }
    .stApp { background: var(--bg); color: var(--ink); }
    .stApp > header { background: transparent; }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1480px; padding: 1rem 2rem 3rem; }
    .brand-row { height: 62px; border-bottom:1px solid var(--line); display:flex; align-items:center; justify-content:space-between; }
    .brand { display:flex; align-items:center; gap:10px; color:var(--ink); font:800 16px Manrope,sans-serif; letter-spacing:1px; }
    .brand-mark { color:var(--lime); font-size:24px; }
    .brand small, .sovereign, .eyebrow, .mono { font-family:'DM Mono',monospace; }
    .brand small { color:#7e958c; font-size:10px; margin-left:4px; font-weight:400; }
    .sovereign { color:var(--lime); font-size:11px; }
    .dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--lime); margin-right:8px; box-shadow:0 0 10px var(--lime); }
    .hero { padding:3.7rem 0 1.3rem; }
    .eyebrow { color:var(--lime); font-size:11px; letter-spacing:1.5px; }
    h1 { color:var(--ink)!important; font:800 clamp(38px,5vw,71px)/1.04 Manrope,sans-serif!important; letter-spacing:-3px!important; margin:12px 0!important; }
    .hero em { color:var(--lime); font-style:normal; }
    .sub { max-width:560px; color:var(--muted); line-height:1.7; font:15px/1.7 Manrope,sans-serif; }
    .notice { border:1px solid #2e423c; background:#0b1714; color:#bdd0c7; padding:11px 13px; font:12px 'DM Mono',monospace; margin:0 0 18px; }
    .panel { background:var(--panel); border:1px solid var(--line); padding:0; }
    .panel-title { border-bottom:1px solid var(--line); padding:16px 18px; display:flex; justify-content:space-between; align-items:center; color:#b9cac1; font:11px 'DM Mono',monospace; }
    .panel-title b { color:#70837b; font-size:10px; font-weight:400; }
    .map-surface { min-height:305px; position:relative; overflow:hidden; background-color:#10221d; background-image:linear-gradient(#1d332c 1px,transparent 1px),linear-gradient(90deg,#1d332c 1px,transparent 1px); background-size:52px 52px; padding:24px; }
    .map-surface:after { content:''; position:absolute; width:120%; height:58px; top:47%; left:-8%; background:#143b39; transform:rotate(-10deg); opacity:.8; }
    .map-empty { min-height:255px; display:grid; place-items:center; text-align:center; color:#71857c; font:12px 'DM Mono',monospace; position:relative; z-index:2; }
    .pin-grid { position:relative; z-index:3; display:flex; gap:20px; flex-wrap:wrap; align-items:center; min-height:255px; }
    .pin { width:67px; height:67px; border-radius:50%; display:grid; place-content:center; text-align:center; color:#07100f; border:3px solid #dcebd3; box-shadow:0 0 0 6px #ffffff16; font-family:'DM Mono',monospace; }
    .pin strong { font-size:17px; line-height:1; }.pin span { font-size:8px; margin-top:4px; }
    .low { background:#a9ff54; }.moderate { background:#ffd166; }.high { background:#ff944d; }.critical { background:#ff5656; }
    .legend { padding:13px 18px; color:#8fa39a; font:10px 'DM Mono',monospace; border-top:1px solid var(--line); }
    .legend i { display:inline-block; width:8px; height:8px; border-radius:50%; margin:0 6px 0 15px; }.legend i:first-child { margin-left:0; }
    .evidence { padding:14px 18px; border-top:1px solid var(--line); background:#0a1412; }
    .evidence strong { display:block; color:var(--lime); font:12px 'DM Mono',monospace; }.evidence span,.evidence small { display:block; color:#91a69c; line-height:1.5; font:11px 'DM Mono',monospace; margin-top:6px; }
    .chips { display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }.chip { color:#c3d3cb; background:#12231e; padding:5px 7px; font:10px 'DM Mono',monospace; }.chip b { color:var(--lime); margin-left:4px; }
    .feed { max-height:390px; overflow:auto; }.event { padding:14px 18px; border-bottom:1px solid #20332c; }.event-agent { color:var(--lime); font:10px 'DM Mono',monospace; text-transform:uppercase; }.event p { color:#c4d1ca; font:12px/1.5 Manrope,sans-serif; margin:5px 0; }.event time { color:#5e746a; font:9px 'DM Mono',monospace; }
    .order { padding:15px 18px; border-bottom:1px solid #20332c; }.order strong { color:var(--ink); font:600 13px Manrope,sans-serif; }.order p { color:#71857c; font:11px 'DM Mono',monospace; margin:4px 0 8px; }.status { color:#ffd166; border:1px solid #715b29; display:inline-block; padding:5px 8px; text-transform:uppercase; font:9px 'DM Mono',monospace; }
    .stButton > button { border-radius:0; border:1px solid var(--line); background:#11231e; color:var(--ink); font:700 11px Manrope,sans-serif; min-height:42px; }
    .stButton > button:hover { border-color:var(--lime); color:var(--lime); }.hero-actions .stButton > button { background:var(--lime); color:#0b1814; border-color:var(--lime); }
    div[data-testid="stAlert"] { border-radius:0; }.caption { color:#71857c; font:10px/1.5 'DM Mono',monospace; }
    @media (max-width: 800px) { .block-container { padding:1rem 1rem 2rem; }.hero { padding-top:2rem; }.sovereign { display:none; } }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_request(path: str, method: str = "get", **kwargs: Any) -> Any:
    response = requests.request(method, f"{API_ROOT}/{path.lstrip('/')}", timeout=15, **kwargs)
    response.raise_for_status()
    return response.json()


def score_components(record: dict[str, Any]) -> dict[str, float]:
    components = {
        "temperature": max(0, min(25, (record.get("temperature_c", 18) - 10) * 1.25)),
        "standing_water": min(30, record.get("standing_water_hours", 0) / 72 * 30),
        "organic_waste": min(20, record.get("organic_waste_pct", 0) * 0.2),
        "sewer_level": min(10, max(0, record.get("sewer_level_pct", 0) - 70) / 3),
        "ph_deviation": min(5, abs(record.get("ph", 7) - 7) * 2.5),
        "clog_probability": min(10, record.get("clog_probability", 0) * 0.1),
    }
    return {name: round(value, 1) for name, value in components.items()}


def severity(pri: float) -> str:
    return "critical" if pri >= 75 else "high" if pri >= 55 else "moderate" if pri >= 30 else "low"


def offline_scenario() -> list[dict[str, Any]]:
    records = json.loads(SCENARIO_FILE.read_text(encoding="utf-8"))
    points = []
    for record in records:
        components = score_components(record)
        pri = round(min(100, sum(components.values())), 1)
        points.append({
            **record,
            "pri": pri,
            "severity": severity(pri),
            "source": record.get("source", "synthetic_scenario"),
            "evidence": record.get("report_summary"),
            "components": components,
        })
    return sorted(points, key=lambda point: point["pri"], reverse=True)


def offline_event(agent: str, message: str) -> dict[str, Any]:
    return {
        "id": len(st.session_state.events) + 1,
        "agent": agent,
        "message": message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_offline_action(path: str, label: str, **kwargs: Any) -> None:
    points = st.session_state.points or offline_scenario()
    st.session_state.points = points
    st.session_state.demo_mode = True
    if path.endswith("trigger-dispatch"):
        sector_id = kwargs.get("json", {}).get("sector_id")
        point = next((item for item in points if item["sector_id"] == sector_id), None)
        if point and point["pri"] >= 30:
            refs = '["BAV-WS-01", "BAV-OHS-02"]'
            st.session_state.orders.insert(0, {
                "id": len(st.session_state.orders) + 1,
                "sector_id": sector_id,
                "title": f"Inspect and mitigate vector breeding risk - {point['district']}",
                "priority": "P1 - same day" if point["pri"] >= 75 else "P2 - within 24 hours",
                "status": "pending_approval",
                "protocol_refs": refs,
            })
            message = f"Drafted human-review work order for {sector_id}; no action was published."
            st.session_state.notice = f"Offline demo: dispatch drafted for {sector_id}. Human approval required."
        else:
            message = f"Monitored {sector_id}; risk remains below the dispatch threshold."
            st.session_state.notice = "Offline demo: location remains in monitoring state."
        st.session_state.events.insert(0, offline_event("Dispatcher & Compliance Copilot", message))
    else:
        st.session_state.notice = f"Offline demo: {label.lower()} using synthetic Munich training records."
        st.session_state.events.insert(0, offline_event("Scenario Data Loader", st.session_state.notice))


def load_dashboard() -> None:
    try:
        points, events, orders = (
            api_request(path)
            for path in ("risks/heatmap", "activity", "work-orders")
        )
        st.session_state.points = points
        st.session_state.events = events
        st.session_state.orders = orders
        st.session_state.api_error = None
        st.session_state.demo_mode = False
    except requests.RequestException as error:
        st.session_state.api_error = f"Live API unavailable at {API_BASE}. Showing offline demo data. ({error})"
        st.session_state.demo_mode = True
        if not st.session_state.points:
            st.session_state.points = offline_scenario()
            st.session_state.events = [offline_event("Scenario Data Loader", "Loaded deterministic synthetic Munich records for offline demonstration.")]
            st.session_state.notice = "Offline demo mode: synthetic training scenario loaded. No live municipal action is possible."


def run_action(path: str, label: str, method: str = "post", **kwargs: Any) -> None:
    if st.session_state.get("demo_mode"):
        run_offline_action(path, label, **kwargs)
        return
    try:
        result = api_request(path, method, **kwargs)
        st.session_state.notice = f"{label}: {result.get('ingested', result.get('action', 'completed'))}"
    except requests.RequestException as error:
        st.session_state.notice = f"{label} failed: {error}"
    load_dashboard()


for key, default in (("points", []), ("events", []), ("orders", []), ("notice", "System ready - local data boundary active."), ("selected", None), ("api_error", None), ("demo_mode", False)):
    st.session_state.setdefault(key, default)
load_dashboard()

st.markdown('<div class="brand-row"><div class="brand"><span class="brand-mark">◈</span> URBANGUARD <small>AI / MUNICIPAL OPS</small></div><div class="sovereign"><span class="dot"></span>EU SOVEREIGN · LOCAL-FIRST</div></div>', unsafe_allow_html=True)

hero, actions = st.columns([1.45, 1], gap="large")
with hero:
    st.markdown('<div class="hero"><div class="eyebrow">MUNICH / BAVARIA REFERENCE LOCATIONS</div><h1>Sanitation intelligence<br><em>at city scale.</em></h1><div class="sub">Combine public environmental evidence with authorised municipal feeds. Every dispatch remains auditable and requires human approval.</div></div>', unsafe_allow_html=True)
with actions:
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    st.markdown('<div class="caption">LIVE DATA CONNECTORS</div>', unsafe_allow_html=True)
    if st.button("↓  REFRESH REAL WEATHER", use_container_width=True):
        run_action("data/refresh-weather", "Real weather refreshed")
    if st.button("▣  REFRESH CITY REPORTS", use_container_width=True):
        run_action("data/refresh-munich-reports", "City reports refreshed")
    if st.button("⌖  LOAD REALISTIC SCENARIO", use_container_width=True):
        run_action("data/load-realistic-scenario", "Training scenario loaded")
    if st.button("▶  RUN DEMO DATA", use_container_width=True):
        run_action("simulation/tick", "Demo telemetry ingested")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f'<div class="notice">◉ {html.escape(st.session_state.notice)}</div>', unsafe_allow_html=True)
if st.session_state.api_error:
    st.error(st.session_state.api_error)
if st.session_state.demo_mode:
    st.warning("OFFLINE DEMO MODE: all records are synthetic training data. Verify with authorised field data before any operational decision.")

map_col, activity_col = st.columns([1.4, 0.9], gap="medium")
with map_col:
    points = st.session_state.points
    st.markdown(f'<div class="panel"><div class="panel-title"><span>⌖ &nbsp; CITY RISK MAP</span><b>{len(points)} ACTIVE LOCATIONS</b></div>', unsafe_allow_html=True)
    if points:
        pins = []
        for point in points:
            severity = point.get("severity", "low")
            district = html.escape(point.get("district", "Unknown").split("-")[0])
            pins.append(f'<div class="pin {severity}"><strong>{point.get("pri", 0):g}</strong><span>{district}</span></div>')
        st.markdown(f'<div class="map-surface"><div class="pin-grid">{"".join(pins)}</div></div>', unsafe_allow_html=True)
        choices = {f'{point["district"]} · PRI {point["pri"]}': point for point in points}
        selected_label = st.selectbox("Inspect a location", ["Select a location"] + list(choices), label_visibility="collapsed")
        if selected_label != "Select a location":
            st.session_state.selected = choices[selected_label]
    else:
        st.markdown('<div class="map-surface"><div class="map-empty">Refresh real weather or load clearly labelled demo data.</div></div>', unsafe_allow_html=True)
    selected = st.session_state.selected
    if selected:
        components = selected.get("components", {})
        chips = "".join(f'<span class="chip">{html.escape(name.replace("_", " "))} <b>{value:g}</b></span>' for name, value in components.items())
        evidence = html.escape(selected.get("evidence") or "No free-text evidence attached.")
        st.markdown(f'<div class="evidence"><strong>{html.escape(selected["district"])} · PRI {selected["pri"]}/100</strong><span>{html.escape(selected.get("source", "unknown"))} · transparent score contributors</span><div class="chips">{chips}</div><small>{evidence}</small></div>', unsafe_allow_html=True)
        if st.button("DRAFT REVIEWED DISPATCH", use_container_width=True):
            run_action("agents/trigger-dispatch", f"Dispatch drafted for {selected['sector_id']}", json={"sector_id": selected["sector_id"]})
    st.markdown('<div class="legend"><i class="low"></i>LOW <i class="moderate"></i>MODERATE <i class="high"></i>HIGH <i class="critical"></i>CRITICAL · evidence is decision support, not diagnosis</div></div>', unsafe_allow_html=True)

with activity_col:
    events = st.session_state.events
    st.markdown(f'<div class="panel"><div class="panel-title"><span>◌ &nbsp; AGENT ACTIVITY FEED</span><b>LIVE AUDIT</b></div><div class="feed">', unsafe_allow_html=True)
    if events:
        for event in events:
            st.markdown(f'<div class="event"><div class="event-agent">{html.escape(event.get("agent", "Agent"))}</div><p>{html.escape(event.get("message", ""))}</p><time>{html.escape(event.get("created_at", ""))}</time></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="map-empty">No agent activity yet.</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

st.markdown('<div class="panel" style="margin-top:18px"><div class="panel-title"><span>▤ &nbsp; WORK ORDER & ALERT MANAGER</span><b>HUMAN APPROVAL REQUIRED</b></div>', unsafe_allow_html=True)
if st.session_state.orders:
    for order in st.session_state.orders:
        refs = html.escape(order.get("protocol_refs", ""))
        st.markdown(f'<div class="order"><strong>{html.escape(order.get("title", "Untitled work order"))}</strong><p>{html.escape(order.get("sector_id", ""))} · {html.escape(order.get("priority", ""))} · Protocol refs: {refs}</p><span class="status">{html.escape(order.get("status", "pending approval").replace("_", " "))}</span></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="map-empty">Draft a high-risk dispatch to create an auditable work order.</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="caption" style="margin-top:16px">UrbanGuard AI is a municipal decision-support prototype. Public weather and citizen reports are exposure or triage signals only. Verify with authorised field, drainage, waste, or laboratory data before operational action.</div>', unsafe_allow_html=True)
