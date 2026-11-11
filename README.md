# Community Air Quality & Environmental Health Dashboard

Local air-quality dashboard for a cloud computing project. People can search a city, see station readings, an Indian AQI when CPCB inputs are valid, compare cities, filter history, download a CSV, and view a model forecast that stays separate from station data.

The public site is https://community-air-quality.vercel.app. The API runs on Cloud Run in `us-central1` and scales to zero when nobody is using it. Cloud SQL stays off. There is no always-free Cloud SQL allowance, so the database remains SQLite inside the API container.

## Run it locally

Use two terminals.

### API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs

### Dashboard

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

The dashboard talks to the API through the Next.js server, so the browser does not call OpenAQ or Open-Meteo directly.

### Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

### Docker Compose

From the repository root, after copying `.env.example` to `.env` if you have a key:

```bash
docker compose up --build
```

The web containers stay up. The popular-city refresh is a separate one-shot process, which is the same shape as a cloud scheduled task:

```bash
docker compose --profile job run --rm scheduler
```

Without Docker, from `backend` with the virtualenv active:

```bash
python -m app.jobs.refresh_popular
```

That job refreshes only cities marked popular. Other cities are fetched when someone searches for them, then stored for reuse.

## Live station data

Without an OpenAQ key, the app loads a **labeled sample dataset** for eight cities: New Delhi, Mumbai, Bengaluru, Kolkata, Chennai, Hyderabad, Pune, and Ahmedabad. Sample values are synthetic.

To load real monitoring data:

1. Create a key at https://explore.openaq.org/register
2. Copy `.env.example` to `.env` in the repository root
3. Set `OPENAQ_API_KEY`
4. Restart the API
5. Open a city and choose **Refresh data**, or run the popular-city job

The key stays in the backend. Do not put it in frontend code or in an image.

Weather and the air-quality forecast use Open-Meteo and do not need a key. Both are labeled as model estimates. History, comparison, and CSV export read the database and do not call OpenAQ.

## What this version does

- Search seeded cities, or any other place, which is geocoded and stored on demand
- Show PM2.5, PM10, NO2, SO2, CO, and O3 with units, source, and timestamps
- Calculate CPCB National AQI only when coverage rules pass
- Leave missing pollutants as unavailable instead of zero
- Map stations, with a filter for AQI or pollutant availability
- Filter stored history by UTC date and show hourly values or daily means
- Compare up to four stored cities
- Download stored measurements as CSV
- Show an Open-Meteo air-quality forecast in its own panel, cached until `CACHE_TTL_MINUTES`
- Record ingestion runs and expose `/api/v1/health` and `/api/v1/metrics`

Pune includes a “School Campus” station that has no particulate data, so its AQI stays unavailable. That is intentional.

## Cloud shape

Google Cloud hosts the API. Vercel hosts the website. The browser talks to Vercel, and the Next.js server calls Cloud Run. Pages opened in India therefore use Vercel’s free bandwidth. Cloud Run’s free outbound gigabyte stays on the path from Iowa to Vercel in North America.

| Concern | What is running |
| --- | --- |
| Website | Vercel project `community-air-quality`, root directory `frontend`, HTTPS |
| API compute | Cloud Run service `community-air-api` in `us-central1`. Minimum instances 0, maximum 1, 1 vCPU, 512 MiB, request-based billing |
| Image build | Cloud Build, image stored in Artifact Registry |
| Scheduled compute | Cloud Scheduler job `refresh-popular`, once a day at 02:30 Asia/Kolkata. It sends `POST /api/v1/jobs/refresh-popular` to this same API. The token is `SCHEDULER_TOKEN` in Secret Manager |
| On-demand compute | Any other city, and a popular city with no live readings yet, is fetched when its dashboard is opened |
| Database | SQLite at `/app/data/airquality.db` inside the API container. The file is created on startup and removed when the instance scales to zero |
| Cache | `measurements`, `forecasts`, and `cache_entries`. A fresh dashboard read does not call OpenAQ |
| Secrets | `openaq-api-key` and `scheduler-token` in Secret Manager. The repository only has `.env.example` |
| Monitoring | Cloud Run logs, `GET /api/v1/health`, `GET /api/v1/metrics`, and one Cloud Monitoring uptime check on `/api/v1/health` every 15 minutes |
| Delivery | GitHub Actions runs the backend tests and the frontend build. The API deploy is a `gcloud run deploy` from this repository |

The API process does not keep request state. Load balancer, NAT gateway, Cloud SQL, and a queue are not part of this deployment. The cost target is ₹0 inside the free allowances: Cloud Run’s monthly request and CPU allowance, one of the three free Cloud Scheduler jobs, six free Secret Manager versions, 0.5 GB of Artifact Registry, 1 million free uptime-check executions, and Vercel’s Hobby plan. Passing a Vercel cap pauses that feature. Passing a Google cap can bill, and the project budget alert is set at ₹0.

Cloud Run’s disk does not survive scale-to-zero. After the instance sleeps, the next visit loads the sample set and then fetches live stations again. The daily job fills the database only for the life of that instance. A separate Cloud Run job was not used, because it would write a database file the website cannot read.

## AQI rules in this version

Methodology id: `CPCB-NAQI-2014`.

- Sub-index from CPCB breakpoints, then rounded half up
- Overall AQI is the worst valid sub-index
- At least three valid pollutants, including PM2.5 or PM10
- 24-hour pollutants need at least 16 hourly values
- 8-hour CO and O3 need at least 6 hourly values
- Ozone above 208 µg/m³ on the 8-hour average uses the 1-hour value
- Severe bands use a ceiling concentration so the index can reach 500, then stay capped
- Model forecast hours are never used as that official AQI

