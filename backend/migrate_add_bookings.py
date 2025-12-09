"""
Migration script to create bookings table for AURA appointment lifecycle.
Tracks: suggested → confirmed → completed appointments.
"""

import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="aura",
    user="postgres",
    password="postgres",
)

cur = conn.cursor()

try:
    # Create bookings table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            vehicle_id VARCHAR(50) NOT NULL,
            slot_start TIMESTAMP NOT NULL,
            slot_end TIMESTAMP NOT NULL,
            center_id VARCHAR(100),
            status VARCHAR(50) DEFAULT 'suggested',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confirmed_at TIMESTAMP DEFAULT NULL,
            completed_at TIMESTAMP DEFAULT NULL
        );
    """)
    print("✓ Created bookings table")
    
    # Create index on vehicle_id and status for faster queries
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_bookings_vehicle_status 
        ON bookings(vehicle_id, status);
    """)
    print("✓ Created index on vehicle_id and status")
    
    # Create index on slot_start for time-based queries
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_bookings_slot_start 
        ON bookings(slot_start);
    """)
    print("✓ Created index on slot_start")
    
    conn.commit()
    print("\n✅ Migration completed successfully!")
    
except Exception as e:
    print(f"❌ Migration failed: {e}")
    conn.rollback()

finally:
    cur.close()
    conn.close()
