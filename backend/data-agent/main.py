from fastapi import FastAPI
from pydantic import BaseModel
import requests
import math

MASTER_URL = "http://127.0.0.1:8000/store_health"

app = FastAPI(title="AURA Data Analysis Agent - Prototype v0")


class RawTelemetry(BaseModel):
    vehicle_id: str
    sensors: dict


@app.get("/")
def root():
    return {"status": "ok", "service": "data-agent", "version": "0.0.1"}


def compute_anomaly(sensors: dict) -> tuple[float, dict]:
    """
    Very simple heuristic:
    - brake_temp above 50 → contributes to anomaly
    - vibration > 0.6 → contributes
    - engine_temp above 100 → small contribution
    """
    score = 0.0
    subsystems = {}

    brake = sensors.get("brake_temp", 40)
    vib = sensors.get("vibration", 0.2)
    eng = sensors.get("engine_temp", 90)

    # Normalize features roughly into 0-1
    brake_component = max(0.0, (brake - 40) / 30)   # 40–70°C
    vib_component = max(0.0, (vib - 0.3) / 0.7)     # 0.3–1.0
    eng_component = max(0.0, (eng - 90) / 30)       # 90–120°C

    score = 0.5 * brake_component + 0.3 * vib_component + 0.2 * eng_component
    score = min(1.0, round(score, 2))

    subsystems["brakes"] = round(brake_component, 2)
    subsystems["suspension"] = round(vib_component, 2)
    subsystems["engine"] = round(eng_component, 2)

    return score, subsystems


@app.post("/analyze")
def analyze(telemetry: RawTelemetry):
    anomaly_score, subsystems = compute_anomaly(telemetry.sensors)

    health_payload = {
        "vehicle_id": telemetry.vehicle_id,
        "anomaly_score": anomaly_score,
        "subsystems": subsystems,
    }

    # forward to Master Agent
    resp = requests.post(MASTER_URL, json=health_payload, timeout=2)
    return {
        "anomaly_score": anomaly_score,
        "subsystems": subsystems,
        "master_status": resp.status_code,
    }