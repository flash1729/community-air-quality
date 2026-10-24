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

## Still ahead

A database that survives scale-to-zero, without turning on Cloud SQL. GitHub Actions does not deploy the API yet. Both can wait until a free persistent disk is confirmed.
