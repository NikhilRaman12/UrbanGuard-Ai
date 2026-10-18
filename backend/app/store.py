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
    c.executescript('''CREATE TABLE IF NOT EXISTS telemetry (id INTEGER PRIMARY KEY, sector_id TEXT, district TEXT, latitude REAL, longitude REAL, source TEXT, payload TEXT, pri REAL, observed_at TEXT, synthetic INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY, agent TEXT, message TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS work_orders (id INTEGER PRIMARY KEY, sector_id TEXT, title TEXT, priority TEXT, status TEXT, protocol_refs TEXT, created_at TEXT, decided_by TEXT, decided_at TEXT);
    CREATE TABLE IF NOT EXISTS evidence (id INTEGER PRIMARY KEY, sector_id TEXT, modality TEXT, latitude REAL, longitude REAL, caption TEXT, features TEXT, score REAL, observed_at TEXT);''')
    _ensure_column(c, "telemetry", "synthetic", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(c, "work_orders", "decided_by", "TEXT")
    _ensure_column(c, "work_orders", "decided_at", "TEXT")
    c.commit(); c.close()
def _ensure_column(c, table, column, definition):
    existing = {row[1] for row in c.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
def has_telemetry():
    c=conn(); value=c.execute("SELECT EXISTS(SELECT 1 FROM telemetry)").fetchone()[0]; c.close(); return bool(value)
def sector_ids():
    c=conn(); values={row[0] for row in c.execute("SELECT DISTINCT sector_id FROM telemetry")}; c.close(); return values
def now(): return datetime.now(timezone.utc).isoformat()
def add_telemetry(t: TelemetryIn, pri: float, synthetic: bool = False):
    c=conn(); c.execute("INSERT INTO telemetry (sector_id,district,latitude,longitude,source,payload,pri,observed_at,synthetic) VALUES (?,?,?,?,?,?,?,?,?)",(t.sector_id,t.district,t.latitude,t.longitude,t.source,t.model_dump_json(),pri,now(),1 if synthetic else 0)); c.commit(); c.close()
def latest_points():
    c=conn(); rows=c.execute('''SELECT t.* FROM telemetry t JOIN (SELECT sector_id, MAX(id) x FROM telemetry GROUP BY sector_id) l ON t.id=l.x ORDER BY t.pri DESC''').fetchall(); c.close(); return rows
def summary():
    rows = latest_points()
    source_counts = {}
    for row in rows:
        source_counts[row["source"]] = source_counts.get(row["source"], 0) + 1
    latest = max((row["observed_at"] for row in rows), default=None)
    synthetic = sum(1 for row in rows if row["synthetic"])
    if rows and synthetic == len(rows):
        data_mode = "synthetic_training_snapshot"
    elif synthetic:
        data_mode = "mixed_sources"
    else:
        data_mode = "live_connector"
    return {
        "locations": len(rows),
        "critical": sum(row["pri"] >= 75 for row in rows),
        "high": sum(55 <= row["pri"] < 75 for row in rows),
        "moderate": sum(30 <= row["pri"] < 55 for row in rows),
        "low": sum(row["pri"] < 30 for row in rows),
        "source_counts": source_counts,
        "latest_observation": latest,
        "data_mode": data_mode,
        "synthetic_locations": synthetic,
        "pending_approval": sum(1 for row in orders() if row["status"] == "pending_approval"),
    }
def evidence_for(row):
    try: return json.loads(row["payload"]).get("report_summary")
    except (json.JSONDecodeError, TypeError): return None
def log(agent,message):
    c=conn(); c.execute("INSERT INTO activity (agent,message,created_at) VALUES (?,?,?)",(agent,message,now())); c.commit(); c.close()
def activities():
    c=conn(); r=c.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 40").fetchall(); c.close(); return r
def create_order(sector,title,priority,refs):
    c=conn(); cursor=c.execute("INSERT INTO work_orders (sector_id,title,priority,status,protocol_refs,created_at) VALUES (?,?,?,?,?,?)",(sector,title,priority,"pending_approval",json.dumps(refs),now())); order_id=cursor.lastrowid; c.commit(); c.close(); return order_id
def order_by_id(order_id):
    c=conn(); row=c.execute("SELECT * FROM work_orders WHERE id=?",(order_id,)).fetchone(); c.close(); return row
def decide_order(order_id, decision, actor):
    status = "approved" if decision == "approve" else "rejected"
    c=conn(); cursor=c.execute("UPDATE work_orders SET status=?, decided_by=?, decided_at=? WHERE id=? AND status='pending_approval'",(status,actor,now(),order_id)); changed=cursor.rowcount; c.commit(); c.close(); return changed > 0
def orders():
    c=conn(); r=c.execute("SELECT * FROM work_orders ORDER BY id DESC LIMIT 20").fetchall(); c.close(); return r
def add_evidence(sector_id, modality, latitude, longitude, caption, features, score):
    c=conn(); cursor=c.execute("INSERT INTO evidence (sector_id,modality,latitude,longitude,caption,features,score,observed_at) VALUES (?,?,?,?,?,?,?,?)",(sector_id,modality,latitude,longitude,caption,json.dumps(features),score,now())); evidence_id=cursor.lastrowid; c.commit(); c.close(); return evidence_id
def evidence_by_sector(sector_id):
    c=conn(); r=c.execute("SELECT * FROM evidence WHERE sector_id=? ORDER BY id DESC",(sector_id,)).fetchall(); c.close(); return r
def latest_evidence(sector_id):
    c=conn(); r=c.execute("SELECT * FROM evidence WHERE sector_id=? ORDER BY id DESC LIMIT 1",(sector_id,)).fetchone(); c.close(); return r
def evidence_by_id(evidence_id):
    c=conn(); r=c.execute("SELECT * FROM evidence WHERE id=?",(evidence_id,)).fetchone(); c.close(); return r

# Keeps direct function and test-client use safe; Uvicorn also calls this idempotently at startup.
init_db()
