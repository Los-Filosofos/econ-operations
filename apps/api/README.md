# ECON Python Hub

Dash (dash-mantine-components, local Tabler icons, Plotly, AG Grid Community) on FastAPI, with SQLModel + Alembic and PostgreSQL for the integration store. The hub endpoint remains a read projection; the separate operations service persists plans, source snapshots, a dispatch outbox and evidence. An explicit CLI worker performs bounded synchronization. All business data for this project is synthetic sandbox data; file samples and current provider reads remain separate evidence.

The homepage (`/`) features an interactive, full-page operations graph with a warm charcoal palette, local SVG silhouettes, a 68/32 desktop canvas-to-detail split, keyboard-focused nodes, and verified relationship evidence. Dedicated pages include requests (with candidate units for a pending request without unit), machinery, operations workflow (paginated registry), integration trace (`/integracion`), indicator sheets (`/indicadores`), decisions (`/decisiones`), sources and admin user management (`/administracion`). There is no refresh button: the page polls `GET /api/v1/status` every 15 s and reloads data only when `registry_version` changes.

From the repository root:

```sh
[ -f apps/api/.env ] || cp apps/api/.env.example apps/api/.env
python -c "import secrets; print(secrets.token_urlsafe(32))"   # paste as SESSION_SECRET in apps/api/.env
docker compose up -d --wait db
uv sync --project apps/api --locked
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api python -m app.cli.create_user --email admin@example.com --role admin --name "Administración"
./scripts/dev.sh   # PowerShell: .\scripts\dev.ps1
```

Do not overwrite an existing `.env`; retain its database settings. Configuration loads `apps/api/.env` regardless of the working directory. `SESSION_SECRET` is mandatory: the application refuses to start without it unless `AUTH_REQUIRED=false` (development only). `create_user` prompts for the password (or reads it with `--password-stdin`); passwords are never command-line arguments. Open `http://localhost:8050` for Dash (sign in at `/login`) and `http://localhost:8050/docs` for the typed OpenAPI contract. Both use one server and the shared `app/services/hub.py` read service. UI code and local assets live in `app/dashboard`; the URL carries the origin, search and display filter. Snapshots are scoped to each browser in memory. See [the dashboard architecture](../../docs/frontend-architecture.md).

```sh
./scripts/check.sh   # ruff check, ruff format --check, pytest, generar_diccionario.py --check, exportar_matrices.py --check; --container builds the image
```

Tests set `AUTH_REQUIRED=false` through `conftest.py` (the auth tests enable it explicitly), use `httpx2` for Starlette 1.6's TestClient and fail on any `DeprecationWarning`. The health tests use temporary SQLite files; normal development uses the existing PostgreSQL Docker service. With `ECON_TEST_POSTGRES_URL` and `ECON_TEST_POSTGRES_MIGRATIONS_URL` set (CI starts `postgres:16`), `tests/test_postgres_*.py` also run: in-flight exclusivity, `SKIP LOCKED`, the append-only trigger, the cycle lock and the `0004_guards` migration round trip. Schema migrations still run explicitly, never on server startup. `DATABASE_URL` accepts `postgres://`, `postgresql://` and `postgresql+psycopg://`: the first two select the installed psycopg driver without changing credentials, hostname, database or SSL options. Other explicit driver schemes are preserved. CI without a local `.env` must supply `DATABASE_URL` before importing the application.

## Session and roles

`app/core/auth.py` owns roles, permissions and the session identity ([ADR 0005](../../docs/adr/0005-session-auth-and-roles.md)). Sessions are a signed `econ_session` cookie (Starlette `SessionMiddleware`; HttpOnly, `SameSite=lax`, `Secure` with `SESSION_HTTPS_ONLY=true`, `SESSION_MAX_AGE_SECONDS` default 28800). Passwords are argon2 hashes through `pwdlib`. The role is read from SQL on every request, so deactivating a user or changing a password ends their sessions immediately.

