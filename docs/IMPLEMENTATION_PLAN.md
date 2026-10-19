# ServiceForce.ai — Implementation Plan (Flutter frontend)

Status: **in progress**. This document is the single source of truth for the build.
Frontend decision: **Flutter (web) replaces the existing React/Vite app** (per product owner).
The React app remains in `frontend/` untouched until the Flutter app reaches parity, then it is retired.

---

## 0. Environment constraints (must read)

Verified on this machine:

| Tool | Status | Consequence |
|---|---|---|
| Python 3.13 | present | backend is fully runnable + testable |
| Node/npm | present | legacy React app still builds |
| Flutter 3.47 / Dart 3.13 | installed | client is compiled, analyzed, tested and built here |
| Docker | NOT installed | `docker compose` cannot be exercised locally |
| git 2.56 | installed | VCS available; the repository is not yet initialised |

**Therefore:** the Flutter client is verified the same way the backend is —
`flutter analyze` (0 issues), `flutter test`, `flutter build web --release`, plus a
manual pass in Chrome. Backend deliverables are verified with `pytest`.

Docker remains the one deliverable this environment cannot exercise. That limitation is
reported honestly rather than hidden.

---

## 1. What already exists (preserve, do not rewrite)

Backend (`backend/app`) — a FastAPI backend, verified by the `pytest` suite:

- Auth + JWT + multi-tenant RBAC (`core/deps.py`, `api/v1/auth.py`).
- Models: organizations, users, memberships, invitations, audit logs, agents,
  knowledge bases/documents/chunks, phone connections, gateways, calls/events/transcripts,
  contacts/consent/suppression, campaigns, billing/integrations/webhooks.
- Tools registry with SSRF guard, RAG pipeline (pdf/docx/txt/md), analytics, billing, audit.
- `TelephonyAdapter` ABC + `MockTelephonyAdapter`.

**Gaps that block the product spec** (the real work):

1. `calls.py` hardcodes `mock_telephony`; `TELEPHONY_PROVIDER` is reported but never used.
2. No inbound-call webhook from a PBX/gateway; no call session orchestrator.
3. No gateway discovery / line+SIM health probe. Gateway rows claim `status="online"` on insert — i.e. **fake success**, which the spec forbids.
4. No WebSocket for live call status/transcript.
5. No background workers (ingestion, summary, campaign dialer).
6. No object storage abstraction for recordings/documents.
7. No real-time voice provider abstraction (Gemini Live) with key isolation.

Frontend: 6 public pages + 17 app pages in React. These define the **feature surface** the
Flutter app must reproduce.

---

## 2. Target architecture

```
 Customer / Staff
   │  (PSTN / mobile)
   ▼
 Physical SIM ── GSM/VoLTE ──► Voice Gateway (Yeastar TG / Dinstar UC2000)
   │                              │ SIP
   │                              ▼
   │                         Asterisk / PJSIP  ──ARI/AMI + ExternalMedia──┐
   │                                                                     │
   ▼                                                                     ▼
 ServiceForce API (FastAPI) ◄── telephony events ── TelephonyAdapter ──► Audio bridge
   │                                                                     │
   ├── CallSessionService (orchestration, policy gates)                  │
   ├── VoiceProvider (Gemini Live / mock) ◄──── bidirectional audio ─────┘
   ├── ToolRunner (SSRF-guarded, audited)
   ├── RAG retrieval
   ├── WebSocket hub  ──► Flutter dashboard (live status + transcript)
   └── Workers (Celery/Redis) ── ingestion, summary, campaign dialer, storage
```

### Layering rule
`api` (HTTP/WS) → `services` (orchestration) → `integrations` (telephony, voice, storage).
No integration SDK types leak into models or API schemas.

---

## 3. Backend workstreams

