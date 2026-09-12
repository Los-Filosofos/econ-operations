# ECON API

FastAPI + SQLModel + Alembic, with PostgreSQL retained for the integration store. The first hub endpoint is a read projection; it does not persist snapshots or pretend to provide background synchronization. No application login is implemented.

From the repository root:

```powershell
if (-not (Test-Path apps/api/.env)) {
    Copy-Item apps/api/.env.example apps/api/.env
}
docker compose up -d --wait db
npm run setup:api
npm run dev:api
```

Do not overwrite an existing `.env`; retain its database settings. Configuration loads `apps/api/.env` regardless of the working directory. Start the frontend separately with the root web script. Open `http://localhost:8000/docs` for the typed OpenAPI contract.

```powershell
uv run --directory apps/api ruff check .
uv run --directory apps/api ruff format --check .
uv run --directory apps/api pytest
uv run --directory apps/api alembic upgrade head
```

The health tests use temporary SQLite files; normal development uses the existing PostgreSQL Docker service. Schema migrations still run explicitly, never on server startup. `DATABASE_URL` accepts `postgres://`, `postgresql://` and `postgresql+psycopg://`: the first two select the installed psycopg driver without changing credentials, hostname, database or SSL options. Other explicit driver schemes are preserved. CI without a local `.env` must supply `DATABASE_URL` before importing the application.

## Read contract

`GET /api/v1/hub?mode=fixture&search=RE-03` returns the typed contract in `app/models/hub.py`. `mode` accepts only `fixture` or `live`; `fixture` is the default. The `search` filter is case-insensitive and applies locally to the bounded read set: equipment ID/code/asset number/name/company/project and request ID/project. Requests joined by exact machinery ID are retained with matching equipment; matching requests can also bring their equipment into the result. No joins use driver or project names.

- `equipment` preserves administrative state, maintenance, multiple tasks (`transfers`), location timestamps and relationship status as separate facts. `code` maps to nullable Nexus `clave`; `asset_number` maps separately to `no_activo`. Display fallbacks do not replace the source ID or claim those fields are equivalent.
- `provenance` identifies the source, original ID, environment, read time and synthetic-data status. The assigned environments contain synthetic data even when the API connection is live.
- `generated_at` is response assembly time. `data_as_of` is the read completion time or the fixed local fixture reference time. A location has its own event time; reading it again does not make its position current.
- `scope.equipment_total` and `requests_total` are the original totals before the local search. Summary counters describe only returned records. `scope.complete` requires the integrated dataset; it remains false for live reads while Startrack is missing. Nexus has its own `connected`/`partial` status for pagination coverage.
- Unknown or inaccessible sources yield empty records and null summary counters, with explicit source status and a safe message. No exception, cookie, credential, upstream body or raw internal response is returned. `alerts_count=0` is emitted only for evaluated records without matching rules; it is not a verified absence of global operational problems.

All hub responses carry `Cache-Control: no-store`. Readiness is separate: `/health/live` checks the process, and `/health/ready` checks the database. Neither certifies upstream connectivity.

## Local scenarios and rule limits

Fixtures are invented local records with the `fixture:` namespace and a fixed reference time, **not copied or current platform data**. They cover RE-03 with an unknown transfer link, occupied equipment alongside a completed task, a stopped machine with a pending linked transfer, and an approved request without equipment. The fixture relationship labeled `confirmed` is confirmed only within that invented example.

Initial alerts evaluate active failure ID, an explicit stop flag plus a confirmed pending task, pending requests whose planned date has arrived, and approved requests without equipment. Missing stop flags remain unknown. `PENDIENTE`/`PENDING` and `APROBADA`/`APPROVED` are the initial recognized status spellings; unknown values remain visible and are not inferred. Confirm source catalogs with the provider before treating these rules as production KPIs. Date-only plans stay dates in El Salvador; ambiguous timestamps without a timezone are not classified as overdue.

Administrative availability is not physical availability. Task completion, GPS/geofence signals and project receipt remain different events. No delivery punctuality, percentage, utilization, cost, trend or ISO compliance result is invented.

## Nexus live reads

Live mode is disabled until the server operator explicitly sets `ALLOW_LIVE_READS=true` and configures `NEXUS_EMAIL` and `NEXUS_PASSWORD`. Because the application has no login, enabling live mode makes its allowed upstream data readable by anyone who can reach this API. Leave live reads disabled on a public fixture deployment. The browser receives no upstream credentials; `VITE_*` variables must never contain them.

The connector contacts only `https://econ-key.maic.ai`. It authenticates through the observed `/api/auth/login` endpoint, keeps the cookie in a process-local HTTP client, and reads only `/api/maquinaria/equipos` and `/api/maquinaria/requests`. It performs no business writes. Redirects and environment proxies are disabled.

The new connector was verified against the assigned account on **2026-09-12 at 19:05 UTC** with one page of one record per collection: equipment returned 1 of a reported 15, and requests returned 1 of a reported 2. It correctly marked that bounded read incomplete. The first strict validation identified a wrong assumption that `clave` was always a string; the real nullable value is now preserved separately from `no_activo`. This small check validates those sampled fields and access, not every record or a supported long-term provider contract. It did not enable live mode permanently or obtain Startrack API access.

Each read uses a configured maximum page count, page size, per-request timeout and overall budget; each response is capped at 1 MB. Default limits are 2 pages × 25 records for each collection, a 5-second network timeout and a 20-second read budget. Reaching a limit or observing unstable totals/duplicate pages produces partial coverage; malformed data produces an explicit source error. Search happens after bounded reads and cannot certify an absent record outside that window. If either collection fails, the aggregate reports Nexus unavailable rather than publishing an apparently complete snapshot.

A `401` allows one serialized reauthentication and one repeat of that safe GET. A `403`, `429`, failed login or other error is reported without retry loops. Sessions coordinate within one process; distributed synchronization, persistence, refresh-token support, recurring polling and live Startrack reads are not implemented. A failed read does not serve a previous success. Startrack is explicitly `not_configured` until its API key and actual response contract are validated.

## Runtime

Build the conventional Python container with `docker build -t econ-api apps/api`. Pass environment variables at runtime; `.env` is excluded from the image. The server binds `0.0.0.0` on `PORT`, defaulting to 8000. Keep PostgreSQL outside its filesystem. See the repository architecture/deployment documentation for the Cloudflare frontend and API hosting boundary. This Dockerfile does not make the current SQLModel/psycopg application a drop-in Python Worker.