| Role | `read` | `manage_transfers` | `declare_reception` | `manage_users` |
| --- | --- | --- | --- | --- |
| `admin` | yes | yes | yes | yes |
| `logistica` | yes | yes | yes | |
| `gerencia_proyecto` | yes | | yes | |
| `mantenimiento`, `control_costos`, `lectura` | yes | | | |

- `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`.
- `GET/POST /api/v1/users`, `PATCH /api/v1/users/{id}` (admin only).
- Without a session: 401 on `/api/*` and Dash callbacks, redirect to `/login?next=` for pages. Without the permission: 403. Ten failed logins per IP in fifteen minutes: 429. Deactivating the last active admin or your own account: 409.
- Pages `/login` and `/administracion` (admin only).

Live reads are visible to every role once the server enables them; management actions (plans, queue, sync, receipt) require the permission above. With `AUTH_REQUIRED=false` (development only) there is no login and management falls back to `ALLOW_LOCAL_MANAGEMENT` from a loopback, same-origin request. The retired `CORS_ORIGINS` setting is gone: UI and API share one origin.

## Read contract

See the Spanish [Swagger walkthrough](../../docs/api-swagger.md) for every
endpoint, parameters, response semantics and an isolated SQLite exercise.
Swagger at `/docs` includes operation descriptions, request examples and errors;
`/openapi.json` is generated from the implementation.

`GET /api/v1/hub?mode=fixture&search=CF-03` returns the typed contract in `app/models/hub.py`. `mode` accepts only `fixture` or `live`; `fixture` is the default and now means supplied OpenAPI examples. The `search` filter is case-insensitive and applies locally to the bounded read set: equipment ID/code/asset number/name/company/project and request ID/project. Requests joined by exact machinery ID are retained with matching equipment; matching requests can also bring their equipment into the result. No joins use driver or project names.

- `equipment` preserves administrative state, maintenance, multiple tasks (`transfers`), location timestamps and relationship status as separate facts. `code` maps to nullable Nexus `clave`; `asset_number` maps separately to `no_activo`. Display fallbacks do not replace the source ID or claim those fields are equivalent.
- `provenance` identifies source, original ID, environment and synthetic-data status. `evidence_kind` distinguishes `provided_sample`, `live_read` and internal `test_case`; `source_reference` points to the document example. Unknown source IDs or observation instants remain nullable. `observed_on` preserves a documented day without inventing an exact time.
- `generated_at` is response assembly time. `data_as_of` is the live read completion time or null for supplied examples without a common observation instant. Source creation/update/approval timestamps are retained separately. A location has its own event time; reading it again does not make its position current.
- `scope.equipment_total` and `requests_total` are the original totals before the local search. Summary counters describe only returned records. `scope.complete` requires the integrated dataset; it remains false for live reads while Startrack is missing. Nexus has its own `connected`/`partial` status for pagination coverage.
- Unknown or inaccessible sources yield empty records and null summary counters, with explicit source status and a safe message. No exception, cookie, credential, upstream body or raw internal response is returned. `alerts_count=0` is emitted only for evaluated records without matching rules; it is not a verified absence of global operational problems.

All hub responses carry `Cache-Control: no-store`. Readiness is separate: `/health/live` checks the process, and `/health/ready` checks the database. Neither certifies upstream connectivity.

## Provided samples and rule limits

`app/integrations/data/sandbox_samples.json` contains five equipment and two request examples from the supplied `econ-hackathon-openapi.json`, with document hash, original IDs and source values. The sample date is 2026-09-12; no common observation instant is documented. Equipment coverage is five of a reported fifteen, so integrated coverage remains partial. The two requests belong to PROY-014; the assigned RE-03/MOT-006/PROY-006 operation is absent from these examples and remains documented separately. CF-03 preserves `OBSOLETA`; no maintenance failure, Startrack task, GPS location or receipt is invented. Fabricated business-rule inputs exist only in isolated tests, never in the application's runtime dataset.

