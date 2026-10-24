# Community Air Quality & Environmental Health Dashboard

Local air-quality dashboard for a cloud computing project. People can search a city, see station readings, an Indian AQI when CPCB inputs are valid, compare cities, filter history, download a CSV, and view a model forecast that stays separate from station data.

The app is at **stage 3** locally: popular cities have a separate refresh command, and a dashboard opens stored readings until the cache window expires. Google Cloud is the selected host. It is not deployed yet. Cloud SQL stays off until its price is confirmed.

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

The same code is what a free-tier deployment would run. Only configuration changes.

| Concern | In this repo | Cloud equivalent, after a quota check |
| --- | --- | --- |
| Web compute | FastAPI and Next.js containers | Cloud Run. Google Cloud is selected and not deployed yet |
| Scheduled compute | `python -m app.jobs.refresh_popular` | A separate Cloud Run job, started by Cloud Scheduler |
| Database | SQLite file locally | PostgreSQL only if a free allowance exists |
| Cache | `measurements`, `forecasts`, `cache_entries` | Same tables. Repeat reads do not call the provider |
| Secrets | `.env`, ignored by git | Secret Manager or Secrets Manager, after checking price |
| Health | `/api/v1/health`, `/api/v1/metrics` | Uptime check and logs |
| Delivery | `.github/workflows/ci.yml` | Test on every push. Deploy is not wired yet |

The API process does not keep request state. Google Cloud is the one provider for this project. Leave the load balancer, NAT gateway, and queue out unless a later deployment actually needs one. The cost target is $0 inside verified free-tier limits, and that is a target, not a guarantee.

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

Cloud deployment itself: choose AWS or GCP after checking current free-tier rules, put the database on persistent storage, store the OpenAQ key in the provider’s secret store, run the popular-city job on a schedule, and serve the site over HTTPS. That is stage 4, and it stays inside one provider’s verified free allowance.
