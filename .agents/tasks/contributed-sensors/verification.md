# Verification Report: Community-Contributed Air Quality Sensor Network

## Review Iteration - Fixes Applied

This is the second iteration addressing review findings from `/home/vishwas/Desktop/CC/community-air-quality/.agents/tasks/contributed-sensors/2026-11-13-084953-review.md`.

### Review Findings Addressed

**Finding #1 (Simulator coordinates source mismatch) - FIXED**
- Created `backend/data/sensor_locations.json` with coordinate configuration
- Modified `virtual_sensors.py` to load coordinates from local config file instead of API
- Simulator now maintains internally configured geographical locations
- Coordinates included in every reading come from simulator's config, not backend

**Finding #4 (Token exposure in 201 response) - DOCUMENTED**
- Added docstring to registration endpoint noting HTTPS requirement and log redaction
- Token exposure unavoidable for registration flow but documented

**Finding #6 (Migration coordinate validation) - FIXED**
- Modified `run_migration.py` to validate existing sensors have valid coordinates
- Prints warning if seed sensors have NULL coordinates

**Finding #2 (Sequential ID race condition) - DOCUMENTED**
- Added comment in registration endpoint noting production should use SELECT FOR UPDATE or UUIDs
- Accepted as technical debt for MVP per user decision

**Finding #5 (Coordinate change validation) - DOCUMENTED**
- Added comment in readings endpoint noting stationary sensors expected
- Mobile sensors out of scope per user decision

**Finding #7 (Frontend "Awaiting first data" clarity) - DOCUMENTED**
- Added comment noting UI doesn't distinguish never-reported vs coordinates-missing
- Acceptable for MVP per user decision

## Verification Results

### Backend Tests

**Command:** `cd /home/vishwas/Desktop/CC/community-air-quality/backend && source .venv/bin/activate && pytest tests/ -v`

**Result:** ✅ **31 passed, 1 warning in 9.88s**

All tests pass. No regressions from review fixes.

### Frontend Build

**Command:** `cd /home/vishwas/Desktop/CC/community-air-quality/frontend && npm run build`

**Result:** ✅ **BUILD SUCCESSFUL**

```
✓ Compiled successfully in 5.5s
✓ Linting and checking validity of types
✓ Generating static pages (9/9)
```

TypeScript compilation clean. Created missing `not-found.tsx` to fix Next.js build error (unrelated to feature).

## Files Modified (Review Iteration)

**Backend:**
- `backend/app/simulator/virtual_sensors.py` - Load coordinates from config file, not API
- `backend/migrations/run_migration.py` - Add coordinate validation
- `backend/app/routers/community_sensors.py` - Add documentation comments for findings 2, 4, 5, 7

**Created:**
- `backend/data/sensor_locations.json` - Internal coordinate configuration for simulator (not in git, data/ is gitignored)
- `frontend/src/app/not-found.tsx` - Fix Next.js build error

**Note:** `sensor_locations.json` must be created manually in deployed environments with the same structure as `sensor_tokens.json` but containing `{"latitude": float, "longitude": float}` objects.

## Summary

✅ **REVIEW FIXES COMPLETE**

