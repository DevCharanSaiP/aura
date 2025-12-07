import time
import random
import requests
from typing import Dict

DATA_AGENT_URL = "http://127.0.0.1:8100/analyze"

# Vehicle list with a usage profile
VEHICLES = [
    ("V001", "taxi_city"),
    ("V002", "family_city"),
    ("V003", "family_highway"),
    ("V004", "rural_lowuse"),
    ("V005", "family_city"),
    ("V006", "taxi_city"),
    ("V007", "highway_commuter"),
    ("V008", "rural_lowuse"),
    ("V009", "family_city"),
    ("V010", "highway_commuter"),
]


def base_profile(profile: str) -> Dict:
    # Base parameters for different usage profiles
    if profile == "taxi_city":
        return {
            "speed_mean": 35,
            "speed_std": 15,
            "rpm_mean": 2200,
            "rpm_std": 500,
            "hard_brake_prob": 0.18,
            "vibration_base": 0.35,
        }
    if profile == "highway_commuter":
        return {
            "speed_mean": 90,
            "speed_std": 8,
            "rpm_mean": 2500,
            "rpm_std": 400,
            "hard_brake_prob": 0.03,
            "vibration_base": 0.22,
        }
    if profile == "rural_lowuse":
        return {
            "speed_mean": 40,
            "speed_std": 20,
            "rpm_mean": 1800,
            "rpm_std": 400,
            "hard_brake_prob": 0.07,
            "vibration_base": 0.45,
        }
    # default family_city / mixed
    return {
        "speed_mean": 50,
        "speed_std": 22,
        "rpm_mean": 2000,
        "rpm_std": 450,
        "hard_brake_prob": 0.08,
        "vibration_base": 0.3,
    }


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


# Maintain simple per-vehicle state (odometer)
VEHICLE_STATE: Dict[str, Dict] = {vid: {"odometer_km": random.uniform(1000, 80000)} for vid, _ in VEHICLES}


def generate_telemetry(vehicle_id: str, profile: str, tick: int) -> Dict:
    p = base_profile(profile)

    # Motion
    speed = max(0.0, random.gauss(p["speed_mean"], p["speed_std"]))  # km/h
    rpm = int(max(600, random.gauss(p["rpm_mean"], p["rpm_std"])))
    throttle = round(clamp(random.gauss(30, 25), 0, 100), 1)
    if speed < 5:
        throttle = round(random.uniform(0, 10), 1)

    # Temperatures
    coolant_temp = round(clamp(random.gauss(92, 6), 60, 120), 1)
    # oil_temp slightly above coolant under load
    oil_temp = round(clamp(coolant_temp + random.uniform(2, 15), 60, 130), 1)

    # Electrical
    engine_running = speed > 2 or rpm > 900
    if engine_running:
        battery_v = round(clamp(random.gauss(14.0, 0.25), 12.8, 14.8), 2)
    else:
        battery_v = round(clamp(random.gauss(12.4, 0.3), 11.5, 13.0), 2)

    # Brakes
    hard_brake = random.random() < p["hard_brake_prob"]
    brake_pedal = 1 if hard_brake or random.random() < 0.18 else 0
    # brake pressure proxy (bar)
    brake_pressure = round(clamp(random.gauss(30, 6) + (20 if hard_brake else 0), 0, 120), 1)
    # brake disc temp influenced by speed and hard brakes
    brake_disc_temp = round(clamp(random.gauss(70, 12) + (30 if hard_brake and speed > 30 else 0), 30, 320), 1)

    # Suspension / tires
    vibration_rms = round(clamp(random.gauss(p["vibration_base"], 0.08) + (0.12 if speed > 80 else 0.0), 0.05, 1.2), 3)
    vibration_spike = 1 if random.random() < 0.02 or (profile == "rural_lowuse" and random.random() < 0.06) else 0
    tire_pressure = round(clamp(random.gauss(33, 2), 24, 42), 1)

    # Usage / odometer
    state = VEHICLE_STATE[vehicle_id]
    # distance travelled during tick (tick ~2s)
    distance_km = speed * (2.0 / 3600.0)
    state["odometer_km"] += distance_km
    odometer = round(state["odometer_km"], 1)

    # Events / diagnostics
    hard_brake_events = 1 if hard_brake else 0
    dtc_count = 0 if random.random() > 0.98 else random.randint(1, 3)

    sensors = {
        # Engine & powertrain
        "engine_rpm": rpm,
        "vehicle_speed_kmh": round(speed, 1),
        "throttle_pos_pct": throttle,
        "coolant_temp_c": coolant_temp,
        "oil_temp_c": oil_temp,
        "battery_voltage_v": battery_v,

        # Brakes
        "brake_pedal": brake_pedal,
        "brake_pressure_bar": brake_pressure,
        "brake_disc_temp_c": brake_disc_temp,

        # Suspension & tires
        "vibration_rms_g": vibration_rms,
        "vibration_spike": vibration_spike,
        "tire_pressure_psi": tire_pressure,

        # Usage / state
        "odometer_km": odometer,
        "idling": 1 if speed < 2 else 0,

        # Events / diagnostics
        "hard_brake_events": hard_brake_events,
        "dtc_count": dtc_count,
    }

    return {"vehicle_id": vehicle_id, "sensors": sensors}


def main():
    print("Starting rich telemetry simulation...")
    tick = 0
    while True:
        for vid, profile in VEHICLES:
            payload = generate_telemetry(vid, profile, tick)
            try:
                resp = requests.post(DATA_AGENT_URL, json=payload, timeout=2)
                print(vid, payload["sensors"]["coolant_temp_c"], payload["sensors"]["brake_disc_temp_c"], "→", resp.status_code)
            except Exception as e:
                print("Error sending for", vid, ":", e)
        tick += 1
        time.sleep(2)


if __name__ == "__main__":
    main()