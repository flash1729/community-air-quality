# Implementation Plan: Community Sensor Network

This plan implements a proof-of-concept Community Sensor Network where simulated IoT air quality sensors post data to the FastAPI backend and display live on a Next.js frontend with Leaflet maps.

## Architecture Summary

- **Backend**: FastAPI + SQLite, two new models (CommunitySensor, CommunitySensorReading), Bearer token auth, 6 REST endpoints
- **Simulator**: Python script simulating 10 virtual sensors, gradual measurement changes, HTTP POST every 5-10s
- **Frontend**: Next.js page at /community with Leaflet map, metrics dashboard, live 5s polling, Recharts history

## Implementation Plan

### Phase 1: Backend Models, Authentication & APIs

- [ ] 1. Add database models to `/home/vishwas/Desktop/CC/community-air-quality/backend/app/models.py`
      Create `CommunitySensor` (id String PK, name, lat/lon, sensor_type, auth_token_hash, status, created_at, last_seen) and `CommunitySensorReading` (id Integer PK, sensor_id FK, sequence_number, pm25, pm10, temp nullable, humidity nullable, recorded_at, received_at, quality_status) following existing SQLAlchemy 2.0 mapped_column patterns in models.py.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/backend/app/models.py`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/backend && source .venv/bin/activate && python -c "from app.models import CommunitySensor, CommunitySensorReading; print('Models imported successfully')"` — imports without error.

- [ ] 2. Add Pydantic schemas to `/home/vishwas/Desktop/CC/community-air-quality/backend/app/schemas.py`
      Create `CommunitySensorOut`, `CommunitySensorReadingOut`, `CommunitySensorReadingSubmit`, `CommunitySensorRegister` following patterns from existing schemas.py.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/backend/app/schemas.py`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/backend && source .venv/bin/activate && python -c "from app.schemas import CommunitySensorOut, CommunitySensorReadingSubmit; print('Schemas imported successfully')"` — imports without error.

- [ ] 3. Install passlib for token hashing
      Add `passlib[bcrypt]==1.7.4` to `/home/vishwas/Desktop/CC/community-air-quality/backend/requirements.txt` and install.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/backend/requirements.txt`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/backend && source .venv/bin/activate && pip install -r requirements.txt && python -c "from passlib.hash import bcrypt; print('passlib installed')"` — no errors.

- [ ] 4. Create community sensors router at `/home/vishwas/Desktop/CC/community-air-quality/backend/app/routers/community_sensors.py`
      Implement 6 endpoints: POST /api/v1/community/sensors (register), POST /api/v1/community/sensors/readings (submit with Bearer auth), GET /api/v1/community/sensors (list with latest reading), GET /api/v1/community/sensors/{sensor_id}, GET /api/v1/community/sensors/{sensor_id}/readings (paginated), GET /api/v1/community/map. Follow patterns from routers/stations.py and routers/locations.py. Use passlib.hash.bcrypt for token hashing/verification.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/backend/app/routers/community_sensors.py`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/backend && source .venv/bin/activate && python -c "from app.routers import community_sensors; print('Router imported successfully')"` — imports without error.

- [ ] 5. Register router in `/home/vishwas/Desktop/CC/community-air-quality/backend/app/main.py`
      Import `from app.routers import community_sensors` and add `app.include_router(community_sensors.router, prefix="/api/v1")` following existing router registrations.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/backend/app/main.py`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000` (start in background), then `curl http://localhost:8000/docs | grep community` — OpenAPI docs include community endpoints.

- [ ] 6. Create seed script `/home/vishwas/Desktop/CC/community-air-quality/backend/app/seed_community_sensors.py`
      Generate 10 CommunitySensor records (SENSOR_001 to SENSOR_010) with Bengaluru coordinates, generate unique tokens with secrets.token_urlsafe(32), hash and store in DB, write plaintext tokens to `/home/vishwas/Desktop/CC/community-air-quality/backend/data/sensor_tokens.json` (gitignored). Follow pattern from seed.py.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/backend/app/seed_community_sensors.py`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/backend && source .venv/bin/activate && python -m app.seed_community_sensors && test -f data/sensor_tokens.json && wc -l data/sensor_tokens.json` — file exists and contains 10+ lines of JSON.

