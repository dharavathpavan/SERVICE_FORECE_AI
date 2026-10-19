# ServiceForce.ai

> **Your business number. Your AI workforce.**  
> A production-oriented, multi-tenant AI voice-agent SaaS platform where businesses configure conversational AI agents that make and receive phone calls using authorized business telephony, retrieve real-time business data, answer questions from a vector knowledge base (pgvector RAG), execute verified actions, and escalate seamlessly to human staff.

---

## 1. Quick Start (Local Development)

### Prerequisites
- Python 3.12+ (Python 3.13 tested)
- Flutter 3.24+ (3.47 tested) with the web toolchain — `flutter doctor` should show Chrome available
- Node.js 20+ & npm (only for the legacy React client in `frontend/`)

### Backend Setup
```bash
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Change to backend directory
cd backend

# 3. Start the FastAPI backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Backend API will be live at: `http://localhost:8000`  
Interactive OpenAPI documentation: `http://localhost:8000/api/v1/docs`

The database starts **empty** — see **Test Data** below to add or remove data.

### Frontend Setup (Flutter web)
In a new terminal, from the repository root:
```bash
# 1. Change to the Flutter app directory
cd app

# 2. Fetch packages
flutter pub get

# 3. Run against the local backend (Chrome)
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000/api/v1

# ...or produce a release bundle and serve it statically
flutter build web --release
```

### Test Data

The repository ships **no pre-populated data**. A fresh database contains zero
organizations, users, agents, gateways, calls or campaigns, so every screen shows
its real empty state and the whole flow — sign up, configure, place a call — is
exercisable from scratch.

Create the first account at `/signup`; it becomes the workspace Owner. Then add an
AI agent, a telephony gateway and a phone connection from the app.

Helpers for repeatable testing:

| Command | Effect |
| --- | --- |
| `python -m app.db.reset --dry-run` | Report what would be deleted |
| `python -m app.db.reset --yes` | Delete all business data (schema kept) |
| `python -m app.db.reset --yes --drop` | Drop and recreate the schema |
| `python -m app.db.seed` | **Optional** demo workspace with one login per role, password `ServiceForce!2026` |

`reset` clears every table except Alembic's `alembic_version`, and also removes
local recordings/uploads (use `--keep-storage` to keep them). When the optional demo
data is seeded, the accounts are `demo.owner@`, `demo.admin@`, `demo.manager@` and
`demo.agent@` at `serviceforce.ai`; re-running the seeder only adds what is missing.

---

## 2. Core Capabilities

- **Production Multi-Tenancy & RBAC:** Complete organization isolation with Owner, Admin, Manager, and Operator permissions.
- **AI Voice Agent Studio & Playground:** Real-time text and speech turn simulation with configurable personalities (Puck, Charon, Aoede, Fenrir), greetings, and versioning.
- **pgvector Reference Knowledge Base (RAG):** Ingestion pipeline for PDF, DOCX, TXT, and Markdown files with recursive chunking and cosine similarity search.
- **Safe Live Data Tool Router:** Pre-built tools for `lookup_customer`, `get_order_status`, `check_inventory`, `create_appointment`, `request_human_transfer`, and `end_call` with SSRF protection against private RFC1918 and AWS metadata IPs.
- **Telephony Adapter Interface & Mock Simulation:** Full-duplex speech interruption / barge-in simulation, Asterisk PBX SIP bridge architecture, and BYO SIM gateway documentation. Numbers are linked through Gateways → Phone lines → Verify (see `docs/TELEPHONY_SETUP.md` §3), and an unverified line is refused rather than dialled.
- **Live AI Voice Sessions:** the agent's own system prompt, greeting, voice, language and enabled tools drive the voice session, and every finished transcript turn is stored against the call as it happens.
- **Manual Dialer:** a telephone keypad (long-press `0` for `+`) with line and agent selection, a confirmation step, and a jump straight to the live transcript.
- **Outbound Calling Campaigns:** Calling window constraints (09:00 - 20:00), Do-Not-Call (DNC) suppression enforcement, concurrency caps, and dry-run preview verification. Starting a campaign places real calls; each pass reports `dialled / refused / failed`, and a refused number is recorded with its reason.
- **Analytics & Audit Logs:** Real aggregated metrics for answer rates, AI resolution percentage, duration, and tamper-evident audit trail.

---

## 3. Running Automated Tests

### Backend Unit & Integration Tests
```bash
cd backend
$env:PYTHONPATH = "."
..\.venv\Scripts\pytest -q tests/
```
*119 tests covering Auth, RBAC, Cross-Tenant Isolation, Demo Logins, CORS,
Test-Data Reset, Call Lifecycle, Campaign Dialing & Consent, Voice Session
Config, Mock Voice Audio (synthesis format, provider payloads, bridge-to-storage
capture, tenant-scoped streaming), RAG, SSRF Guard, Telephony Adapters, Realtime
Streaming, Voice/Storage/Workers.*

### Flutter Web Client Checks
```bash
cd app
flutter analyze          # must report "No issues found!"
flutter test             # 20 tests (error mapping, model parsing, dial keypad)
flutter build web --release
```

---

## 4. Docker Compose Environment

For running the full stack with PostgreSQL + pgvector and Redis:
```bash
docker compose up --build
```
Services started:
- `backend`: FastAPI API server (`:8000`)
- `frontend`: Nginx serving the production SPA (`:5173`)
- `postgres`: PostgreSQL 16 with pgvector extension (`:5432`)
- `redis`: Redis 7 alpine queue cache (`:6379`)

> The container image for `frontend` still builds the original React/Vite client,
> which is kept in `frontend/` for reference. The supported client is the Flutter
> web app in `app/`; point any static host at `app/build/web` after
> `flutter build web --release`.

---

## 5. Telephony Hardware Prerequisites for Live Calls

When moving beyond demo/simulation mode to live business telephone numbers:
1. **Certified Hardware Gateway:** Yeastar TG Series or Dinstar UC2000-VE VoLTE GSM Gateway for BYO SIM, or direct cloud SIP trunk.
2. **Asterisk PBX Media Bridge:** Configured with AudioSocket or WebSocket audio stream (see `docs/TELEPHONY_SETUP.md`).
3. **Acceptance Test:** Complete the 5-point acceptance checklist in `docs/TELEPHONY_SETUP.md` (Two-way audio, Barge-in, Live tool query, Warm transfer, and Clean hangup).
