from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import psycopg2
import json
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import jwt
import hashlib

# JWT configuration
JWT_SECRET = "aura_secret_key_change_in_production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

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
    # ML-based anomaly score and decision label
    ml_anomaly_score: float | None = None
    ml_label: str | None = None
    # Rule-based anomaly score (before ML combination)
    rule_anomaly_score: float | None = None


# ========== AUTHENTICATION MODELS ==========

class LoginRequest(BaseModel):
    username: str
    password: str
    role: str  # "user" | "service" | "manufacturing"


class LoginResponse(BaseModel):
    success: bool
    token: str | None = None
    user_id: str | None = None
    role: str | None = None
    message: str = ""


class TokenData(BaseModel):
    user_id: str
    role: str
    vehicle_id: str | None = None  # Only for car owners


# ========== UTILITY FUNCTIONS ==========

def hash_password(password: str) -> str:
    """Simple hash (in production, use bcrypt)."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_jwt_token(user_id: str, role: str, vehicle_id: str | None = None) -> str:
    """Create a JWT token."""
    payload = {
        "user_id": user_id,
        "role": role,
        "vehicle_id": vehicle_id,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> TokenData:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenData(
            user_id=payload.get("user_id"),
            role=payload.get("role"),
            vehicle_id=payload.get("vehicle_id"),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_token_from_request(request: Request) -> TokenData:
    """Extract and verify JWT token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = auth_header.replace("Bearer ", "")
    return verify_jwt_token(token)


# Mock user database (in production, use real DB)
USERS_DB = {
    # Car owners (vehicle-specific)
    "owner_v001": {"password": hash_password("pass123"), "role": "user", "vehicle_id": "V001"},
    "owner_v002": {"password": hash_password("pass123"), "role": "user", "vehicle_id": "V002"},
    "owner_v003": {"password": hash_password("pass123"), "role": "user", "vehicle_id": "V003"},
    # Service center
    "service_center": {"password": hash_password("service123"), "role": "service", "vehicle_id": None},
    # Manufacturing
    "manufacturing": {"password": hash_password("mfg123"), "role": "manufacturing", "vehicle_id": None},
}


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
    return {"status": "ok", "service": "master-agent", "version": "0.0.5"}


# ========== AUTHENTICATION ENDPOINTS ==========

@app.post("/auth/login")
def login(req: LoginRequest):
    """
    Login endpoint for all three roles:
    - user (car owner): requires vehicle_id
    - service: service center staff
    - manufacturing: manufacturing team
    """
    user_record = USERS_DB.get(req.username)
    
    if not user_record:
        return LoginResponse(
            success=False,
            message="Invalid username or password"
        )
    
    # Verify password
    if user_record["password"] != hash_password(req.password):
        return LoginResponse(
            success=False,
            message="Invalid username or password"
        )
    
    # Verify role matches
    if user_record["role"] != req.role:
        return LoginResponse(
            success=False,
            message="Role mismatch"
        )
    
    # Create JWT token
    token = create_jwt_token(
        user_id=req.username,
        role=req.role,
        vehicle_id=user_record.get("vehicle_id"),
    )
    
    return LoginResponse(
        success=True,
        token=token,
        user_id=req.username,
        role=req.role,
        message="Login successful"
    )


@app.post("/auth/validate")
def validate_token(token: str):
    """Validate JWT token and return user info."""
    try:
        token_data = verify_jwt_token(token)
        return {
            "valid": True,
            "user_id": token_data.user_id,
            "role": token_data.role,
            "vehicle_id": token_data.vehicle_id,
        }
    except HTTPException:
        return {
            "valid": False,
            "message": "Token invalid or expired"
        }


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
def get_health(vehicle_id: str, request: Request):
    """Get health data for a vehicle. Only car owners can access their own vehicle."""
    try:
        token_data = get_token_from_request(request)
    except HTTPException:
        raise
    
    # Only car owners (role="user") can access health data
    if token_data.role != "user":
        raise HTTPException(status_code=403, detail="Only car owners can view health data")
    
    # Car owners can only access their own vehicle
    if token_data.vehicle_id and token_data.vehicle_id != vehicle_id:
        raise HTTPException(status_code=403, detail="You can only view your own vehicle's health")
    
    key = f"health:{vehicle_id}"
    data = store.get(key)
    return {"vehicle_id": vehicle_id, "health": data}