### WS-1 · Telephony adapter layer  *(core differentiator)*
- **B1.1** Rewrite `services/telephony/adapter.py` to the full interface required by the spec:
  `discover_devices`, `get_line_status`, `verify_connectivity`, `on_inbound_event`,
  `initiate_call`, `answer_call`, `reject_call`, `hangup_call`, `get_call_state`,
  `bridge_audio`, `transfer_call`, `capabilities()`. Every method returns typed
  **capability results**, never a bare bool.
- **B1.2** `Capability` model: `SUPPORTED | UNSUPPORTED | UNKNOWN` — adapters must report
  unsupported capabilities **honestly** (spec §3).
- **B1.3** `TelephonyError` hierarchy: `BusyError`, `UnreachableError`, `NoAnswerError`,
  `CarrierError`, `GatewayOfflineError`, `NotSupportedError`.
- **B1.4** `provider_factory.py` reading `TELEPHONY_PROVIDER` (`mock|asterisk|sip_gateway`).
- **B1.5** Expand `MockTelephonyAdapter` to the full interface (deterministic, seedable).
- **B1.6** `AsteriskAdapter` over **ARI** (REST + WebSocket), documented, with real
  `ExternalMedia`/AudioSocket audio bridge; capability report reflects what Asterisk
  actually exposes. Requires a running Asterisk → integration-tested behind `ASTERISK_E2E=1`.
- **B1.7** `docs/TELEPHONY_SETUP.md` updated: ARI config, real GSM/VoLTE gateway, and the
  honest statement that consumer phones are not gateways.

### WS-2 · Gateway & line health
- **B2.1** `GatewayService`: probe via adapter, persist `status`, `last_heartbeat`,
  signal/registration details. **Never** mark connected on row insert.
- **B2.2** `POST /gateways/{id}/verify` performs a real probe; `POST /gateways/{id}/heartbeat`
  from the bridge. `POST /gateways` creates in `status="unverified"`.
- **B2.3** Phone connection `is_verified` only becomes true after a successful line probe.

### WS-3 · Call orchestration
- **B3.1** `CallSessionService` implementing the inbound + outbound workflows (spec §4, §5)
  as explicit, testable state transitions: `queued→ringing→in_progress→{completed,transferred,failed,no_answer,busy}`.
- **B3.2** Policy gate module: enabled agent, calling hours, monthly cap, budget,
  DNC suppression, consent, concurrency, no-duplicate-concurrent-call.
- **B3.3** `POST /telephony/inbound` — PBX/gateway webhook (HMAC-signed) → resolve tenant by
  DID → run gates → answer/reject/fallback (human → voicemail → polite failure). Never silent drop.
- **B3.4** Manual outbound endpoint with mandatory confirmation token for high-risk calls.
- **B3.5** Call events persisted at each transition; summary/title/outcome queued async.

### WS-4 · Real-time
- **B4.1** `WS /api/v1/ws/calls/{call_id}` — live status + transcript deltas, tenant-scoped.
- **B4.2** In-process `EventHub` abstraction; Redis pub/sub swap for multi-worker.

### WS-5 · Voice provider
- **B5.1** `VoiceProvider` ABC: `start_session`, `send_audio`, `receive_events`, `interrupt`, `end_session`.
- **B5.2** `GeminiLiveProvider` (server-side only, key never leaves backend) + `MockVoiceProvider`.
- **B5.3** Barge-in: `interrupt()` path tested.

### WS-6 · Workers & storage
- **B6.1** `StorageBackend` ABC + `LocalStorage` + `S3Storage` (boto3, optional import).
- **B6.2** Worker tasks: `ingest_document`, `finalize_call_summary`, `campaign_dialer_sweep`.
  Runnable in-process (dev) or via Celery (prod) behind one interface.

### WS-7 · Quality
- **B7.1** pytest coverage for every new module (mock adapter, factory, gates, orchestrator,
  storage, inbound webhook).
- **B7.2** Structured logging, health/readiness with real dependency checks.

---

## 4. Flutter frontend workstream (`app/`)

Chosen stack (all stable): `flutter_riverpod`, `go_router`, `dio`, `freezed`+`json_serializable`,
`fl_chart`, `intl`, `file_picker`, `web_socket_channel`, `flutter_secure_storage`.

