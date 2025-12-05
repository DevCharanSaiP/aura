import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="aura",
    user="postgres",
    password="postgres",
)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS health_snapshots (
    id SERIAL PRIMARY KEY,
    vehicle_id VARCHAR(20) NOT NULL,
    anomaly_score DOUBLE PRECISION NOT NULL,
    subsystems JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
""")

conn.commit()
cur.close()
conn.close()

print("health_snapshots table ready.")