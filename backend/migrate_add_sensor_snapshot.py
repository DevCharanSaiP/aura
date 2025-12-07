import psycopg2

DB_CONFIG = dict(
    host="localhost",
    port=5432,
    dbname="aura",
    user="postgres",
    password="postgres",
)

def migrate():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Add sensor_snapshot column if it doesn't exist
    cur.execute("""
        ALTER TABLE health_snapshots
        ADD COLUMN sensor_snapshot JSONB DEFAULT NULL;
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete: added sensor_snapshot column to health_snapshots")

if __name__ == "__main__":
    try:
        migrate()
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        # If column already exists, that's ok
        if "already exists" in str(e):
            print("Column already exists, skipping.")
        else:
            raise