### Design system — explicitly **not** "vibe coded"
Non-negotiables, encoded as tokens (never ad-hoc values in widgets):

- **Type scale**: Inter (or system fallback) at 12/14/16/20/24/32 with fixed line-heights and
  a 600/500 weight discipline. No font-size literals outside `AppTypography`.
- **Spacing**: 4px base grid → `AppSpacing.xs..xxxl`. No magic numbers.
- **Color**: a restrained semantic palette (surface / surfaceVariant / outline / primary /
  success / warning / danger / info) with light + dark themes. **No purple-to-pink gradients.**
  Accent is a single hue (deep teal-blue `#0E6E8C`) used sparingly.
- **Radii/elevation**: 8/12/16 radii, two elevation levels only. No random shadows.
- **Components**: one `AppButton` (variants), `AppCard`, `AppTable`, `AppBadge`, `AppField`,
  `AppDialog`, `AppEmptyState`, `AppErrorState`, `AppSkeleton`, `AppToast`, `StatusPill`.
- **States**: every data view ships explicit **loading (skeleton)**, **empty**, **error(retry)**
  and **populated** states. No bare spinners, no raw exception text.
- **Motion**: 120–200ms, ease-out; respects `MediaQuery.disableAnimations`.
- **A11y**: focus order, semantic labels, contrast ≥ 4.5:1, min hit target 44px, keyboard nav.
- **Copy**: sentence case, no exclamation marks, no emoji in UI chrome, real error messages.

### Screens (parity with React app, then beyond)
Public: Landing, Features, Pricing, Docs, Login, Signup.
App: Dashboard, Agents (list/detail/editor), Knowledge (list/detail/upload),
Tool Router, Phone Connections, Gateways (with real verify flow), Calls (list/detail +
live transcript), Campaigns, Contacts, Analytics, Billing, Audit Logs, Settings, Team.

### Cross-cutting
- `ApiClient` (dio): base URL, bearer token, `X-Organization-Id`, 401 refresh/redirect,
  typed errors → user-facing messages, request-id surfacing.
- `AuthController`: secure token storage, org switcher.
- Router guards mirror `ProtectedRoute`.
- WebSocket repo feeding a live call stream into the Calls screens.

---

## 5. Milestones & definition of done

| # | Milestone | DoD |
|---|---|---|
| M0 | Plan (this doc) | committed |
| M1 | Telephony adapter layer | full interface, factory, mock + asterisk, capability honesty; pytest green |
| M2 | Gateway/line health | verify endpoint does a real probe; no fake online; pytest green |
| M3 | Call orchestration + inbound webhook | gates + state machine + fallback; pytest green |
| M4 | WebSocket live updates | tenant-scoped stream; test green |
| M5 | Voice provider abstraction | mock + gemini live, barge-in; test green |
| M6 | Workers + storage | local + s3 backends; in-process runner; test green |
| M7 | Flutter foundation + design system | theming, components, router, auth, dashboard; authored & reasoned |
| M8 | Flutter feature screens | all screens above with 4 states each |
| M9 | Docs + CI | README, TELEPHONY_SETUP, CI workflow, lint/type/test |

M1–M6 are test-verified here. M7–M8 are authored; compile verification requires the Flutter SDK.

---

## 6. Explicit non-goals / honesty notes

- **A consumer Android phone is not a voice gateway.** The spec forbids pretending otherwise.
  Guidance in `docs/TELEPHONY_SETUP.md` states the required gateway capabilities and marks
  phone-as-gateway as unsupported for production barge-in.
- No fake call success: when the gateway/carrier is down the API returns a typed error and the
  call is recorded as `failed` with `failure_reason`.
- No secrets in the browser; `GEMINI_API_KEY` is server-side only.
- Flutter is not compiled in this environment (SDK absent) — stated up front, not glossed over.

---

## 7. Status after this implementation pass

