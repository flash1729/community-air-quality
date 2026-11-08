# Community-Contributed Air Quality Sensor Network

Adds user sensor registration to the existing Community Sensor Network without requiring location input during registration. Sensors report coordinates with each measurement. Backend generates sequential IDs starting from SENSOR_011, validates coordinates, and updates sensor location. Frontend shows "Awaiting first data" for sensors without coordinates, displays "Community Contributed" badges, and renders the Add Sensor modal with four fields. Python simulator loads coordinates from local config file and includes them in every HTTP reading submission. All 10 existing seed sensors preserved with source='seed'.

The registration-to-display flow works: user registers sensor with four fields (name, hardware ID, hardware model, contributor name) → backend generates SENSOR_0XX ID and token → simulator loads coordinates from local config → simulator submits readings via HTTP with coordinates → backend validates and stores coordinates in both readings table and sensor's latest location → frontend filters sensors without coordinates from map → sensor appears on map after first valid reading → "Community Contributed" badge shown in map popup and details panel.

**Watch for:** Sequential ID race condition under concurrent load (confirmed - no SELECT FOR UPDATE, documented as MVP technical debt), token exposed in 201 response requires HTTPS in production (confirmed - plaintext in response body, documented), coordinate validation added in migration (confirmed - validates seed sensors have non-NULL coordinates).

**Verdict**: APPROVED

## High-level view

Registration endpoint generates sequential IDs by querying MAX(id) and incrementing, with 3-attempt retry on collision but no row-level locking. Under concurrent registration load two requests could generate the same ID. The coder documented this as technical debt acceptable for local MVP; production needs SELECT FOR UPDATE or UUIDs.

Coordinates flow through two storage points: every reading stores its reported latitude/longitude in community_sensor_readings (historical), and the sensor's latitude/longitude columns are updated to the latest reported coordinates (current location for map display). Seed sensors have fixed coordinates; contributed sensors start with NULL and get populated on first reading submission. Map endpoint filters WHERE latitude IS NOT NULL AND longitude IS NOT NULL, excluding sensors awaiting first data.

Token security follows bcrypt hashing with 32-byte tokens for contributed sensors (24-byte for seed sensors). Registration response returns plaintext token once; no retrieval endpoint exists. The coder documented that HTTPS is required in production and logs should redact tokens. For local testing with HTTP and console logging, token exposure is a known gap.

Simulator coordinates come from backend/data/sensor_locations.json (local config file), not from the API. This matches the requirement that devices maintain internally configured locations and report coordinates with every reading. Physical devices would have GPS or manual provisioning; the simulator uses a JSON config as the equivalent of that internal source.

Frontend distinguishes contributed sensors with source field and renders blue "Community Contributed" badge in map popups and details panel. Sensors with null coordinates show "Awaiting first data" in details panel location field and do not appear on map. The UI doesn't distinguish between "never reported" and "reported without coordinates" — both show the same awaiting state, acceptable for MVP per verification notes.

All 10 existing Bengaluru sensors (SENSOR_001 through SENSOR_010) preserved with source='seed'. Seed script sets source='seed' for new sensors and updates existing sensors if source is NULL. Database migration recreates community_sensors table to make latitude/longitude nullable (SQLite limitation), copies existing data, sets source='seed' for all existing sensors, and adds coordinate columns to community_sensor_readings.

<details>
<summary>Issues (4)</summary>

1. **Sequential ID race condition** — Two concurrent registration requests can generate the same sensor ID because MAX(id) query and INSERT are not atomic. Add SELECT FOR UPDATE or switch to UUIDs in production.

2. **Token exposure in plaintext response** — Registration endpoint returns token in 201 response body, visible in logs and network traffic. Require HTTPS in production and configure log redaction for token field.

3. **Stationary sensor assumption** — Backend accepts coordinate changes on every reading without validation. If a sensor reports wildly different coordinates, the map location jumps. Add coordinate drift detection if mobile sensors become a requirement.

4. **UI "Awaiting first data" ambiguity** — Frontend shows "Awaiting first data" for sensors with null coordinates but doesn't distinguish between "never reported any reading" and "reported readings without coordinates." Acceptable for MVP where contributed sensors always include coordinates.

</details>

<details>
<summary>Details</summary>

## Registration without location input

The Add Sensor form collects exactly four fields: name, hardware_id, hardware_model, contributor_name. No latitude or longitude fields. Backend generates sequential sensor ID by querying `MAX(CAST(SUBSTR(id, 8) AS INTEGER))` from sensors with id LIKE 'SENSOR_%', incrementing, and formatting as SENSOR_XXX. First contributed sensor becomes SENSOR_011.

The registration endpoint includes 3-attempt retry on IntegrityError to handle primary key collisions. Each attempt queries MAX and generates a new ID. This handles the race condition where another thread committed between the MAX query and the INSERT, but doesn't prevent two threads from reading the same MAX value simultaneously. Production should use SELECT FOR UPDATE or UUIDs.

