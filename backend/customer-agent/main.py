from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

MASTER_URL = "http://127.0.0.1:8000/contact_decision"

app = FastAPI(title="AURA Customer Engagement Agent - Stub v0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ContactRequest(BaseModel):
    vehicle_id: str
    owner_name: str | None = None
    phone: str | None = None


@app.get("/")
def root():
    return {"status": "ok", "service": "customer-agent", "version": "0.0.1"}


@app.post("/simulate_call")
def simulate_call(req: ContactRequest):
    # Ask Master whether we should contact
    resp = requests.get(f"{MASTER_URL}/{req.vehicle_id}", timeout=2)
    decision = resp.json()

    if not decision.get("should_contact"):
        return {
            "vehicle_id": req.vehicle_id,
            "action": "no_call",
            "message": "Risk low, no proactive call needed.",
            "decision": decision,
        }

    # Simple script generation based on severity
    severity = decision.get("severity")
    if severity == "critical":
        script = (
            f"Hi {req.owner_name or 'there'}, this is AURA from Hero Service. "
            "We have detected a critical issue in your vehicle that could lead "
            "to a breakdown very soon. We recommend scheduling a service "
            "appointment at the earliest possible slot."
        )
    else:
        script = (
            f"Hi {req.owner_name or 'there'}, this is AURA from Hero Service. "
            "We noticed early warning signs in your vehicle and recommend a "
            "convenient preventive check-up in the next few days."
        )

    return {
        "vehicle_id": req.vehicle_id,
        "action": "suggest_call",
        "phone": req.phone,
        "decision": decision,
        "script": script,
    }