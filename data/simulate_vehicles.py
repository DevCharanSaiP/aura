import time
import random
import requests

DATA_AGENT_URL = "http://127.0.0.1:8100/analyze"  # new agent we'll create

VEHICLES = [
    "V001", "V002", "V003", "V004", "V005",
    "V006", "V007", "V008", "V009", "V010",
]

def generate_telemetry(vehicle_id: str) -> dict:
    # Simple sensor model
    base_brake = 40
    base_temp = 90
    drift = 0

    if vehicle_id == "V001":
        drift = 10  # 'bad' vehicle

    return {
        "vehicle_id": vehicle_id,
        "sensors": {
            "brake_temp": base_brake + drift + random.gauss(0, 3),
            "engine_temp": base_temp + random.gauss(0, 2),
            "vibration": random.uniform(0.1, 0.8),
        }
    }

def main():
    print("Starting telemetry simulation...")
    while True:
        for vid in VEHICLES:
            payload = generate_telemetry(vid)
            try:
                resp = requests.post(DATA_AGENT_URL, json=payload, timeout=2)
                print("TX →", vid, "status", resp.status_code)
            except Exception as e:
                print("Error sending for", vid, ":", e)
        time.sleep(2)

if __name__ == "__main__":
    main()