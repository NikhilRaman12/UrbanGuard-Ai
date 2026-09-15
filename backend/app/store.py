import json, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from .models import TelemetryIn

DB = Path(__file__).parent.parent / "data" / "urbanguard.db"
def conn():
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c
def init_db():
    c=conn()
    c.executescript('''CREATE TABLE IF NOT EXISTS telemetry (id INTEGER PRIMARY KEY, sector_id TEXT, district TEXT, latitude REAL, longitude REAL, source TEXT, payload TEXT, pri REAL, observed_at TEXT);
    CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY, agent TEXT, message TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS work_orders (id INTEGER PRIMARY KEY, sector_id TEXT, title TEXT, priority TEXT, status TEXT, protocol_refs TEXT, created_at TEXT);''')
    c.commit(); c.close()
def has_telemetry():
    c=conn(); value=c.execute("SELECT EXISTS(SELECT 1 FROM telemetry)").fetchone()[0]; c.close(); return bool(value)
def sector_ids():
    c=conn(); values={row[0] for row in c.execute("SELECT DISTINCT sector_id FROM telemetry")}; c.close(); return values
def now(): return datetime.now(timezone.utc).isoformat()
def add_telemetry(t: TelemetryIn, pri: float):
    c=conn(); c.execute("INSERT INTO telemetry (sector_id,district,latitude,longitude,source,payload,pri,observed_at) VALUES (?,?,?,?,?,?,?,?)",(t.sector_id,t.district,t.latitude,t.longitude,t.source,t.model_dump_json(),pri,now())); c.commit(); c.close()
def latest_points():
    c=conn(); rows=c.execute('''SELECT t.* FROM telemetry t JOIN (SELECT sector_id, MAX(id) x FROM telemetry GROUP BY sector_id) l ON t.id=l.x ORDER BY t.pri DESC''').fetchall(); c.close(); return rows
def summary():
    rows = latest_points()
    source_counts = {}
    for row in rows:
        source_counts[row["source"]] = source_counts.get(row["source"], 0) + 1
    latest = max((row["observed_at"] for row in rows), default=None)
    return {
        "locations": len(rows),
        "critical": sum(row["pri"] >= 75 for row in rows),
        "high": sum(55 <= row["pri"] < 75 for row in rows),
        "moderate": sum(30 <= row["pri"] < 55 for row in rows),
        "low": sum(row["pri"] < 30 for row in rows),
        "source_counts": source_counts,
        "latest_observation": latest,
        "data_mode": "synthetic_training_snapshot" if any(row["source"] == "citizen_report" for row in rows) else "live_connector",
    }
def evidence_for(row):
    try: return json.loads(row["payload"]).get("report_summary")
    except (json.JSONDecodeError, TypeError): return None
def log(agent,message):
    c=conn(); c.execute("INSERT INTO activity (agent,message,created_at) VALUES (?,?,?)",(agent,message,now())); c.commit(); c.close()
def activities():
    c=conn(); r=c.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 40").fetchall(); c.close(); return r
def create_order(sector,title,priority,refs):
    c=conn(); c.execute("INSERT INTO work_orders (sector_id,title,priority,status,protocol_refs,created_at) VALUES (?,?,?,?,?,?)",(sector,title,priority,"pending_approval",json.dumps(refs),now())); c.commit(); c.close()
def orders():
    c=conn(); r=c.execute("SELECT * FROM work_orders ORDER BY id DESC LIMIT 20").fetchall(); c.close(); return r

# Keeps direct function and test-client use safe; Uvicorn also calls this idempotently at startup.
init_db()
