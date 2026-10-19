# ServiceForce.ai — Flutter web client

The front end for ServiceForce.ai. It replaces the original React/Vite app (still
present in `../frontend`, no longer built or deployed) with a Flutter web client
that shares the backend at `../backend`.

> **Build status: not yet compiled in this environment.** The Flutter/Dart SDK is
> not installed here, so `flutter pub get`, `flutter analyze`, `flutter test` and
> `flutter build web` have not been run. Everything below is written to be correct
> by inspection; run the commands in *Local development* to verify. See
> *Verification status* at the end.

## What this app covers

| Area | Screens |
| --- | --- |
| Public | Landing, Features, Pricing, Sign in, Sign up |
| Workspace | Dashboard, Calls, Call detail (live), Agents, Agent detail + tester |
| Knowledge | Knowledge bases, document upload and ingestion status |
| Telephony | Phone lines (verify each line), Gateways (register + probe + line detail) |
| Outreach | Campaigns (dry-run/start/pause), Contacts + suppression |
| Insights | Analytics, Audit log |
| Administration | Team (roles, invites), Settings (theme, provider, readiness) |

## Design system

Deliberate, token-driven and *not* template-looking. The rules are enforced by the
shared widgets rather than repeated per screen.

- **One accent hue.** `#0E6E8C` (deep teal-blue) in light, `#4FB3CE` in dark. No
  gradients anywhere. Colour is used for meaning, not decoration.
- **Strict 4px spacing grid.** `AppSpacing` only — widgets never contain bare
  numbers for padding or gaps.
- **Three radii, two elevations.** `AppRadii.sm|md|lg`. Cards are flat with a
  1px outline; there is no drop-shadow soup and no layered glow.
- **Defined type scale.** `AppType` (`display → micro`, plus `mono` for phone
  numbers, IDs and timings). Widgets must not set `fontSize` directly.
- **Semantic palette as a `ThemeExtension`.** Every colour has a role
  (`surfaceSunken`, `outlineStrong`, `dangerSurface`, `focusRing`, …), so light
  and dark are one switch, not two designs.
- **Four states for every data view.** Loading uses `AppSkeleton` (never a bare
  spinner), then empty (`AppEmptyState`, always with a next step), error
  (`AppErrorState`, always with retry) and data. `AsyncView` is the single place
  that guarantees this, so no screen can forget one.
- **Honesty is a UI rule.** Gateway and line state only render as connected when
  the server says a probe succeeded. Provider capability matrices state what the
  hardware *cannot* do. Failed and skipped calls show the recorded reason.
- **Accessibility.** Visible `focusRing` on focus, `Semantics` on icon-only
  controls and headers, tooltips with the same text as the accessible label,
  tabular figures for numeric columns, and reduced-motion support in skeletons.

## Layout

```
lib/
  main.dart                  app entry; restores the session once
  src/
    app.dart                 MaterialApp.router + boot splash
    router/app_router.dart   go_router with an auth redirect guard
    theme/
      tokens.dart            AppSpacing, AppRadii, AppDurations, AppPalette
      app_theme.dart         AppType scale, AppTheme.light/dark
    api/
      api_client.dart        Dio wrapper; the only place that sees DioException
      api_error.dart         sealed ApiError variants with user-safe messages
      models.dart            defensive JSON → view models
      repositories.dart      one class per backend resource
    state/
      session_store.dart     secure-storage session + TokenProvider
      providers.dart         Riverpod providers, AuthController
    services/call_stream.dart  live call WebSocket with backoff + reconnect
    widgets/                 the component library (see below)
    features/                one folder per area, screens only
```

`widgets/`: `primitives.dart` (button, icon button, badge, status mapping),
`surfaces.dart` (card, page/section headers, empty/error/skeleton/table),
`async_view.dart` (the four-state contract), `inputs.dart` (field, select, switch,
stat tile, detail row), `app_shell.dart` (sidebar, top bar, provider chip).

## Local development

```powershell
cd app
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000/api/v1
```

Requires Flutter **>= 3.24** (Dart >= 3.4, for `ThemeExtension`, sealed classes and
pattern `switch` expressions).

Start the backend first:

```powershell
cd ../backend
$env:PYTHONPATH="."
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Sign in with an account created at `/signup` (the first account owns the new
workspace). The database ships empty, so every screen starts in its real empty
state. Login accepts **JSON** (`{"email", "password"}`), not form encoding.

To load the optional demo workspace instead (`python -m app.db.seed`), or to wipe
everything again (`python -m app.db.reset --yes`), see the repository README.

### Production build

```powershell
flutter build web --release --dart-define=API_BASE_URL=https://api.example.com/api/v1
```

The bundle lands in `build/web`. Model keys never reach this bundle: they are read
server-side only.

## Tests

```powershell
flutter test          # unit tests for the API/error/model layer
flutter analyze       # lint + type checks
```

`test/api_error_test.dart` pins error classification (including that a 503 keeps
its body so readiness checks can be shown rather than hidden).
`test/models_test.dart` pins the defensive parsing rules — notably that a gateway
without an explicit status is never treated as verified.

## Verification status

| Item | State |
| --- | --- |
| `flutter pub get` / `analyze` / `test` / `build web` | **Not run** — Flutter SDK absent in the authoring environment |
| Code paths that need the SDK translated/compiled | Everything under `lib/` and `test/` |
| Backend contract | Verified against the running backend's routers (`backend/app/api/v1`) |

Before first deploy, run `flutter analyze`, then `dart format .`, then
`flutter build web`, and fix anything the analyser reports.
