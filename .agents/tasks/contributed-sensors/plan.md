# Implementation Plan: Community-Contributed Air Quality Sensor Network

## Overview

This plan implements a feature that allows users to register air quality sensors and contribute measurements with embedded geographical coordinates. The implementation extends the existing Community Sensor Network, preserves all 10 existing Bengaluru sensors, and works entirely locally (SQLite, no cloud dependencies). Key architectural decision: sensors report their location with each reading; no location is collected during registration.

**Order of implementation is critical:** Database schema must be migrated before model changes, and backend must be complete before frontend work begins.

---

## Implementation Steps

- [ ] 1. **Create database migration script and execute schema changes**
      
      Create `backend/migrations/001_add_contributed_sensor_fields.sql` with ALTER TABLE statements to add new columns to `community_sensors` (hardware_id, hardware_model, contributor_name, source) and `community_sensor_readings` (latitude, longitude). Make latitude/longitude nullable in community_sensors by recreating the table (SQLite limitation). Execute migration manually using Python script that opens the database and runs the SQL.
      
      **Decision:** Use table recreation for community_sensors to change latitude/longitude to nullable (SQLite doesn't support ALTER COLUMN). Copy existing data, drop old table, create new table with correct schema, restore data.
      
      Files:
      - Create: `backend/migrations/001_add_contributed_sensor_fields.sql`
      - Create: `backend/migrations/run_migration.py` (standalone script to execute SQL)
      
      Verify: Run `python backend/migrations/run_migration.py`, then check schema with `python -c "from app.database import get_db; from app.config import get_settings; from sqlalchemy import inspect; eng = create_engine(get_settings().database_url); insp = inspect(eng); print(insp.get_columns('community_sensors'))"` - confirm source, hardware_id, hardware_model, contributor_name, and nullable lat/lon exist.

- [ ] 2. **Update database models with new fields**
      
      Modify `backend/app/models.py`: In `CommunitySensor`, change latitude and longitude to `Mapped[float | None]` (nullable), add source, hardware_id, hardware_model, contributor_name fields. In `CommunitySensorReading`, add latitude and longitude fields (nullable). These changes match the schema created in step 1.
      
      Files:
      - `backend/app/models.py`
      
      Verify: Run `pytest tests/` - all existing tests pass (no schema mismatch errors). If tests fail due to missing data, proceed to step 3 first, then rerun.

- [ ] 3. **Update seed script to set source='seed' for existing sensors**
      
      Modify `backend/app/seed_community_sensors.py`: Add `source='seed'` when creating CommunitySensor instances. Ensure hardware_id, hardware_model, contributor_name are explicitly None for backward compatibility. Re-run seed script to update existing sensors (script already has idempotency - skips existing sensors but we need to update them, so add an update path for sensors that exist but have NULL source).
      
      **Decision:** Seed script will UPDATE existing sensors to set source='seed' if currently NULL, ensuring existing 10 Bengaluru sensors are properly tagged.
      
      Files:
      - `backend/app/seed_community_sensors.py`
      
      Verify: Run `python -m app.seed_community_sensors` from backend directory. Check database: `python -c "from sqlalchemy import create_engine; from app.config import get_settings; eng = create_engine(get_settings().database_url); with eng.connect() as conn: print(conn.execute('SELECT id, source FROM community_sensors').fetchall())"` - confirm all 10 sensors have source='seed'.

- [ ] 4. **Add new Pydantic schemas for contributed sensor registration**
      
      Add to `backend/app/schemas.py`: `ContributedSensorRegisterRequest` (name, hardware_id, hardware_model, contributor_name with validation), `ContributedSensorRegisterResponse` (sensor_id, token, ingestion_url, message). Modify `CommunitySensorOut` to include source, hardware_id, hardware_model, contributor_name and make latitude/longitude nullable. Modify `CommunitySensorReadingSubmit` and `CommunitySensorReadingOut` to add latitude/longitude fields (both nullable).
      
      Files:
      - `backend/app/schemas.py`
      
      Verify: Import schemas in Python REPL: `from app.schemas import ContributedSensorRegisterRequest, ContributedSensorRegisterResponse; print(ContributedSensorRegisterRequest.model_fields)` - no import errors, fields match specification.

- [ ] 5. **Implement POST /api/v1/community/sensors/register endpoint**
      
      Add new route to `backend/app/routers/community_sensors.py`: Registration endpoint that generates sequential sensor ID (query max SENSOR_XXX, increment), generates 32-byte token, hashes with bcrypt, creates CommunitySensor with source='contributed' and sensor_type='contributed', latitude=None, longitude=None. Implement retry logic (3 attempts) for IntegrityError on primary key collision. Return sensor_id, plaintext token, ingestion URL.
      
      **Decision:** Sequential IDs (SENSOR_011, SENSOR_012...) for MVP; UUID deferred to production. Retry logic handles race conditions.
      
      Files:
      - `backend/app/routers/community_sensors.py` (add imports: IntegrityError, text from sqlalchemy; secrets already imported)
      
      Verify: Start backend (`uvicorn app.main:app --port 8000`), test with curl: `curl -X POST http://localhost:8000/api/v1/community/sensors/register -H "Content-Type: application/json" -d '{"name":"Test Sensor","hardware_id":"ESP32-TEST","hardware_model":"ESP32+PMS5003","contributor_name":"Test User"}'` - returns 201 with sensor_id starting with SENSOR_0, token, ingestion_url.

- [ ] 6. **Modify POST /api/v1/community/sensors/readings endpoint to handle coordinates**
      
      Modify existing readings endpoint in `backend/app/routers/community_sensors.py`: Add coordinate validation (if provided: range checks -90..90 lat, -180..180 lon, math.isfinite() check for NaN/Inf). For contributed sensors (source='contributed'), require latitude and longitude (raise 400 if missing). Add temperature range validation (-40..60°C) if provided. Store coordinates in CommunitySensorReading. Update sensor.latitude and sensor.longitude with latest reported coordinates if provided. Add `import math` at top of file.
      
      Files:
      - `backend/app/routers/community_sensors.py`
      
      Verify: Using sensor from step 5, submit reading with coordinates: `curl -X POST http://localhost:8000/api/v1/community/sensors/readings -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d '{"sensor_id":"SENSOR_011","sequence_number":1,"pm25":35.5,"pm10":58.2,"temperature":28.0,"humidity":65.0,"latitude":12.9352,"longitude":77.6245,"recorded_at":"2024-11-13T10:00:00Z"}'` - returns 201. Submit again without lat/lon - returns 400 "Latitude and longitude required". Submit with latitude=999 - returns 400 "Invalid latitude".

- [ ] 7. **Modify GET /api/v1/community/sensors endpoint to return new fields**
      
      Update `_sensor_to_out` helper in `backend/app/routers/community_sensors.py` to include source, hardware_id, hardware_model, contributor_name in CommunitySensorOut construction. Update reading output construction to include latitude and longitude from CommunitySensorReading.
      
      Files:
      - `backend/app/routers/community_sensors.py`
      
      Verify: `curl http://localhost:8000/api/v1/community/sensors` - JSON response includes "source" field for all sensors, and newly registered sensor shows hardware_id, hardware_model, contributor_name, with lat/lon matching the submitted reading from step 6.

- [ ] 8. **Modify GET /api/v1/community/map endpoint to filter sensors without coordinates**
      
      Update map endpoint in `backend/app/routers/community_sensors.py`: Add WHERE clauses to filter sensors with latitude.is_not(None) and longitude.is_not(None). Add source field to sensor_data dictionary.
      
      Files:
      - `backend/app/routers/community_sensors.py`
      
      Verify: Register a new sensor but don't submit any readings. Call `curl http://localhost:8000/api/v1/community/map` - the new sensor (with null lat/lon) does NOT appear in the sensors array. After submitting a reading with coordinates (step 6 verification), call map endpoint again - sensor now appears with correct coordinates.

- [ ] 9. **Update frontend types to match new backend schemas**
      
      Modify `frontend/src/lib/types.ts`: Change CommunitySensor type to make latitude and longitude nullable (`number | null`), add source, hardware_id, hardware_model, contributor_name fields (all nullable for seed sensors). Add latitude and longitude to CommunitySensorReading type (nullable).
      
      Files:
      - `frontend/src/lib/types.ts`
      
      Verify: Run `npm run build` from frontend directory - no TypeScript compilation errors.

- [ ] 10. **Create AddSensorModal component for sensor registration**
      
      Create `frontend/src/components/community/AddSensorModal.tsx`: Modal component with form (4 fields: name, hardware_id, hardware_model, contributor_name), form validation (all required, max lengths), POST to /api/v1/community/sensors/register, success state showing sensor_id and token with copy-to-clipboard buttons and security warning, error display for API failures. Use Tailwind CSS for styling matching existing components. Modal uses isOpen prop and onClose callback, plus onSuccess callback to refresh parent sensor list.
      
      **Design decision:** Two-stage modal - form view, then success view with connection details. Token displayed as monospace text with "⚠️ Store securely" warning.
      
      Files:
      - Create: `frontend/src/components/community/AddSensorModal.tsx`
      
      Verify: `npm run build` - no compilation errors. Start dev server (`npm run dev`), visually inspect modal in browser dev tools (will integrate with page in step 12).

- [ ] 11. **Modify CommunitySensorMap to show source badges and filter invalid coordinates**
      
      Update `frontend/src/components/community/CommunitySensorMap.tsx`: Filter sensors at component entry: `const validSensors = sensors.filter(s => s.latitude !== null && s.longitude !== null)`. Use validSensors for map markers. In marker popup, add source badge below sensor details: if source === 'contributed', render blue badge "Community Contributed". Existing color coding and online/offline status unchanged.
      
      Files:
      - `frontend/src/components/community/CommunitySensorMap.tsx`
      
      Verify: `npm run build` - no errors. In browser (next step after integration), register sensor without submitting reading - sensor does not appear on map. After submitting reading with coordinates via simulator, sensor appears at correct location with blue "Community Contributed" badge in popup.

- [ ] 12. **Modify SensorDetails component to handle sensors awaiting first data**
      
      Update `frontend/src/components/community/SensorDetails.tsx`: Add conditional rendering for location field - if latitude and longitude are null, show "Awaiting first data" in italic gray text instead of coordinates. Display source badge ("Community Contributed" for contributed, or no badge for seed). Show hardware_id, hardware_model, contributor_name fields if present (only for contributed sensors). Existing readings display unchanged.
      
      Files:
      - `frontend/src/components/community/SensorDetails.tsx`
      
      Verify: `npm run build` - no errors. After integration with page (step 13), test with new sensor before submitting reading - details panel shows "Awaiting first data" and metadata fields. After reading submitted, shows coordinates.

- [ ] 13. **Integrate AddSensorModal into Community page with Add Sensor button**
      
      Modify `frontend/src/app/community/page.tsx`: Add state for modal visibility, add "Add Sensor" button in page header (next to title), wire up modal open/close handlers, add onSuccess callback that refetches sensors (existing useEffect already polls every 5 seconds, but add immediate refresh on success). Import AddSensorModal component dynamically to avoid SSR issues if needed (modal itself doesn't use Leaflet, but test first with static import).
      
      Files:
      - `frontend/src/app/community/page.tsx`
      
      Verify: Run `npm run dev`, open http://localhost:3000/community. Click "Add Sensor" button - modal opens. Fill form, submit - success view shows sensor_id and token. Close modal - new sensor appears in metrics (Total Sensors count increases). Sensor NOT on map yet (awaiting data). Check browser console - no React errors.

- [ ] 14. **Update simulator to include coordinates in readings payload**
      
      Modify `backend/app/simulator/virtual_sensors.py`: In `generate_reading()` method of VirtualSensor class, add "latitude" and "longitude" fields to reading dict using self.latitude and self.longitude (already stored as instance variables from API metadata). No other changes needed - simulator already fetches sensor metadata including coordinates, and already submits via HTTP to readings endpoint.
      
      **Verification note:** Simulator already has lat/lon as instance variables from API; this step just includes them in the reading payload.
      
      Files:
      - `backend/app/simulator/virtual_sensors.py`
      
      Verify: Start backend, register a new contributed sensor via UI (step 13), manually add sensor_id and token to `backend/data/sensor_tokens.json`, edit the new VirtualSensor creation in load_sensors to set latitude/longitude for the new sensor, run simulator: `python -m app.simulator.virtual_sensors --api-url http://localhost:8000`. Check console output - readings accepted (status 201). In frontend, new sensor appears on map at correct location within 5-10 seconds.

- [ ] 15. **Manual registration testing: add a contributed sensor token to simulator config**
      
      Using the UI from step 13, register a new sensor and copy the token. Edit `backend/data/sensor_tokens.json` to add the new sensor_id and token as a JSON key-value pair. The simulator's `load_sensors()` function already loads this file and fetches metadata from the API, so no code change needed - this step is workflow documentation.
      
      **Note:** This step documents the manual bridge between UI registration and simulator. In production, physical devices would use the token directly. For local testing, we manually add tokens to the JSON file the simulator reads.
      
      Files:
      - `backend/data/sensor_tokens.json` (manual edit by user)
      
      Verify: After editing JSON file, run simulator: `python -m app.simulator.virtual_sensors --api-url http://localhost:8000`. Simulator output includes the newly registered sensor submitting readings. Frontend shows sensor updating in real-time with green/yellow/orange/red marker colors based on PM2.5 values.

- [ ] 16. **Update simulator documentation (SIMULATOR_QUICKSTART.md)**
      
      Modify `backend/SIMULATOR_QUICKSTART.md` (or create if missing): Add section "Running Contributed Sensors in Simulator" explaining: 1) Register sensor via UI, 2) Copy sensor_id and token, 3) Add to backend/data/sensor_tokens.json, 4) Run simulator normally - it will automatically detect and simulate the new sensor. Include example JSON structure for tokens file. Note that simulator loads sensor metadata (including location) from backend API, so coordinates are pulled automatically.
      
      Files:
      - `backend/SIMULATOR_QUICKSTART.md` (create or update)
      
      Verify: Read the documentation and follow it manually - instructions should be clear and complete. Running the documented steps should successfully add and simulate a contributed sensor.