Initial alerts evaluate active failure ID, an explicit stop flag plus a confirmed pending task, pending requests whose planned date has arrived, and approved requests without equipment. Date-dependent alerts require a known observation cutoff and are not evaluated against the current clock for old contract examples. Missing stop flags remain unknown. `PENDIENTE`/`PENDING` and `APROBADA`/`APPROVED` are recognized status spellings; unknown values remain visible. Date-only plans stay dates in El Salvador; ambiguous timestamps without a timezone are not classified as overdue.

Administrative availability is not physical availability. Task completion, GPS/geofence signals and project receipt remain different events. No delivery punctuality, percentage, utilization, cost, trend or ISO compliance result is invented.

## Nexus live reads

Live mode is disabled until the server operator explicitly sets `ALLOW_LIVE_READS=true` and configures `NEXUS_EMAIL` and `NEXUS_PASSWORD`. Leave live reads disabled on a public fixture deployment. The browser never receives upstream credentials. Every signed-in role can read live data once the server enables it; no role can enable it.

The connector contacts only `https://econ-key.maic.ai`. It authenticates through the observed `/api/auth/login` endpoint and keeps the cookie in a process-local HTTP client. The hub reads equipment and requests; the workflow can read exact request/equipment details. It performs no business writes. Both connectors share `app/integrations/http.py` (`BoundedClient`): one fixed origin, no redirects, environment proxies ignored, serialized reads under a time budget and a 1 MB cap per response.

The new connector was verified against the assigned account on **2026-09-12 at 19:05 UTC** with one page of one record per collection: equipment returned 1 of a reported 15, and requests returned 1 of a reported 2. It correctly marked that bounded read incomplete. The first strict validation identified a wrong assumption that `clave` was always a string; the real nullable value is now preserved separately from `no_activo`. This small check validates those sampled fields and access, not every record or a supported long-term provider contract. It did not enable live mode permanently or obtain Startrack API access.

Each read uses a configured maximum page count, page size, per-request timeout and overall budget; each response is capped at 1 MB. Default limits are 2 pages × 25 records for each collection, a 5-second network timeout and a 20-second read budget. Reaching a limit or observing unstable totals/duplicate pages produces partial coverage; malformed data produces an explicit source error. Search happens after bounded reads and cannot certify an absent record outside that window. If either collection fails, the aggregate reports Nexus unavailable rather than publishing an apparently complete snapshot.

A `401` allows one serialized reauthentication and one repeat of that safe GET. A `403`, `429`, failed login or other error is reported without retry loops. Sessions coordinate within one process. A failed hub read does not serve a previous success; historical operation evidence remains separately timestamped in the ledger. Startrack credentials and the actual authenticated response contract still need validation for this account.

## Startrack SDK and local transfer preparation

`app/integrations/startrack.py` implements bounded reads for tasks, geofences, users, vehicles, task statuses/types and visits. Drafts validate explicit dates and unique ID lists with Pydantic types (`ExplicitDate`, `UniqueIds`); the ledger validates observation payloads with `ObservationData`. Task creation has an independent server-side write gate and no POST retry. It uses a fixed sandbox origin, server-owned Basic credentials, explicit pagination/size/time limits and sanitized errors. An exhausted page is not a complete integrated snapshot. Authenticated provider validation, including array encoding in task creation, is still pending.

`app/services/transfers.py` prepares a local task draft from an approved request, its exact machinery record and an explicit mapping of source IDs, destination geofence, assigned Startrack users, movement reference and scheduled date. Missing facts or conflicting IDs prevent draft generation. Supplied examples remain identified as samples. Draft payloads disable contact notifications and never infer delivery, receipt, current availability or unique remote IDs.

To inspect the supplied approved request without any network calls:

```sh
uv run --directory apps/api python -m app.cli.prepare_transfer --request-source-id 46d2573e-08d3-4855-971d-2fbf9564e135
```

An optional `--mapping` local JSON file supplies the explicit mapping for a reviewable draft. This does not create records in Prisma or Startrack. Prisma's supplied contract does not expose project/request creation or approval webhooks; Startrack's documented webhooks forward vehicle telemetry. See [current context](../../docs/contexto-vigente.md).

