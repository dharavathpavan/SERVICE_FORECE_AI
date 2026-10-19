# AGENTS.md — ServiceForce.ai

## What this repo is

Multi-tenant SaaS for AI voice agents on physical-SIM telephony. **Flutter web** frontend (mobile scaffolding added) + **FastAPI** backend. Legacy React app in `frontend/` is untouched (not deployed).

- Backend: `backend/` — FastAPI, SQLAlchemy, SQLite/Postgres, pytest
- Flutter app: `app/` — Riverpod, go_router, dio, Material 3 design system
- Docs: `docs/` (IMPLEMENTATION_PLAN.md, TELEPHONY_SETUP.md, ARCHITECTURE.md, SECURITY.md)

## Commands

### Backend (run from `backend/`)
```powershell
$env:PYTHONPATH="."
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000   # dev server
..\.venv\Scripts\python.exe -m pytest -q                                           # 119 tests
..\.venv\Scripts\python.exe -m app.db.reset --yes                                  # wipe DB
..\.venv\Scripts\python.exe -m app.db.seed                                          # optional demo data
```
- Auth login expects **JSON** `{"email","password"}`, not form encoding.
- DB is `backend/serviceforce.db`. After DDL changes, delete the file + restart (tables created by `Base.metadata.create_all` at import).
- In-memory test DB: `DATABASE_URL=sqlite:///:memory:` (set in CI).

### Flutter (run from `app/`)
```powershell
$env:Path = "C:\src\flutter\bin;C:\tools\PortableGit\cmd;" + $env:Path
flutter pub get
flutter analyze                      # must be clean
flutter test                        # 20 tests
flutter build web --release          # -> build/web, ~3.1 MB
flutter build apk --debug           # requires Android SDK + JDK 17 (see below)
```

### Environment quirks (Windows)
- **WMI is wedged** on this machine; `platform.machine()` hangs. A `sitecustomize.py` in `.venv/Lib/site-packages/` sets `platform._wmi = None` so SQLAlchemy imports. Don't delete it; reboot restores normal WMI.
- Android SDK at `C:\Android\sdk`, JDK 17 at `C:\Java\jdk-17.0.13+11`. Set `JAVA_HOME` and `ANDROID_HOME` in the shell before building APKs.
- `file_picker` compileSdk mismatch: `android/build.gradle.kts` has a `subprojects { afterEvaluate { ... compileSdkVersion(36) } }` override. Don't remove it.
- `app/android/app/build.gradle.kts` has `compileSdk = 36` (not `flutter.compileSdkVersion`).

## Architecture

- **Backend entrypoint**: `backend/app/main.py` — creates tables, mounts routers at `/api/v1`, conditionally serves `STATIC_DIR` (default `/app/static`) for the Flutter build.
- **Voice provider**: `VOICE_PROVIDER=mock` (default). Mock provider synthesizes real PCM16 audio (Windows SAPI or numpy tones) and the audio bridge stores it as `agent_audio_key` on the Call. Served via `GET /api/v1/calls/{id}/agent-audio`.
- **Telephony**: `TELEPHONY_PROVIDER=mock`. Mock adapter's healthy line number is exactly `+1-800-555-0100` with `connection_type=mock`. Any other number stays `unverified`/`degraded` — this is correct honest behavior.
- **CORS**: `BACKEND_CORS_ORIGIN_REGEX = ^http://(localhost|127\.0\.0\.1)(:\d+)?$`. Production: set `BACKEND_CORS_ORIGINS` to JSON list + regex for `*.onrender.com`.
- **Agent config**: `build_voice_config(db, call)` in `backend/app/services/voice/session_config.py` is the single mapper from stored agent → `VoiceSessionConfig`. Don't bypass it.

## Key conventions

- `Call.outcome` is **NULL until a call concludes** — never default to `ai_resolved`. `finalize()` does not invent an outcome.
- Analytics counts AI-resolved only among `completed`/`transferred`.
- Gateway identifiers are unique **per organization** (not global).
- `recording_url` = carrier recording (null with mock). `agent_audio_key` = locally synthesized AI audio (agent side only). Never conflate them.
- Campaign policy refusals are recorded as `opted_out` + a failed call carrying the reason; only genuine failures increment `failed_calls`.
- `AuthState.copyWith` cannot clear the session (passing `session: null` keeps the old value) — known limitation.

## Flutter conventions

- Design system tokens in `app/lib/src/theme/tokens.dart` (`AppType`, `AppSpacing`, `AppRadii`, `AppPalette`). Accent: teal-blue `#0E6E8C`/`#4FB3CE`. No gradients.
- `AsyncView<T>` widget for loading/empty/error states.
- Riverpod family providers: `FutureProviderFamily<T, Arg>`.
- Web-only code guarded by conditional imports: `export 'x_stub.dart' if (dart.library.js_interop) 'x_web.dart'`.
- `kApiBaseUrl` defaults to `http://localhost:8000/api/v1`. Override via `--dart-define=API_BASE_URL=...`.
- Audio player: `app/lib/src/platform/audio_player.dart` facade → stub (VM) or web (HTMLAudioElement via data: URL).

## Gotchas

- `.env` is gitignored but contains a real-looking `GEMINI_API_KEY`; not rotated (no commits existed until recently).
- `frontend/` (legacy React) is retained but not deployed; has its own "Instant Demo Sign In".
- `backend/storage/` holds recordings/docs — gitignored, ephemeral on Render free tier.
- The stray external prober hits bare `/health` (404) on port 8000 — unrelated to app code (app uses `/api/v1/health/ready`).
- `flutter_secure_storage` pulls in `flutter_secure_storage_web` (web-only) — fine, transitive dep.
- `build/` is gitignored at root level; `app/build/` too. The Render deploy bundles `backend/static/` (Flutter build output) into the Docker image.

## Deployment

- **Render**: `render.yaml` blueprint. Backend + Flutter static (bundled) + Postgres. Live at https://service-forece-ai.onrender.com
- **GitHub**: https://github.com/dharavathpavan/SERVICE_FORCE_AI (branch: `main`)
- Render MCP configured with API key `rnd_…` in `~/.config/opencode/opencode.json`.

## Testing

- Backend: `pytest -q` (119 tests). CI uses `DATABASE_URL=sqlite:///:memory:` and `DEMO_MODE=true`.
- Flutter: `flutter test` (20 tests), `flutter analyze` (must be clean).
- Live E2E: register → inbound call → WS `/api/v1/voice/stream?call_id=...&token=...` → assert transcripts + agent audio stored.