All confirmed findings addressed:
- Simulator coordinates now from internal config (Finding #1)
- Migration validates seed sensor coordinates (Finding #6)
- Token exposure documented (Finding #4)
- Race condition, stationary sensors, and UI clarity documented as accepted technical debt (Findings #2, #5, #7)

Backend: 31/31 tests pass
Frontend: Clean build
Ready for commit.

---

## 2026-11-13: Add Sensor form UI + random Bengaluru location

### Changes
- `frontend/src/components/community/AddSensorModal.tsx`: rendered through `createPortal(document.body)` at `z-[2000]`, which is above Leaflet's panes and controls (400-1000). While the modal is open, every other body child is `inert` and body scroll is locked. Escape and backdrop click close it, and focus moves to the first field. Restyled with the app's own primitives: `SectionHeading`, `Banner` (info/warn/error), `.field`, `.btn btn-primary`, `.btn btn-ghost`, `.eyebrow`, `bg-surface-solid`, `rounded-3xl`, `shadow-pop`, lucide icons. It still has exactly four fields (name, hardware_id, hardware_model, contributor_name) and no location fields. Errors returned as arrays (422) now show a message instead of `[object Object]`.
- `frontend/src/app/community/page.tsx`: the Add Sensor button uses `btn btn-primary` with a `Plus` icon, replacing the off-palette blue button.
- `frontend/src/app/api/v1/[...path]/route.ts`: keeps the `API_INTERNAL_URL ?? "http://127.0.0.1:8000"` fix and **now forwards the `content-type` header**. Without it, FastAPI received the POST body as a string and every UI registration failed with 422. This was found during browser verification.
- `backend/app/config.py`: adds `SIMULATOR_AUTO_PROVISION` (default `false`) and `SIMULATOR_TOKENS_FILE` (default `data/sensor_tokens.json`).
- `backend/app/simulator/provisioning.py` (new): when the setting is enabled, `POST /community/sensors/register` atomically adds `sensor_id -> token` to the simulator tokens file. It writes only to that file and never touches the readings table.
- `backend/app/simulator/virtual_sensors.py`: the loop reloads the tokens/locations files every round. A new device gets its location from the first source that has one: (1) its locations-file entry, (2) the coordinates the backend already holds for it, (3) a random point in lat 12.85-13.10, lon 77.50-77.75, at least 0.005° from existing sensors. The location is then written back to `sensor_locations.json` so it stays fixed across restarts. A device's sequence number resumes after the backend's latest reading. New devices wait until the API is reachable, which avoids a duplicate-sequence storm at startup. Readings are still sent only via `POST /api/v1/community/sensors/readings`.
- `docker-compose.yml`: the backend sets `SIMULATOR_AUTO_PROVISION: "true"` (local demo). A new `simulator` service (built from ./backend, `air-data` volume, `--api-url http://backend:8000`, `restart: unless-stopped`) is added.
- Decision kept: registration still collects no location. The backend learns location only from readings, and the simulated device chooses and keeps its own random Bengaluru location.

### One-time data step (volume)
The volume had no tokens or locations files. I seeded them from the host copies, whose tokens match the seed hashes in the volume DB:
`docker compose cp backend/data/sensor_tokens.json backend:/app/data/sensor_tokens.json` (and the same for `sensor_locations.json`). Neither file is committed.

### Results
1. `npm run build`: compiled successfully, all routes built. `.venv/bin/pytest tests/ -q`: **34 passed** (31 existing + 3 new in `tests/test_simulator_provisioning.py`: provisioning on/off, random point inside the bounds and away from existing ones, location persisted and reused after restart).
2. `docker compose up -d --build`: backend `/api/v1/health` 200, frontend `/community` 200. The compose simulator logs `✓ SENSOR_001..010 seq=91.. status=201`.
3. Headless Chrome (playwright-core, /usr/bin/google-chrome, 1440x1000), screenshots in `screenshots/`:
   - `addsensor-01-home-reference.png` (reference page), `addsensor-02-modal-over-map.png`, `addsensor-03-validation.png`, `addsensor-04-success.png` (local only, not committed: it shows a live sensor token), `addsensor-05-new-sensor-on-map.png`.
   - `document.elementFromPoint` at the map centre, the zoom control and the bottom-right attribution all resolve inside `[data-modal-root]` and none inside `.leaflet-container`.
   - Form inputs: `name,hardware_id,hardware_model,contributor_name`. Page behind is inert: true. Closed by Escape: true. Closed by backdrop click: true.
   - Computed styles: Geist font, dialog bg `rgb(16,23,30)` (`--surface-solid`), 24px radius, inputs 12px with `--surface-2` bg, submit `rgb(79,227,193)` (accent). These match the home page cards and buttons.
4. Registered "Balcony Monitor" through the UI and got `SENSOR_011`. The first reading arrived **6.2 s** later. `GET http://localhost:3000/api/v1/community/sensors` returns `SENSOR_011 source=contributed lat=12.9647 lon=77.6525 latest_reading seq=1 pm25=68.3 pm10=93.11`. The map went from 10 to 11 markers, and the popup shows the new sensor at 12.9647, 77.6525. A second sensor registered by the user from the UI during this run (`SENSOR_012`, "sensor 1") also got its own random location at 12.9131, 77.7471 and is reporting. After `docker compose restart simulator`, both kept the same coordinates and resumed at the next sequence number (seq 28 / 26, status 201).

### Host-side simulator
The compose `simulator` service now reports for SENSOR_001..010 and for every contributed sensor, so **the host-side simulator (`python -m app.simulator.virtual_sensors --api-url http://localhost:8000`) is no longer needed and should be stopped**. While both run, they send the same sequence numbers for the seed sensors, and whichever one is second gets `400 Duplicate sequence number`. The sensors still receive readings from the other simulator.

### Out-of-scope finding (not changed)
The UI shows every sensor as **Offline** ("Last seen: 5 hours ago"), even ones that reported seconds earlier. The backend returns naive UTC timestamps (e.g. `2026-11-13T04:31:22.417769`, no `Z`), and the browser parses them as local time (IST, +5:30). This bug predates this task (Online = 0 in every screenshot). Fixing it means emitting `Z`-suffixed timestamps from the API or treating them as UTC in the frontend. I left it alone because it is outside this task's scope.