- [ ] 7. Ensure data directory is gitignored
      Verify or add `/backend/data/sensor_tokens.json` or `/backend/data/` pattern to `.gitignore`.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/.gitignore`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality && git check-ignore backend/data/sensor_tokens.json` — returns the file path (meaning it's ignored).

- [ ] 8. Write backend integration tests in `/home/vishwas/Desktop/CC/community-air-quality/backend/tests/test_community_sensors.py`
      Test registration, authenticated submission, invalid token rejection, duplicate sequence rejection, list/detail/readings endpoints. Follow patterns from test_api.py.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/backend/tests/test_community_sensors.py`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/backend && source .venv/bin/activate && pytest tests/test_community_sensors.py -v` — all tests pass.

### Phase 2: Simulator

- [ ] 9. Create simulator directory and module
      Create `/home/vishwas/Desktop/CC/community-air-quality/backend/app/simulator/` with `__init__.py`.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/backend/app/simulator/__init__.py`
      Verify: `test -d /home/vishwas/Desktop/CC/community-air-quality/backend/app/simulator && test -f /home/vishwas/Desktop/CC/community-air-quality/backend/app/simulator/__init__.py` — directory and file exist.

- [ ] 10. Create virtual sensors simulator at `/home/vishwas/Desktop/CC/community-air-quality/backend/app/simulator/virtual_sensors.py`
      Implement VirtualSensor class with state (pm25, pm10, temp, humidity, sequence_number, active). Implement generate_reading() (gradual changes +/-5 for pm25, proportional pm10, small temp/humidity changes). Implement submit_reading(api_base_url) (POST with Bearer token, log success/error). Implement load_sensors() (read sensor_tokens.json, query API for metadata). Implement main loop (every 5-10s submit for each active sensor). Add CLI with argparse for --api-url, --tokens-file, --spike, --disconnect, --reconnect.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/backend/app/simulator/virtual_sensors.py`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/backend && source .venv/bin/activate && python -m app.simulator.virtual_sensors --help` — shows usage and options.

- [ ] 11. Test simulator end-to-end
      Start backend (`uvicorn app.main:app`), run seed script, start simulator for 30 seconds, verify readings submitted successfully.
      Files: N/A (integration test)
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/backend && source .venv/bin/activate && (uvicorn app.main:app --port 8000 &); sleep 2; python -m app.simulator.virtual_sensors --api-url http://localhost:8000 & SIMPID=$!; sleep 30; kill $SIMPID; curl -s http://localhost:8000/api/v1/community/sensors/SENSOR_001/readings | jq '.count' | grep -E '[0-9]+'` — returns count > 0, indicating readings were stored.

### Phase 3: Frontend

- [ ] 12. Add TypeScript types to `/home/vishwas/Desktop/CC/community-air-quality/frontend/src/lib/types.ts`
      Add `CommunitySensor` (id, name, lat, lon, sensor_type, status, created_at, last_seen, latest_reading?) and `CommunitySensorReading` types matching backend schemas.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/frontend/src/lib/types.ts`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/frontend && npx tsc --noEmit` — no TypeScript errors.

- [ ] 13. Create community page at `/home/vishwas/Desktop/CC/community-air-quality/frontend/src/app/community/page.tsx`
      Client component that fetches `/api/v1/community/sensors` on mount and every 5s with useEffect + setInterval. State: sensors array, selectedSensorId, loading. Layout: header, metrics dashboard (total/online/offline counts), map (60% width), details+history panel (40% width).
      Files: `/home/vishwas/Desktop/CC/community-air-quality/frontend/src/app/community/page.tsx`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/frontend && npm run build` — builds without errors.

- [ ] 14. Create CommunitySensorMap component at `/home/vishwas/Desktop/CC/community-air-quality/frontend/src/components/community/CommunitySensorMap.tsx`
      Adapt from station-map.tsx. Marker color by PM2.5 level (green <30, yellow 30-60, orange 60-100, red >100, grey if last_seen >2 min ago). Popup shows sensor info and latest reading. OnClick sets selectedSensorId in parent.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/frontend/src/components/community/CommunitySensorMap.tsx`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/frontend && npx tsc --noEmit` — no TypeScript errors.

- [ ] 15. Create SensorDetails component at `/home/vishwas/Desktop/CC/community-air-quality/frontend/src/components/community/SensorDetails.tsx`
      Display selected sensor's name, ID, coordinates, status, last_seen, latest reading values (PM2.5, PM10, temp, humidity, recorded_at). Card styling consistent with existing components.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/frontend/src/components/community/SensorDetails.tsx`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/frontend && npx tsc --noEmit` — no TypeScript errors.

- [ ] 16. Create SensorHistory component at `/home/vishwas/Desktop/CC/community-air-quality/frontend/src/components/community/SensorHistory.tsx`
      Fetch `/api/v1/community/sensors/{sensor_id}/readings?limit=50` when selectedSensorId changes. Display Recharts LineChart with PM2.5 (blue) and PM10 (orange) lines, x-axis recorded_at, y-axis concentration. Handle loading/error/no-selection states.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/frontend/src/components/community/SensorHistory.tsx`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/frontend && npx tsc --noEmit` — no TypeScript errors.

- [ ] 17. Add navigation link to `/home/vishwas/Desktop/CC/community-air-quality/frontend/src/components/site-header.tsx`
      Add link to /community in site header navigation if not already present.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/frontend/src/components/site-header.tsx`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality/frontend && npm run build` — builds without errors.

- [ ] 18. Test frontend live updates
      Start backend, run seed, start simulator, start frontend dev server, open /community in browser, verify map shows 10 sensors, metrics update every 5s, selecting sensor shows details and chart.
      Files: N/A (manual test)
      Verify: Manual: Open http://localhost:3000/community, observe 10 markers on map, click one, verify details panel appears, verify metrics update every 5 seconds.

### Phase 4: Documentation & Integration

- [ ] 19. Update README with Community Sensor Network section
      Add section to `/home/vishwas/Desktop/CC/community-air-quality/README.md` explaining: what the feature demonstrates (simulated sensors, not real), how to seed sensors, how to run simulator, how to view the /community page, what the simulation demonstrates.
      Files: `/home/vishwas/Desktop/CC/community-air-quality/README.md`
      Verify: `cd /home/vishwas/Desktop/CC/community-air-quality && grep -i "community sensor" README.md` — section exists.

- [ ] 20. End-to-end smoke test: all components working together
      Start backend, seed sensors, start simulator, start frontend, verify: (1) 10 sensors created in DB, (2) simulator logs successful submissions, (3) backend API returns expected data, (4) invalid token rejected with 401, (5) DB contains readings in both tables, (6) spike changes readings, (7) disconnect makes sensor offline on frontend, (8) frontend shows live updates.
      Files: N/A (integration smoke test)
      Verify: Manual checklist: Run full stack (backend + simulator + frontend), execute each verification point, confirm all pass.

## Summary

This plan implements the Community Sensor Network in 3 phases: (1) Backend models/APIs with authentication, (2) Simulator with gradual measurement changes and scenarios, (3) Frontend with live map and polling. Each phase builds on the previous, with verification at each step. The implementation follows existing project patterns (SQLAlchemy models, FastAPI routers, Leaflet maps, Recharts) and uses simple HTTP polling (no MQTT/Kafka/Redis/WebSockets as required).