- [ ] 17. **Run full backend test suite and verify no regressions**
      
      Run `pytest tests/` from backend directory with virtualenv active. All existing tests must pass. If tests fail due to new required fields, update test fixtures in tests/conftest.py to include source='seed' for test sensors created in fixtures. Do NOT modify test assertions that check response structures - if those fail, the schema changes in earlier steps broke backward compatibility and must be fixed.
      
      Files:
      - `backend/tests/conftest.py` (if test fixtures need source field)
      - Backend code (if tests reveal bugs in earlier steps)
      
      Verify: `cd backend && source .venv/bin/activate && pytest tests/ -v` - all tests pass, no failures or errors. If test_api.py::test_health fails, check FastAPI app startup for model/schema mismatches.

- [ ] 18. **End-to-end integration test: complete registration-to-display flow**
      
      Start backend (`uvicorn app.main:app --reload --port 8000`), start frontend (`npm run dev`), start simulator (`python -m app.simulator.virtual_sensors --api-url http://localhost:8000`). Open http://localhost:3000/community. Click "Add Sensor", fill form with: name="Integration Test Sensor", hardware_id="INT-TEST-001", hardware_model="Test Device", contributor_name="Test User". Submit. Copy sensor_id and token from success dialog. Add to backend/data/sensor_tokens.json. Restart simulator. Within 15 seconds, sensor should appear on map. Click marker - popup shows "Community Contributed" badge and latest readings. Select sensor - details panel shows metadata (hardware info, contributor). Sensor status is "online" (green badge). Historical chart shows PM2.5/PM10 trends building up.
      
      **Expected outcomes:**
      - New sensor appears in metrics (Total Sensors count)
      - After first reading: sensor appears on map at reported coordinates
      - Map marker color reflects PM2.5 value (green/yellow/orange/red)
      - Marker popup shows "Community Contributed" badge
      - Details panel shows hardware_id, hardware_model, contributor_name
      - Status badge shows "online" (green)
      - Historical chart updates with new readings every 5-10 seconds
      - Existing 10 Bengaluru sensors remain unchanged, no "Community Contributed" badge
      
      Files: None (manual testing)
      
      Verify: Manually execute the flow above. All expected outcomes must occur. Take screenshots or record video for documentation. If any step fails, identify which implementation step introduced the bug, fix it, and retest from step 17.