## Project layout

```text
backend/app        FastAPI, CPCB calculation, providers, cache, scheduled job
frontend/src       Next.js dashboard
.github/workflows  test and frontend build
community_air_quality_project_documentation.md
```

The database file is created at `backend/data/airquality.db` on first launch. Delete that file to rebuild the sample dataset. New tables are created on startup; existing rows are kept.

## Community Sensor Network

The Community Sensor Network demonstrates a distributed air quality monitoring system where simulated IoT sensors post measurements to the backend and appear live on an interactive map.

**Important:** This feature uses **simulated data from virtual sensors**, not real hardware. The purpose is to demonstrate the complete device-to-application architecture.

### What it demonstrates

- **Virtual sensors:** 10 simulated IoT devices representing community-operated air quality sensors across Bengaluru neighborhoods (Koramangala, Indiranagar, HSR Layout, Whitefield, Marathahalli, Electronic City, Jayanagar, MG Road, Hebbal, Yelahanka)
- **Device authentication:** Each sensor authenticates using a Bearer token (bcrypt-hashed in the database)
- **Real-time ingestion:** Sensors POST readings every 5-10 seconds with gradually-changing PM2.5, PM10, temperature, and humidity values
- **Live dashboard:** `/community` page displays all sensors on a Leaflet map with color-coded markers (green/yellow/orange/red by PM2.5 level, grey when offline)
- **Polling updates:** Frontend polls the backend every 5 seconds for live metrics and readings
- **Sensor details:** Click any marker to view latest readings and historical PM2.5/PM10 trends (Recharts line chart)
- **Simulation scenarios:** Pollution spikes and sensor disconnects can be triggered via CLI flags

### How to seed sensors

From the `backend` directory with the virtual environment active:

```bash
cd backend
source .venv/bin/activate
python -m app.seed_community_sensors
```

This creates 10 community sensors in the database and generates authentication tokens in `backend/data/sensor_tokens.json` (gitignored).

### How to run the simulator

Start the backend API first, then run the simulator in a separate terminal:

```bash
# Terminal 1: Backend API
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Simulator
cd backend
source .venv/bin/activate
python -m app.simulator.virtual_sensors --api-url http://localhost:8000
```

The simulator will load tokens from `backend/data/sensor_tokens.json`, fetch sensor metadata, and begin submitting readings every 5-10 seconds. Press Ctrl+C to stop.

**Simulation scenarios:**

```bash
# Trigger pollution spike for SENSOR_001 (increases PM2.5 by 40-80 for 60 seconds)
python -m app.simulator.virtual_sensors --api-url http://localhost:8000 --spike SENSOR_001 --duration 60

# Disconnect a sensor (stops submissions)
python -m app.simulator.virtual_sensors --api-url http://localhost:8000 --disconnect SENSOR_003

# Reconnect a sensor (resumes submissions)
python -m app.simulator.virtual_sensors --api-url http://localhost:8000 --reconnect SENSOR_003
```

### Community sensors in the deployed demo

The Cloud Run deployment has no simulator process, and its SQLite file disappears when the instance scales to zero. The API is therefore deployed with `COMMUNITY_DEMO_MODE=true` (default `false`):

- On startup the API seeds the ten Bengaluru sensors if they are missing. Their tokens are not saved anywhere.
- When the community endpoints are read (`/community/sensors`, `/community/sensors/{id}`, `/community/sensors/{id}/readings`, `/community/map`), the API fills in one simulated reading per minute per active sensor since its last reading. A sensor's first read gets two hours of history; later reads add at most 60 rows. Values follow a smooth random walk per sensor.
- A newly registered sensor gets a random location inside Bengaluru on the next read, so it appears on the map within one 5-second poll.
- Simulated rows have `quality_status: "simulated"`. Readings posted by a device to `/community/sensors/readings` are still accepted and stored as `"accepted"`.
- All data, including registered sensors, resets when the container restarts.

Add it to the deploy command with `--set-env-vars CORS_ORIGINS=<vercel-url>,COMMUNITY_DEMO_MODE=true`, or on an existing service with `gcloud run services update community-air-api --region us-central1 --update-env-vars COMMUNITY_DEMO_MODE=true`. Leave it off locally: Docker Compose runs the real simulator.

### How to view the community page

With the backend API and simulator running, start the frontend:

```bash
cd frontend
npm run dev
```

Open http://localhost:3000/community

### What the simulation shows

- **Dashboard metrics:** Total sensors, online sensors (last seen <2 minutes ago), offline sensors, total readings
- **Interactive map:** 10 sensor markers colored by PM2.5 level:
  - Green: <30 µg/m³ (Good)
  - Yellow: 30-60 µg/m³ (Moderate)
  - Orange: 60-100 µg/m³ (Unhealthy for sensitive groups)
  - Red: >100 µg/m³ (Unhealthy)
  - Grey: Offline (no data for >2 minutes)
- **Sensor details panel:** When you click a marker, view the sensor's name, ID, coordinates, status, latest reading values (PM2.5, PM10, temperature, humidity), and timestamp
- **Historical chart:** PM2.5 and PM10 trends over the last 50 readings with time on the x-axis
- **Live updates:** Metrics, map markers, and readings refresh every 5 seconds automatically
- **Spike visualization:** When a spike is triggered, the affected sensor's marker color changes within 5-10 seconds as PM2.5 increases

The feature demonstrates how community-operated sensors could provide neighborhood-level air quality coverage beyond official monitoring stations.

## Still ahead

A database that survives scale-to-zero, without turning on Cloud SQL. GitHub Actions does not deploy the API yet. Both can wait until a free persistent disk is confirmed.
