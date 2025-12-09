from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import datetime as dt
import requests
import psycopg2

MASTER_URL = "http://127.0.0.1:8000/contact_decision"
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "aura"
DB_USER = "postgres"
DB_PASS = "postgres"

app = FastAPI(title="AURA Scheduling Agent - Stub v0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScheduleRequest(BaseModel):
    vehicle_id: str
    owner_name: str | None = None
    preferred_days: int = 7  # within next N days
    center_id: str | None = "CENTER_MUMBAI_01"


def get_booked_slots(vehicle_id: str):
    """
    Fetch confirmed bookings for a vehicle from the database.
    Returns list of (slot_start, slot_end) tuples.
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
        )
        cur = conn.cursor()
        cur.execute(
            """
            SELECT slot_start, slot_end
            FROM bookings
            WHERE vehicle_id = %s AND status = 'confirmed'
            """,
            (vehicle_id,),
        )
        booked = cur.fetchall()
        cur.close()
        conn.close()
        return booked
    except Exception as e:
        print(f"Error fetching booked slots: {e}")
        return []


def slot_is_available(slot_start_iso: str, slot_end_iso: str, booked_slots):
    """
    Check if a proposed slot conflicts with any confirmed booking.
    Returns True if available, False if overlaps with a booking.
    """
    from datetime import datetime
    
    try:
        slot_start = datetime.fromisoformat(slot_start_iso)
        slot_end = datetime.fromisoformat(slot_end_iso)
        
        for booked_start, booked_end in booked_slots:
            # Check for overlap: if slot overlaps with any booked slot, it's unavailable
            if slot_start < booked_end and slot_end > booked_start:
                return False
        return True
    except Exception as e:
        print(f"Error checking slot availability: {e}")
        return True  # default to available if error


@app.get("/")
def root():
    return {"status": "ok", "service": "scheduling-agent", "version": "0.0.2"}


def generate_slots(days: int, severity: str):
    """Very simple rule-based slot generator."""
    today = dt.date.today()
    slots = []
    # for demo: 3 slots per recommended day
    base_hours = [10, 14, 17]

    # critical: first 2 days; warning: 3–5 days; ok: no slots
    if severity == "critical":
        day_range = range(0, min(days, 2))
    elif severity == "warning":
        day_range = range(1, min(days, 5))
    else:
        return []

    for offset in day_range:
        d = today + dt.timedelta(days=offset)
        for h in base_hours:
            start = dt.datetime(d.year, d.month, d.day, h, 0)
            end = start + dt.timedelta(hours=1)
            slots.append(
                {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "label": f"{d.strftime('%a %d %b')} {h:02d}:00–{h+1:02d}:00",
                }
            )
    return slots[:6]  # at most 6 options for UI
    


@app.post("/propose_slots")
def propose_slots(req: ScheduleRequest):
    # ask Master how urgent this is
    decision_resp = requests.get(f"{MASTER_URL}/{req.vehicle_id}", timeout=2)
    decision = decision_resp.json()
    severity = decision.get("severity", "ok")

    slots = generate_slots(req.preferred_days, severity)

    if not slots:
        return {
            "vehicle_id": req.vehicle_id,
            "center_id": req.center_id,
            "severity": severity,
            "can_schedule": False,
            "reason": "risk_low_or_no_slots",
            "decision": decision,
        }

    # Filter out already-booked slots
    booked_slots = get_booked_slots(req.vehicle_id)
    available_slots = [
        slot for slot in slots
        if slot_is_available(slot["start"], slot["end"], booked_slots)
    ]

    if not available_slots:
        return {
            "vehicle_id": req.vehicle_id,
            "center_id": req.center_id,
            "severity": severity,
            "can_schedule": False,
            "reason": "all_suggested_slots_already_booked",
            "decision": decision,
            "total_suggested": len(slots),
            "available": len(available_slots),
        }

    return {
        "vehicle_id": req.vehicle_id,
        "center_id": req.center_id,
        "severity": severity,
        "can_schedule": True,
        "decision": decision,
        "options": available_slots,
        "total_suggested": len(slots),
        "available": len(available_slots),
    }