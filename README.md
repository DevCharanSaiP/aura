# AURA

AURA is a prototype predictive vehicle-health and maintenance platform. It simulates vehicle telemetry, scores potential issues with rule-based checks and an optional Isolation Forest model, and presents health and maintenance information in a role-based web dashboard.

## What it includes

- **React dashboard** for car owners, service centers, and manufacturing users.
- **Data Analysis Agent** on port `8100` to score incoming telemetry.
- **Master Agent** on port `8000` for authentication, health history, contact decisions, vehicle data, fleet summaries, and bookings.
- **Customer Engagement Agent** on port `8200` to simulate a proactive service call.
- **Scheduling Agent** on port `8300` to suggest appointment slots and exclude confirmed bookings.
- **PostgreSQL 16** for health snapshots and bookings.
- **Telemetry simulator** that sends readings for ten sample vehicles.

The agents communicate with the Master Agent over local HTTP. The database is the only service configured in Docker Compose; the Python agents and frontend run as separate local processes.

## Requirements

- Python 3.10 or 3.11 (the pinned NumPy version does not support newer Python releases)
- Node.js compatible with Vite 7 (Node.js 20.19+ or 22.12+)
- Docker Desktop with Docker Compose

## Getting started

The commands below are for Windows PowerShell and should be run from the repository root unless a step says otherwise.

### 1. Start PostgreSQL

```powershell
docker compose up -d db
```

The Compose configuration exposes PostgreSQL on `localhost:5432` and creates the `aura` database with the local development user `postgres`.

### 2. Install Python dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell prevents activation, use the Python executable at `.venv\Scripts\python.exe` directly in the commands below.

### 3. Create and update the database schema

Run the included setup and migration scripts once against a fresh database:

```powershell
python backend\setup_db.py
python backend\migrate_add_sensor_snapshot.py
python backend\migrate_add_bookings.py
```

The vehicle-details endpoint also queries three model-score columns that are not added by the checked-in scripts. Add them before using that endpoint:

```powershell
docker compose exec db psql -U postgres -d aura -c "ALTER TABLE health_snapshots ADD COLUMN IF NOT EXISTS ml_anomaly_score DOUBLE PRECISION, ADD COLUMN IF NOT EXISTS ml_label VARCHAR(20), ADD COLUMN IF NOT EXISTS rule_anomaly_score DOUBLE PRECISION;"
```

The sensor-snapshot migration is not idempotent; do not run it a second time on the same database. The database connection settings in the Python scripts currently target the local Compose database.

### 4. Start the backend agents

Open a separate PowerShell terminal for each agent. Run each command from the repository root:

```powershell
cd backend\master-agent
$env:PYTHONPATH = ".."
python -m uvicorn main:app --reload --port 8000
```

```powershell
cd backend\data-agent
python -m uvicorn main:app --reload --port 8100
```

```powershell
cd backend\customer-agent
python -m uvicorn main:app --reload --port 8200
```

```powershell
cd backend\scheduling-agent
python -m uvicorn main:app --reload --port 8300
```

Each agent exposes a root health endpoint at `/`. The Master Agent's interactive API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 5. Start the frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (by default, [http://localhost:5173](http://localhost:5173)). The frontend is configured to call the agents at `127.0.0.1` on the ports listed above.

### 6. Send simulated telemetry

Once PostgreSQL and all four agents are running, start the simulator from the repository root:

```powershell
python data\simulate_vehicles.py
```

The simulator continuously sends telemetry for vehicles `V001` through `V010`. Leave it running to populate health snapshots and update the dashboard. Stop it with `Ctrl+C`.

The Data Analysis Agent loads `backend\models\isoforest.pkl` when present. If no model is available, rule-based scoring still runs. To train or refresh the model, first collect sensor snapshots with the simulator, then run:

```powershell
python backend\ml_training.py
```

## Demo accounts

Select the matching role on the login screen:

| Role | Username | Password | Access |
|---|---|---|---|
| Car owner | `owner_v001` | `pass123` | Vehicle `V001` |
| Car owner | `owner_v002` | `pass123` | Vehicle `V002` |
| Car owner | `owner_v003` | `pass123` | Vehicle `V003` |
| Hero service center | `hero_sc` | `hero123` | Hero service bookings |
| M&M service center | `mm_sc` | `mm123` | M&M service bookings |
| Manufacturing | `manufacturing` | `mfg123` | Aggregated fleet summary |

Health and service information will be limited until the simulator has sent data. The owner view includes vehicle health, recent history, contact decisions, simulated calls, and appointment suggestions. Service-center users see upcoming bookings for their brand; manufacturing users see an aggregate fleet summary.

## API overview

| Agent | Port | Main endpoints |
|---|---:|---|
| Master | `8000` | `POST /auth/login`, `POST /auth/validate`, `GET /health/{vehicle_id}`, `GET /history/{vehicle_id}`, `GET /contact_decision/{vehicle_id}`, `POST /bookings/confirm`, `GET /bookings/upcoming`, `GET /mfg/summary` |
| Data Analysis | `8100` | `POST /analyze` |
| Customer Engagement | `8200` | `POST /simulate_call` |
| Scheduling | `8300` | `POST /propose_slots` |

Most dashboard-facing Master Agent endpoints require a bearer token. See the Master Agent's `/docs` page for request and response schemas.

## Tests and checks

The repository does not currently define a centralized test runner. `test_booking_lifecycle.py` and `test_call.py` are standalone scripts that exercise local services; they are not pytest-discovered tests. The booking lifecycle script expects a running backend and valid owner authorization, so it may require adjustment before it can be used as an automated check.

The frontend provides these npm scripts:

```powershell
npm run lint
npm run build
```

Run them from the `frontend` directory.

## Project layout

```text
backend/
  customer-agent/       Simulated proactive customer contact
  data-agent/           Telemetry scoring and forwarding
  master-agent/         Authentication, health, fleet, and booking APIs
  scheduling-agent/     Appointment-slot suggestions
  models/               Trained Isolation Forest model
  setup_db.py           Initial health snapshot table
  migrate_*.py          Database migrations
data/
  simulate_vehicles.py  Sample telemetry generator
frontend/
  src/                  React application
docker-compose.yml      Local PostgreSQL service
```

## Prototype limitations

This project is intended for local demos and development, not production use. It uses hard-coded local service URLs and database settings, demo credentials, and a development JWT secret. Change these settings and introduce appropriate secret management, password hashing, access controls, and deployment configuration before exposing any service outside a trusted local environment.