## Persistent workflow

`services/workflow.py` is shared by Dash actions, `/api/v1/operations` and
`python -m app.cli.sync_operations`. `services/ledger.py` owns short transactions,
source snapshots and a durable dispatch claim. Timestamps go through the
`UTCDateTime` type in `models/operations.py`, so SQLite and PostgreSQL store
and return aware UTC instants. Apply `alembic upgrade head` explicitly
(`0001_operations`, `0002_review_schedule`, `0003_users`, `0004_guards`: session
actor on events and receipts, `tracked_vehicle_kind`, partial unique indexes for
one in-flight movement per machine and one `job_id` per environment, and the
PostgreSQL-only append-only trigger on `operation_events`); startup never
creates or drops tables.

- `GET /api/v1/status?mode=fixture`: deterministic `registry_version`, last stored registry read, `hub_data_as_of` and the automatic synchronization state; polled by the page, never a provider call.
- `GET /api/v1/graph`, `GET /api/v1/indicators`, `GET /api/v1/requests/{id}/suggestions`: typed read projections over the same bounded hub read plus one registry page (see the [Swagger walkthrough](../../docs/api-swagger.md)).
- `GET /api/v1/operations?mode=fixture`: movements and execution history (`page`, `page_size` up to 500).
- `GET /api/v1/operations/catalogs`: bounded sandbox mapping catalogs.
- `POST /api/v1/operations/plans`: save a plan with explicit mapping and provenance.
- `POST /api/v1/operations/{id}/queue`: refresh and validate before queueing a live plan.
- `POST /api/v1/operations/sync`: one bounded synchronization and dispatch cycle.
- `POST /api/v1/operations/{id}/receipt`: record a receiver, zoned instant and evidence reference.
- `POST /api/v1/operations/{id}/resolve`: close a live `unknown` movement as `failed` with a closed reason code and the session actor; never repeats the POST.

Management requires a session whose role holds `manage_transfers` (receipt:
`declare_reception`); `WorkflowService` checks the permission per action. Only
with `AUTH_REQUIRED=false` does `ALLOW_LOCAL_MANAGEMENT=true` plus a loopback,
same-origin request grant it. Browser flags cannot enable it. Remote creation additionally
requires `ALLOW_LIVE_READS`, `ALLOW_LIVE_WRITES` and both provider credentials.
All flags default to false. `AUTO_QUEUE_TRANSFERS` applies only to explicitly
saved, currently approved and validated plans; it does not invent mappings.

Run one cycle with `python -m app.cli.sync_operations --mode live`; add `--watch`
for a 120-second interval. `SYNC_INTERVAL_SECONDS` (0 = off, otherwise 30–3600)
runs the same bounded live cycle inside the web process under the PostgreSQL
cycle lock (`SyncScheduler`), only with `ALLOW_LIVE_READS=true` and never for
fixture; its last outcome (`ok`, `skipped`, `error: …`) is published by
`GET /api/v1/status`. Run a single worker: provider report limits are shared
per IP while the local limiter is per process. Outcomes with uncertain creation
are reconciled by exact reference and payload fields without another POST.
GPS presence and task completion never generate receipt. See the Spanish
[operating runbook](../../docs/solucion-integracion.md) and
[ADR 0004](../../docs/adr/0004-persistent-transfer-workflow.md).

## Runtime

Build the conventional Python container with `docker build -t econ-hub apps/api`. Pass environment variables at runtime; `.env` is excluded from the image. The server binds `0.0.0.0` on `PORT`, defaulting to 8000. Keep PostgreSQL outside its filesystem. Dash and API routes run together on Uvicorn; no Node build or separate frontend deployment is needed. See [deployment](../../docs/despliegue-backend.md) and [ADR 0003](../../docs/adr/0003-python-dash-hub.md). This Dockerfile does not make the current SQLModel/psycopg application a drop-in Python Worker.