## Coordinates in every reading

For contributed sensors (source='contributed'), the readings endpoint requires latitude and longitude and returns 400 if missing. Coordinate validation: latitude must be finite number between -90 and 90; longitude between -180 and 180. math.isfinite() catches NaN and Infinity.

Readings endpoint creates CommunitySensorReading with coordinates from payload and updates sensor.latitude and sensor.longitude if provided. The sensor's current location is always its latest reported coordinates. Historical coordinates preserved in readings table. No validation that coordinates stay within reasonable drift range — a sensor reporting wildly different coordinates on each reading will cause the map location to jump.

## Simulator coordinate source

VirtualSensor class receives latitude and longitude in constructor. generate_reading() includes coordinates in reading dict. Coordinates come from load_sensors(), which reads backend/data/sensor_locations.json and creates VirtualSensor instances with coordinates from that file — not from the API. This matches the requirement that devices maintain internally configured locations.

sensor_locations.json maps sensor_id to {latitude, longitude} object. Simulator requires both sensor_tokens.json and sensor_locations.json. If a sensor exists in tokens file but not in locations file, simulator logs warning and skips that sensor.

## Source distinguishing and badge display

Database source field distinguishes 'seed' (existing 10 Bengaluru sensors) from 'contributed' (user-registered sensors). Frontend checks `if (sensor.source === "contributed")` and renders blue "Community Contributed" badge in map popup and details panel.

## Database migration and existing sensor preservation

Migration 001_add_contributed_sensor_fields.sql recreates community_sensors table to make latitude/longitude nullable (SQLite doesn't support ALTER COLUMN). Steps: create community_sensors_new with updated schema, INSERT...SELECT to copy data with source='seed' for all rows, drop old table, rename new table, recreate index. Adds latitude/longitude columns to community_sensor_readings via ALTER TABLE.

run_migration.py executes SQL via executescript(), verifies schema changes, and validates that seed sensors have non-NULL coordinates. Prints warning if any seed sensors have NULL coordinates.

## Test coverage

Backend: 31 tests pass (pytest tests/ -v). Tests cover sensor registration, reading submission, coordinate validation, bearer token auth, duplicate sequence number rejection.

Frontend: no test suite exists. Verification via `npm run build` (TypeScript compilation clean) and manual E2E testing.

Not tested: concurrent registration race condition, token exposure in logs, coordinate drift detection (not implemented), historical coordinate tracking (stored but no UI or API), migration idempotency or rollback (SQLite doesn't support transactions across schema changes).

## Files changed

- `backend/app/routers/community_sensors.py` — Registration endpoint, coordinate validation in readings, map filtering
- `backend/app/models.py` — Nullable coordinates, source/hardware fields
- `backend/app/schemas.py` — Registration request/response, coordinate fields
- `backend/app/simulator/virtual_sensors.py` — Load coordinates from JSON config
- `backend/migrations/` — Schema migration and verification
- `frontend/src/components/community/AddSensorModal.tsx` — Registration form
- `frontend/src/components/community/CommunitySensorMap.tsx` — Filter null coordinates, badge display
- `frontend/src/components/community/SensorDetails.tsx` — "Awaiting first data" state, hardware fields
- `frontend/src/app/community/page.tsx` — Add Sensor button, modal integration
- `frontend/src/lib/types.ts` — Nullable coordinates, source field

</details>

<details>
<summary>File map</summary>

**Backend (Python/FastAPI/SQLite):**
- `app/routers/community_sensors.py` — Registration and readings endpoints, coordinate validation, map filtering
- `app/models.py` — Nullable coordinates, source field, hardware metadata columns
- `app/schemas.py` — Registration request/response, coordinate fields in reading schemas
- `app/seed_community_sensors.py` — Source='seed' for existing sensors
- `app/simulator/virtual_sensors.py` — Load coordinates from JSON config, include in readings
- `migrations/001_add_contributed_sensor_fields.sql` — Schema changes for contributed sensors
- `migrations/run_migration.py` — Execute migration and verify schema

**Frontend (React/Next.js/TypeScript):**
- `components/community/AddSensorModal.tsx` — Registration form and success view
- `components/community/CommunitySensorMap.tsx` — Filter null coordinates, show badges
- `components/community/SensorDetails.tsx` — Display metadata, "Awaiting first data" state
- `app/community/page.tsx` — Add Sensor button, modal integration
- `lib/types.ts` — Nullable coordinates, source field

**Data (gitignored):**
- `backend/data/sensor_tokens.json` — Sensor ID to plaintext token mapping for simulator
- `backend/data/sensor_locations.json` — Sensor ID to coordinates mapping for simulator

Full diff: `git diff 034b6f7..HEAD` (commits 8b730fc and 3e9f600)

</details>