@app.get("/history/{vehicle_id}")
def get_history(vehicle_id: str, request: Request, limit: int = 20):
    """
    Return last N (default 20) health snapshots from DB for this vehicle.
    Only accessible to car owners of that vehicle.
    """
    try:
        token_data = get_token_from_request(request)
    except HTTPException:
        raise
    
    # Only car owners (role="user") can access health history
    if token_data.role != "user":
        raise HTTPException(status_code=403, detail="Only car owners can view health history")
    
    # Car owners can only access their own vehicle history
    if token_data.vehicle_id and token_data.vehicle_id != vehicle_id:
        raise HTTPException(status_code=403, detail="You can only view your own vehicle's history")
    
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
def list_vehicles(request: Request):
    """
    Return vehicles based on user role:
    - Car Owner (user): only their own vehicle with full data
    - Service Center (service): all vehicles with anomaly scores only (no sensor data)
    - Manufacturing (manufacturing): fleet summary only
    """
    try:
        token_data = get_token_from_request(request)
    except HTTPException:
        raise
    
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

    # Filter vehicles based on role
    if token_data.role == "user":
        # Car owners only see their own vehicle
        ids = [token_data.vehicle_id] if token_data.vehicle_id else []
    elif token_data.role == "service":
        # Service center sees all vehicles but only anomaly scores (no sensors)
        pass
    elif token_data.role == "manufacturing":
        # Manufacturing sees fleet summary only
        pass

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
def contact_decision(vehicle_id: str, request: Request):
    """Determine if customer should be contacted. Only accessible to car owners."""
    try:
        token_data = get_token_from_request(request)
    except HTTPException:
        raise
    
    # Only car owners (role="user") can access contact decisions
    if token_data.role != "user":
        raise HTTPException(status_code=403, detail="Only car owners can view contact decisions")
    
    # Car owners can only access their own vehicle
    if token_data.vehicle_id and token_data.vehicle_id != vehicle_id:
        raise HTTPException(status_code=403, detail="You can only view your own vehicle's contact decision")
    
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
def mfg_summary(request: Request):
    """
    Manufacturing view: fleet summary only.
    Only accessible to manufacturing role.
    Returns aggregate counts by severity, but NOT individual vehicle details with IDs.
    """
    try:
        token_data = get_token_from_request(request)
    except HTTPException:
        raise
    
    # Only manufacturing team can view fleet summary
    if token_data.role != "manufacturing":
        raise HTTPException(status_code=403, detail="Only manufacturing team can view fleet summary")
    
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

    return {
        "counts": counts,
        "fleet_size": len(rows),
        "message": "Fleet summary - aggregated view only (no vehicle details)"
    }


# ========== BOOKING LIFECYCLE ENDPOINTS ==========

class BookingRequest(BaseModel):
    vehicle_id: str
    slot_start: str  # ISO datetime string
    slot_end: str    # ISO datetime string
    center_id: str | None = None


