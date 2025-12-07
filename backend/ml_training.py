import json
import os

import joblib
import numpy as np
import psycopg2
from sklearn.ensemble import IsolationForest


DB_CONFIG = dict(
    host="localhost",
    port=5432,
    dbname="aura",
    user="postgres",
    password="postgres",
)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_PATH = os.path.join(MODEL_DIR, "isoforest.pkl")


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






def fetch_sensor_snapshots_safely(limit: int = 5000):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    # Assuming your table has a JSONB column called sensor_snapshot
    cur.execute(
        """
        SELECT sensor_snapshot
        FROM health_snapshots
        WHERE sensor_snapshot IS NOT NULL
        ORDER BY id DESC
        LIMIT %s
        """,
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in rows]


def build_feature_matrix(snapshots):
    X = []
    for snap in snapshots:
        # psycopg2 may return dict or JSON string depending on how you stored it
        if isinstance(snap, str):
            snap = json.loads(snap)
        row = []
        for key in FEATURE_KEYS:
            val = snap.get(key)
            if val is None:
                val = 0.0
            row.append(float(val))
        X.append(row)
    return np.array(X, dtype=np.float32)


def train_isolation_forest(X: np.ndarray):
    # treat all fetched data as "mostly normal"
    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,  # assume ~5% anomalies
        random_state=42,
    )
    model.fit(X)
    return model


def main():
    print("Fetching sensor snapshots...")
    snapshots = fetch_sensor_snapshots_safely(limit=5000)
    if not snapshots:
        print("No sensor_snapshot data found in DB. Run the simulator first.")
        return

    print(f"Fetched {len(snapshots)} snapshots.")
    X = build_feature_matrix(snapshots)
    print("Feature matrix shape:", X.shape)

    print("Training Isolation Forest...")
    model = train_isolation_forest(X)

    print(f"Saving model to {MODEL_PATH} ...")
    joblib.dump(model, MODEL_PATH)
    print("Done.")


if __name__ == "__main__":
    main()