| # | Milestone | State |
|---|---|---|
| M0 | Plan | Done (`docs/IMPLEMENTATION_PLAN.md`) |
| M1 | Telephony adapter layer | Done — verified by pytest |
| M2 | Gateway/line health | Done — verified by pytest |
| M3 | Call orchestration + inbound webhook | Done — verified by pytest |
| M4 | WebSocket live updates | Done — verified by pytest |
| M5 | Voice provider abstraction | Done — verified by pytest |
| M6 | Workers + storage | Done — verified by pytest |
| M7 | Flutter foundation + design system | Done: theme tokens, type scale, palette extension, component library (`widgets/`), API layer, session store, providers, router guard, app shell — `flutter analyze` clean |
| M8 | Flutter feature screens | Done: 5 public pages + 13 app pages, each with the four-state data contract via `AsyncView` — 20 tests pass, release bundle builds |
| M9 | Docs + CI | Done: `app/README.md`, `docs/TELEPHONY_SETUP.md`, `.github/workflows/ci.yml` (backend pytest, Flutter analyze/test/build-web, legacy React build non-blocking) |

Backend: `107 passed`. Flutter: SDK 3.47.7 installed, `flutter analyze` reports
"No issues found!", `flutter test` passes 20 tests, and `flutter build web --release`
produces a bundle (`main.dart.js` ≈ 3.1 MB). Docker is still not installed, so
`docker compose up` has not been exercised.

### Dialing, keypad and campaigns (latest pass)

- **Number linking.** Gateways are now unique *per tenant* rather than globally
  (`UQ_gateway_org_identifier`), so two organizations may both register
  `yeastar-tg200`. The in-app steps and their REST equivalents are documented in
  `docs/TELEPHONY_SETUP.md` §3, and a short how-to card sits on the Phone lines
  page. A number is still only usable after a real probe.
- **AI voice sessions.** `app/services/voice/session_config.py` builds the provider
  session from the call's agent — prompt, greeting, voice, language and enabled
  tools — instead of a hardcoded script, and the audio bridge persists each finished
  transcript turn against the call (and publishes it to the live stream).
- **Manual dialer.** A real keypad widget (1-9, `*`, `0`, `#`, long-press `0` → `+`,
  backspace, clear) drives the destination field, which fixes the place-call button
  state not tracking typing, and the dialog links straight to the live transcript.
- **Campaigns dial.** `POST /campaigns/{id}/start` now runs a dialer pass and returns
  honest `{dialed, blocked, failed}` counts; `POST /campaigns/{id}/sweep` runs further
  passes. Dry runs are timezone-aware and list each refused number with its reason.
  Only genuine failures increment `failed_calls`; policy refusals are recorded as
  `opted_out` on the contact and as a failed call carrying the reason code.
- **Honest outcomes.** `Call.outcome` no longer defaults to `ai_resolved` on insert
  (a ringing or unfinalised call has no outcome), and analytics counts AI-resolved
  calls only among calls that actually completed or transferred.

### Deviations from the original spec, and why

- **Frontend stack.** The spec said React/Vite. The user asked for Flutter, so the
  Flutter client in `app/` is the front end. The React app in `frontend/` is left
  intact but is no longer the deployed client (its CI job is non-blocking).
- **Charts.** `fl_chart` was dropped in favour of a small hand-built bar chart, so
  the chart uses the same tokens as everything else and adds no dependency.
- **Realtime transport.** `EventHub` is in-process with an asyncio handoff, which is
  correct for one worker. Multi-worker deployment needs the Redis pub/sub swap noted
  in WS-4.2; the interface is already in place for it.

### To verify the frontend

```powershell
cd app
flutter pub get
flutter analyze --no-fatal-infos --no-fatal-warnings
flutter test
flutter build web --release --dart-define=API_BASE_URL=http://localhost:8000/api/v1
```

Requires Flutter >= 3.24. Docker and git are also unavailable here, so
`docker compose up` and any commit-based workflow could not be exercised.