@app.post("/bookings/confirm")
def confirm_booking(req: BookingRequest, request: Request):
    """
    Confirm a suggested booking slot.
    Only car owners can confirm their own vehicle bookings.
    """
    try:
        token_data = get_token_from_request(request)
    except HTTPException:
        raise
    
    # Only car owners can confirm bookings
    if token_data.role != "user":
        raise HTTPException(status_code=403, detail="Only car owners can confirm bookings")
    
    # Car owners can only confirm their own vehicle bookings
    if token_data.vehicle_id and token_data.vehicle_id != req.vehicle_id:
        raise HTTPException(status_code=403, detail="You can only confirm your own vehicle bookings")
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            INSERT INTO bookings (vehicle_id, slot_start, slot_end, center_id, status, confirmed_at)
            VALUES (%s, %s, %s, %s, 'confirmed', CURRENT_TIMESTAMP)
            RETURNING id, vehicle_id, slot_start, slot_end, center_id, status, confirmed_at
            """,
            (req.vehicle_id, req.slot_start, req.slot_end, req.center_id),
        )
        booking = cur.fetchone()
        conn.commit()
        
        return {
            "success": True,
            "booking_id": booking[0],
            "vehicle_id": booking[1],
            "slot_start": booking[2].isoformat() if booking[2] else None,
            "slot_end": booking[3].isoformat() if booking[3] else None,
            "center_id": booking[4],
            "status": booking[5],
            "confirmed_at": booking[6].isoformat() if booking[6] else None,
        }
    except Exception as e:
        conn.rollback()
        print(f"Error confirming booking: {e}")
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()


@app.get("/bookings/upcoming")
def get_upcoming_bookings(request: Request, limit: int = 10):
    """
    Fetch upcoming confirmed bookings. 
    - Service Center (service): see all upcoming bookings
    - Others: forbidden
    """
    try:
        token_data = get_token_from_request(request)
    except HTTPException:
        raise
    
    # Only service center can view all upcoming bookings
    if token_data.role != "service":
        raise HTTPException(status_code=403, detail="Only service center can view upcoming bookings")
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            SELECT id, vehicle_id, slot_start, slot_end, center_id, status, confirmed_at
            FROM bookings
            WHERE status = 'confirmed' AND slot_start >= CURRENT_TIMESTAMP
            ORDER BY slot_start ASC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        
        bookings = []
        for row in rows:
            bookings.append({
                "booking_id": row[0],
                "vehicle_id": row[1],
                "slot_start": row[2].isoformat() if row[2] else None,
                "slot_end": row[3].isoformat() if row[3] else None,
                "center_id": row[4],
                "status": row[5],
                "confirmed_at": row[6].isoformat() if row[6] else None,
            })
        
        return {"bookings": bookings, "count": len(bookings)}
    except Exception as e:
        print(f"Error fetching upcoming bookings: {e}")
        return {"bookings": [], "count": 0, "error": str(e)}
    finally:
        cur.close()
        conn.close()


@app.get("/bookings/vehicle/{vehicle_id}")
def get_vehicle_bookings(vehicle_id: str, request: Request):
    """
    Fetch all bookings for a specific vehicle.
    - Car Owner (user): only their own vehicle bookings
    """
    try:
        token_data = get_token_from_request(request)
    except HTTPException:
        raise
    
    # Only car owners can view their own vehicle bookings
    if token_data.role != "user":
        raise HTTPException(status_code=403, detail="Only car owners can view booking history")
    
    # Car owners can only access their own vehicle
    if token_data.vehicle_id and token_data.vehicle_id != vehicle_id:
        raise HTTPException(status_code=403, detail="You can only view your own vehicle's bookings")
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            SELECT id, vehicle_id, slot_start, slot_end, center_id, status, confirmed_at
            FROM bookings
            WHERE vehicle_id = %s
            ORDER BY slot_start DESC
            LIMIT 20
            """,
            (vehicle_id,),
        )
        rows = cur.fetchall()
        
        bookings = []
        for row in rows:
            bookings.append({
                "booking_id": row[0],
                "vehicle_id": row[1],
                "slot_start": row[2].isoformat() if row[2] else None,
                "slot_end": row[3].isoformat() if row[3] else None,
                "center_id": row[4],
                "status": row[5],
                "confirmed_at": row[6].isoformat() if row[6] else None,
            })
        
        return {"bookings": bookings}
    except Exception as e:
        print(f"Error fetching vehicle bookings: {e}")
        return {"bookings": [], "error": str(e)}
    finally:
        cur.close()
        conn.close()
