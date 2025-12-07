from fastapi import FastAPI
from pydantic import BaseModel
import psycopg2
import json
from typing import List
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AURA Master Agent - Prototype v0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store: dict[str, str] = {}


class VehicleHealth(BaseModel):
    vehicle_id: str
    anomaly_score: float
    subsystems: dict
    # Optional snapshot of raw sensors that produced this health record
    sensor_snapshot: dict | None = None


def get_db_conn():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="aura",
        user="postgres",
        password="postgres",
    )


@app.get("/")
def root():
    return {"status": "ok", "service": "master-agent", "version": "0.0.4"}


@app.post("/store_health")
def store_health(health: VehicleHealth):
    key = f"health:{health.vehicle_id}"
    store[key] = health.model_dump_json()

    conn = get_db_conn()
    cur = conn.cursor()
    sensor_snapshot_json = json.dumps(health.sensor_snapshot) if health.sensor_snapshot else None
    cur.execute(
        """
        INSERT INTO health_snapshots (vehicle_id, anomaly_score, subsystems, sensor_snapshot)
        VALUES (%s, %s, %s, %s)
        """,
        (health.vehicle_id, health.anomaly_score, json.dumps(health.subsystems), sensor_snapshot_json),
    )
    conn.commit()
    cur.close()
    conn.close()

    return {"stored": True, "key": key}


@app.get("/health/{vehicle_id}")
def get_health(vehicle_id: str):
    key = f"health:{vehicle_id}"
    data = store.get(key)
    return {"vehicle_id": vehicle_id, "health": data}


@app.get("/history/{vehicle_id}")
def get_history(vehicle_id: str, limit: int = 20):
    """
    Return last N (default 20) health snapshots from DB for this vehicle.
    """
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT anomaly_score, subsystems, created_at
        FROM health_snapshots
        WHERE vehicle_id = %s
        ORDER BY id DESC
        LIMIT %s
        """,
        (vehicle_id, limit),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    history = []
    for score, subsystems, created_at in rows:
        # subsystems is already JSONB, but psycopg returns as dict or str depending on driver
        if isinstance(subsystems, str):
            subsystems = json.loads(subsystems)
        history.append(
            {
                "anomaly_score": score,
                "subsystems": subsystems,
                "timestamp": created_at.isoformat(),
            }
        )

    # Reverse so oldest first, easiest for charts
    history.reverse()
    return {"vehicle_id": vehicle_id, "points": history}


@app.get("/vehicles")
def list_vehicles():
    """
    Return all distinct vehicle_ids with latest anomaly_score and a status bucket.
    """
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT vehicle_id
        FROM health_snapshots
        ORDER BY vehicle_id
        """
    )
    ids = [row[0] for row in cur.fetchall()]

    vehicles: List[dict] = []

    for vid in ids:
        key = f"health:{vid}"
        latest = store.get(key)
        anomaly = None
        status = "unknown"

        if latest:
            data = json.loads(latest)
            anomaly = float(data.get("anomaly_score", 0.0))
            if anomaly > 0.3:
                status = "critical"
            elif anomaly > 0.18:
                status = "warning"
            else:
                status = "ok"

        vehicles.append(
            {
                "vehicle_id": vid,
                "anomaly_score": anomaly,
                "status": status,
            }
        )

    cur.close()
    conn.close()

    return {"vehicles": vehicles}


@app.get("/contact_decision/{vehicle_id}")
def contact_decision(vehicle_id: str):
    key = f"health:{vehicle_id}"
    data = store.get(key)
    if not data:
        return {
            "vehicle_id": vehicle_id,
            "should_contact": False,
            "reason": "no_recent_health_data",
        }

    parsed = json.loads(data)
    score = float(parsed.get("anomaly_score", 0.0))

    if score > 0.3:
        level = "critical"
        reason = "high_risk_failure_predicted"
        should_contact = True
    elif score > 0.18:
        level = "warning"
        reason = "moderate_risk_recommend_scheduling"
        should_contact = True
    else:
        level = "ok"
        reason = "low_risk_no_immediate_action"
        should_contact = False

    return {
        "vehicle_id": vehicle_id,
        "anomaly_score": score,
        "severity": level,
        "should_contact": should_contact,
        "reason": reason,
    }

@app.get("/mfg/summary")
def mfg_summary():
    """
    Simple manufacturing view: counts by status and top risky vehicles.
    """
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT vehicle_id,
               anomaly_score,
               created_at
        FROM health_snapshots
        WHERE id IN (
          SELECT DISTINCT ON (vehicle_id)
                 id
          FROM health_snapshots
          ORDER BY vehicle_id, id DESC
        )
        ORDER BY anomaly_score DESC NULLS LAST
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    vehicles = []
    counts = {"ok": 0, "warning": 0, "critical": 0, "unknown": 0}
    for vid, score, ts in rows:
        level = "unknown"
        if score is not None:
            if score > 0.3:
                level = "critical"
            elif score > 0.18:
                level = "warning"
            else:
                level = "ok"
        counts[level] = counts.get(level, 0) + 1
        vehicles.append(
            {
                "vehicle_id": vid,
                "anomaly_score": float(score) if score is not None else None,
                "severity": level,
                "timestamp": ts.isoformat() if ts else None,
            }
        )

    top5 = vehicles[:5]
    return {
        "counts": counts,
        "fleet_size": len(vehicles),
        "top_risk": top5,
    }