---

## Verification Commands Summary

**Database schema check:**
```bash
cd /home/vishwas/Desktop/CC/community-air-quality/backend
python -c "from sqlalchemy import create_engine, inspect; from app.config import get_settings; eng = create_engine(get_settings().database_url); insp = inspect(eng); cols = insp.get_columns('community_sensors'); print([c['name'] for c in cols])"
```
Expected output includes: source, hardware_id, hardware_model, contributor_name

**Backend tests:**
```bash
cd /home/vishwas/Desktop/CC/community-air-quality/backend
source .venv/bin/activate
pytest tests/ -v
```
Expected: All tests pass (31 collected based on current state)

**Frontend build:**
```bash
cd /home/vishwas/Desktop/CC/community-air-quality/frontend
npm run build
```
Expected: Build succeeds with no TypeScript errors

**Start backend:**
```bash
cd /home/vishwas/Desktop/CC/community-air-quality/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Start frontend:**
```bash
cd /home/vishwas/Desktop/CC/community-air-quality/frontend
npm run dev
```

**Start simulator:**
```bash
cd /home/vishwas/Desktop/CC/community-air-quality/backend
source .venv/bin/activate
python -m app.simulator.virtual_sensors --api-url http://localhost:8000
```

---

## Key Design Decisions

1. **Database Migration Strategy:** Table recreation for community_sensors to change lat/lon to nullable (SQLite limitation), ALTER TABLE for new columns. Manual migration script preserves existing data.

2. **Sensor ID Generation:** Sequential numeric suffix (SENSOR_011, SENSOR_012) with 3-attempt retry on collision. Matches existing pattern, human-readable for MVP. UUID deferred to production.

3. **Location Handling:** Sensors register without location; coordinates provided in each reading and stored in both readings table (historical) and sensors table (latest). "Awaiting first data" state for sensors with null coordinates.

4. **Source Distinguishing:** Two fields work together - sensor_type ('virtual' vs 'contributed' for programmatic context) and source ('seed' vs 'contributed' for UI display). Frontend shows "Community Contributed" badge only for source='contributed'.

5. **Backward Compatibility:** Existing seed sensors can submit readings without coordinates. New readings endpoint requires coordinates only for source='contributed' sensors. Existing 10 sensors preserved with source='seed', remain fully functional.

6. **Token Security:** 32-byte tokens (43 base64 chars), bcrypt hashed in database. Displayed once in UI with security warning. User must copy and store securely - no retrieval endpoint.

7. **Simulator Integration:** Manual bridge for MVP - user registers in UI, copies token, adds to sensor_tokens.json. Simulator loads tokens file, fetches metadata from API (including coordinates seeded in the sensor record once first reading arrives), simulates readings with coordinates. Physical devices would use token directly in production.

8. **Frontend State:** Sensors without coordinates excluded from map but appear in sensors list. Details panel shows "Awaiting first data" until first reading with coordinates arrives. Existing polling (5-second interval) handles real-time updates automatically.

---

## Dependencies and Constraints

- Python 3.12, FastAPI, SQLAlchemy 2.x, bcrypt already installed (requirements.txt)
- React 19, Next.js, Leaflet, Recharts already installed (package.json)
- SQLite database at `backend/data/airquality.db` (existing)
- 10 Bengaluru sensors already seeded with IDs SENSOR_001 through SENSOR_010
- Simulator already exists and functional - modification only adds coordinates to payload
- Local development only - no cloud dependencies, no authentication/authorization beyond sensor tokens
- No test framework for frontend (no package.json scripts for jest/vitest) - verification is build + manual testing

---

## Out of Scope (Deferred)

- User authentication for registration (anyone can register sensors)
- Sensor management UI (edit, delete, transfer ownership)
- Historical coordinate tracking display (map shows only latest location)
- Advanced filtering (by source, by contributor, by PM2.5 range)
- CSV export of contributed sensor data
- Cloud deployment configuration
- Physical device integration instructions beyond token usage
- GPS hardware specification or integration
- Multi-tenant isolation (all sensors visible to all users)
