from fastapi import FastAPI
from pydantic import BaseModel
import requests
import math
import joblib
import numpy as np
import os

MASTER_URL = "http://127.0.0.1:8000/store_health"

# Load the trained ML model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "isoforest.pkl")
ML_MODEL = None
try:
    if os.path.exists(MODEL_PATH):
        ML_MODEL = joblib.load(MODEL_PATH)
        print(f"✓ ML model loaded from {MODEL_PATH}")
    else:
        print(f"Warning: ML model not found at {MODEL_PATH}. ML scoring will be skipped.")
except Exception as e:
    print(f"Error loading ML model: {e}")

FEATURE_KEYS = [
    "vehicle_speed_kmh",
    "engine_rpm",
    "coolant_temp_c",
    "oil_temp_c",
    "battery_voltage_v",
    "brake_disc_temp_c",
    "vibration_rms_g",
    "tire_pressure_psi",
    "hard_brake_events",
    "dtc_count",
]

app = FastAPI(title="AURA Data Analysis Agent - Prototype v0")


class RawTelemetry(BaseModel):
    vehicle_id: str
    sensors: dict


@app.get("/")
def root():
    return {"status": "ok", "service": "data-agent", "version": "0.0.1", "ml_model_loaded": ML_MODEL is not None}


def compute_ml_anomaly(sensors: dict) -> tuple[float, str]:
    """
    Score telemetry using trained Isolation Forest model.
    Returns: (anomaly_score, label) where score in [0, 1] and label is "normal" or "anomaly".
    """
    if ML_MODEL is None:
        return 0.0, "unknown"
    
    try:
        # Extract feature vector
        row = []
        for key in FEATURE_KEYS:
            val = sensors.get(key, 0.0)
            if val is None:
                val = 0.0
            row.append(float(val))
        X = np.array([row], dtype=np.float32)
        
        # Get prediction: -1 is anomaly, 1 is normal
        prediction = ML_MODEL.predict(X)[0]
        
        # Get decision function score (distance from separation hyperplane)
        # Higher = more normal, Lower = more anomalous
        # Typical range: roughly [-0.5, 0.5] but can vary
        df_score = ML_MODEL.decision_function(X)[0]
        
        # Map decision function to [0, 1] anomaly scale
        # df_score > 0.2 => normal (0.0)
        # df_score < -0.2 => anomaly (1.0)
        # Linear mapping between
        anomaly_score = max(0.0, min(1.0, 0.5 - df_score * 2.5))
        
        label = "anomaly" if prediction == -1 else "normal"
        return round(anomaly_score, 2), label
    except Exception as e:
        print(f"Error computing ML anomaly: {e}")
        import traceback
        traceback.print_exc()
        return 0.0, "error"


def compute_anomaly(sensors: dict) -> tuple[float, dict]:
    # Read sensors with safe defaults and fallbacks
    brake_temp = float(sensors.get("brake_disc_temp_c", sensors.get("brake_temp", 60)))
    vib = float(sensors.get("vibration_rms_g", sensors.get("vibration", 0.25)))
    vibration_spike = float(sensors.get("vibration_spike", 0))
    coolant = float(sensors.get("coolant_temp_c", sensors.get("engine_temp", 90)))
    oil_temp = float(sensors.get("oil_temp_c", sensors.get("oil_temp", sensors.get("oil_temperature", 90))))
    battery = float(sensors.get("battery_voltage_v", sensors.get("battery", 13.8)))
    tire_p = float(sensors.get("tire_pressure_psi", 33))
    hard_brakes = float(sensors.get("hard_brake_events", 0))
    dtc_count = int(sensors.get("dtc_count", 0))
    brake_pressure = float(sensors.get("brake_pressure_bar", sensors.get("brake_pressure", 0)))
    engine_rpm = float(sensors.get("engine_rpm", 0))

    # Brakes: combine disc temp, brake pressure spikes, and hard-brake events
    brake_temp_comp = max(0.0, (brake_temp - 100.0) / 80.0)
    pressure_comp = max(0.0, (brake_pressure - 60.0) / 60.0)
    hard_brake_comp = min(1.0, hard_brakes * 0.5)
    brake_comp = max(brake_temp_comp, pressure_comp, hard_brake_comp)

    # Suspension: vibration RMS and spikes
    vib_comp = max(0.0, (vib - 0.25) / 0.65)
    spike_comp = min(1.0, vibration_spike * 0.7)
    vib_comp = max(vib_comp, spike_comp)

    # Engine: coolant, oil temp, and high RPM under load
    coolant_comp = max(0.0, (coolant - 95.0) / 25.0)
    oil_comp = max(0.0, (oil_temp - 95.0) / 35.0)
    rpm_comp = max(0.0, (engine_rpm - 3000.0) / 4000.0)
    engine_comp = max(coolant_comp, oil_comp, rpm_comp)

    # Electrical: battery under-voltage
    batt_comp = 0.0
    if battery < 13.3:
        batt_comp = min(1.0, (13.3 - battery) / 1.5)

    # Tires: low <28 or high >40 psi
    tire_comp = 0.0
    if tire_p < 28:
        tire_comp = min(1.0, (28.0 - tire_p) / 8.0)
    elif tire_p > 40:
        tire_comp = min(1.0, (tire_p - 40.0) / 8.0)

    # Events / diagnostics: DTCs and hard braking and vibration spikes
    event_comp = min(1.0, hard_brakes * 0.25 + dtc_count * 0.30 + vibration_spike * 0.2)

    # Weighted sum across subsystems
    w_brakes = 0.30
    w_susp = 0.20
    w_engine = 0.20
    w_elec = 0.10
    w_tire = 0.10
    w_event = 0.10

    score = (
        w_brakes * brake_comp
        + w_susp * vib_comp
        + w_engine * engine_comp
        + w_elec * batt_comp
        + w_tire * tire_comp
        + w_event * event_comp
    )
    score = float(max(0.0, min(1.0, round(score, 2))))

    subsystems = {
        "brakes": round(brake_comp, 2),
        "suspension": round(vib_comp, 2),
        "engine": round(engine_comp, 2),
        "electrical": round(batt_comp, 2),
        "tires": round(tire_comp, 2),
        "events": round(event_comp, 2),
    }
    return score, subsystems


@app.post("/analyze")
def analyze(telemetry: RawTelemetry):
    # Rule-based anomaly score and subsystems breakdown
    rule_score, subsystems = compute_anomaly(telemetry.sensors)
    
    # ML-based anomaly score
    ml_score, ml_label = compute_ml_anomaly(telemetry.sensors)
    
    # Combine scores: weighted average (70% rule-based, 30% ML)
    combined_score = round(0.7 * rule_score + 0.3 * ml_score, 2)
    combined_score = float(max(0.0, min(1.0, combined_score)))

    # Preserve whatever sensors were sent so downstream can inspect exact inputs
    sensor_snapshot = dict(telemetry.sensors or {})

    health_payload = {
        "vehicle_id": telemetry.vehicle_id,
        "anomaly_score": combined_score,
        "subsystems": subsystems,
        "sensor_snapshot": sensor_snapshot,
        # Include ML details for debugging/monitoring
        "ml_anomaly_score": ml_score,
        "ml_label": ml_label,
        "rule_anomaly_score": rule_score,
    }

    # forward to Master Agent
    resp = requests.post(MASTER_URL, json=health_payload, timeout=2)
    return {
        "anomaly_score": combined_score,
        "subsystems": subsystems,
        "ml_anomaly_score": ml_score,
        "ml_label": ml_label,
        "master_status": resp.status_code,
    }