# Community demo mode: report

## What changed

- `backend/app/config.py`: new setting `COMMUNITY_DEMO_MODE` (default `false`).
- `backend/app/database.py` / `main.py`: with demo mode on, startup seeds the ten Bengaluru sensors via `seed_community_sensors` (bcrypt rounds 4, because demo tokens are never used; no tokens file written). Without the lower rounds, the 10 hashes added about 3.4 s to each cold start.
- `backend/app/community_demo.py`: `ensure_demo_readings(session)`, a no-op when demo mode is off. For each active sensor it:
  - gives sensors without coordinates a random Bengaluru point (`random_bengaluru_location`, same box and 0.005 deg separation as the local simulator), stored on the sensor and on each reading;
  - writes one reading per minute aligned to the minute: 120 rows (2 h) on first touch, then the elapsed slots since the latest reading, max 60 per call;
  - generates values with a mean-reverting random walk seeded by sensor id and slot (PM2.5 15-120, PM10 1.3-2.0x PM2.5, 20-32 C, 35-85 %);
  - continues sequence numbers after the sensor's max, sets `recorded_at = received_at` in UTC, sets `last_seen` to the newest row and `quality_status='simulated'`;
  - runs in one transaction, rolls back on a unique-constraint race, skips when another thread holds the lock, and is throttled to once per 3 s per database unless a sensor is still unlocated (so a newly registered sensor appears on the very next read).
  The interval is 1 minute, not 2, so `last_seen` always stays inside the frontend's 2-minute "Online" window.
- `routers/community_sensors.py`: the four community GETs the frontend uses (`/sensors`, `/sensors/{id}`, `/sensors/{id}/readings`, `/map`) call the helper first. Registration and `POST /sensors/readings` are unchanged. I mirrored the ingestion logic rather than factoring it out, so the real path is untouched.
- Timezones: `CommunitySensorOut` / `CommunitySensorReadingOut` now mark naive datetimes as UTC (validators), and `/map` does the same for its `last_seen` / `recorded_at`. The API now returns `...Z` / `+00:00`. This applies in both modes and fixes the "Offline, last seen 5 hours ago" display for browsers in India.
- Docs: README section "Community sensors in the deployed demo"; deploy command in PROJECT_DOCUMENTATION.md 6.4.
- docker-compose.yml is unchanged (demo mode stays off locally).

## Verification

- `cd backend && .venv/bin/pytest tests/ -q`: **38 passed** (34 existing + 4 new in `tests/test_community_demo.py`: startup seed with tz-aware recent `last_seen`; a new sensor gets Bengaluru coords, 50 readings and appears on `/map` on the next GET; backfill adds only elapsed slots; demo off leaves a new sensor without coords or readings and with a tz-aware `created_at`).
- `cd frontend && npm run build`: passed.
- Live server: real uvicorn on port 8002, `COMMUNITY_DEMO_MODE=true`, fresh `/tmp/demo.db`. The run was in-process because the agent shell refuses background servers; it was stopped afterwards, and ports 3000/8000 were not touched.
  - Startup log: `Created 10 community sensors.`
  - `POST /sensors/register` → 201 `SENSOR_011`.
  - `GET /sensors` → 11 sensors, all with coordinates, a latest reading (`quality_status=simulated`), and `last_seen=2026-11-13T05:31:00Z` (16 s old, so the frontend shows Online). SENSOR_011 got 12.9145, 77.5183.
  - `GET /sensors/SENSOR_011/readings?limit=50` → 50 rows, 04:42Z to 05:31Z.
  - `GET /map` → 11 sensors including SENSOR_011, `last_seen` with `+00:00`.
  - Real `POST /sensors/readings` with the issued token → 201 "Reading accepted."
  - The seed points SENSOR_006 (Electronic City, 12.8458) and SENSOR_010 (Yelahanka, 13.1007) fall just outside the 12.85-13.10 random-pick box. They are the existing fixed seed coordinates and are still in Bengaluru.

## Deploy change needed (not run)

Rebuild and deploy the new image with the extra env var, e.g.:

```bash
gcloud builds submit backend --tag us-central1-docker.pkg.dev/<PROJECT>/<REPO>/community-air-api
gcloud run deploy community-air-api \
  --image us-central1-docker.pkg.dev/<PROJECT>/<REPO>/community-air-api \
  --region us-central1 --allow-unauthenticated \
  --min-instances 0 --max-instances 1 --cpu 1 --memory 512Mi \
  --update-env-vars COMMUNITY_DEMO_MODE=true \
  --set-secrets OPENAQ_API_KEY=openaq-api-key:latest,SCHEDULER_TOKEN=scheduler-token:latest
```

`--update-env-vars` keeps the existing `CORS_ORIGINS`. The documented fresh-deploy form is `--set-env-vars CORS_ORIGINS=https://<vercel-domain>,COMMUNITY_DEMO_MODE=true`. Data, including registered sensors, resets whenever the container restarts.
