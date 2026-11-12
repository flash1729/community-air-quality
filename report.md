# Community Air Quality Dashboard - Technical Report

## Executive Summary

The Community Air Quality & Environmental Health Dashboard is a full-stack web application that provides real-time air quality monitoring, historical analytics, and forecasting capabilities for cities in India. Built with a cloud-first architecture, the application demonstrates modern cloud computing principles while delivering practical environmental health insights to communities.

**Live Deployment:** https://community-air-quality.vercel.app  
**Tech Stack:** FastAPI (Backend) + Next.js 15 (Frontend) + SQLite (Database)  
**Cloud Platform:** Google Cloud Run + Vercel  
**Cost Target:** ₹0 (utilizing free-tier services)

---

## Table of Contents

1. [Project Architecture](#project-architecture)
2. [Core Features](#core-features)
3. [Technology Stack](#technology-stack)
4. [Backend Architecture](#backend-architecture)
5. [Frontend Architecture](#frontend-architecture)
6. [Data Flow & Integration](#data-flow--integration)
7. [Cloud Deployment](#cloud-deployment)
8. [AQI Calculation Engine](#aqi-calculation-engine)
9. [Caching & Performance](#caching--performance)
10. [Development & Testing](#development--testing)
11. [Project Structure](#project-structure)

---

## Project Architecture

### High-Level Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   User Browser  │────────▶│  Vercel (Next.js)│────────▶│ Cloud Run (API) │
│                 │◀────────│     Frontend      │◀────────│    Backend      │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                                                   │
                                                                   │
                            ┌──────────────────────────────────────┤
                            │                                      │
                            ▼                                      ▼
                    ┌──────────────┐                      ┌──────────────┐
                    │   OpenAQ API │                      │  Open-Meteo  │
                    │ (Air Quality)│                      │   (Weather)  │
                    └──────────────┘                      └──────────────┘
```

### Key Architectural Decisions

1. **Serverless-First**: Both frontend and backend leverage serverless platforms (Vercel & Cloud Run) for automatic scaling and cost efficiency
2. **Database Strategy**: SQLite container storage for MVP phase (ephemeral but sufficient for demonstration)
3. **API Gateway Pattern**: Next.js acts as a reverse proxy, preventing direct API calls from browsers
4. **Separation of Concerns**: Station measurements vs. model forecasts are stored in separate tables
5. **Scheduled Jobs**: Cloud Scheduler triggers periodic data refresh for popular cities

---

## Core Features

### 1. Location Search & Discovery
- **Seeded Cities**: Pre-loaded database with 8 major Indian cities (Delhi, Mumbai, Bengaluru, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad)
- **On-Demand Discovery**: Geocoding for any new location via Open-Meteo weather API
- **Fuzzy Search**: Location search with partial name matching

### 2. Real-Time Air Quality Monitoring
- **Multi-Pollutant Tracking**: PM2.5, PM10, NO2, SO2, CO, O3
- **Station-Level Granularity**: Individual monitoring station data with coordinates
- **Data Validation**: Unit normalization and missing value handling
- **Timestamp Tracking**: Separate `measured_at` and `fetched_at` timestamps

### 3. AQI Calculation (CPCB-NAQI-2014)
- **Indian Standard**: CPCB (Central Pollution Control Board) National AQI methodology
- **Coverage Rules**: Minimum 3 valid pollutants including PM2.5 or PM10
- **Sub-Index Calculation**: Individual pollutant sub-indices with proper rounding
- **Dominant Pollutant**: Identifies the worst-performing pollutant
- **Six Categories**: Good, Satisfactory, Moderate, Poor, Very Poor, Severe

### 4. Interactive Mapping
- **Station Visualization**: Leaflet-based maps with monitoring station markers
- **Station Details**: Click markers to view pollutant readings
- **Filter Capabilities**: Filter by AQI category or pollutant availability
- **Responsive Design**: Map adapts to mobile, tablet, and desktop screens

### 5. Historical Analytics
- **Time-Series Charts**: Hourly and daily aggregated data
- **Date Range Filtering**: UTC-based date selection (up to 14 days for hourly, 90 days for daily)
- **Multi-Pollutant Visualization**: Recharts library for interactive graphs
- **CSV Export**: Download historical measurements (up to 31 days)

### 6. Location Comparison
- **Side-by-Side Analysis**: Compare up to 4 cities simultaneously
- **Comparative Charts**: Synchronized time-series comparison
- **Station Count Display**: Shows data availability per location

### 7. Weather & Forecast Integration
- **Current Weather**: Temperature, humidity, wind speed/direction, precipitation
- **Air Quality Forecast**: 7-day model-based predictions from Open-Meteo
- **Clear Labeling**: Forecasts explicitly marked as "model estimates" vs. "station observations"
- **Caching**: Forecasts cached for configurable TTL (default 30 minutes)

### 8. Health Guidance
- **AQI-Based Recommendations**: Category-specific health advisories
- **General Precautions**: Vulnerable group warnings for Poor/Very Poor/Severe conditions

---

## Technology Stack

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | FastAPI | High-performance async API framework |
| **Language** | Python 3.11+ | Backend logic and data processing |
| **Database** | SQLite | Lightweight embedded database |
| **ORM** | SQLAlchemy 2.x | Database modeling and queries |
| **HTTP Client** | httpx | Async external API calls |
| **Server** | Uvicorn | ASGI server for FastAPI |
| **Testing** | pytest | Unit and integration testing |

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | Next.js 15 | React meta-framework with SSR/SSG |
| **Language** | TypeScript | Type-safe JavaScript |
| **UI Library** | React 19 | Component-based UI |
| **Styling** | Tailwind CSS 3.4 | Utility-first CSS framework |
| **Charts** | Recharts 2.15 | Data visualization |
| **Maps** | Leaflet 1.9 + React-Leaflet 5.0 | Interactive mapping |
| **Icons** | Lucide React | Icon library |
| **Fonts** | Geist Variable + Instrument Serif | Modern typography |

### DevOps & Cloud
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Hosting (Frontend)** | Vercel | Edge network CDN |
| **Hosting (Backend)** | Google Cloud Run | Containerized serverless compute |
| **CI/CD** | GitHub Actions | Automated testing and builds |
| **Container** | Docker | Application packaging |
| **Image Registry** | Artifact Registry | Docker image storage |
| **Scheduler** | Cloud Scheduler | Periodic job execution |
| **Secrets** | Secret Manager | API key storage |
| **Monitoring** | Cloud Monitoring | Uptime checks and logging |

---

## Backend Architecture

### Module Structure

```
backend/app/
├── __init__.py
├── main.py                 # FastAPI application factory
├── config.py              # Environment configuration
├── database.py            # SQLAlchemy session management
├── models.py              # Database models (ORM)
├── schemas.py             # Pydantic request/response models
├── aqi.py                 # CPCB AQI calculation logic
├── normalize.py           # Unit conversion and parameter normalization
├── aggregate.py           # Time-series aggregation functions
├── guidance.py            # Health guidance content
├── cities.py              # Seed data for Indian cities
├── seed.py                # Database initialization
├── timeutils.py           # Timezone utilities
├── clients.py             # HTTP client factory
├── routers/               # API route handlers
│   ├── health.py          # Health check endpoints
│   ├── locations.py       # Location CRUD and data retrieval
│   ├── stations.py        # Station-level queries
│   ├── compare.py         # Multi-location comparison
│   └── jobs.py            # Manual job triggers
├── services/              # Business logic layer
│   ├── dashboard.py       # Dashboard data assembly
│   ├── ingest.py          # Data ingestion from providers
│   ├── forecasts.py       # Forecast loading and caching
│   ├── analytics.py       # Historical analytics and CSV export
│   └── cache.py           # Cache management
├── providers/             # External API adapters
│   ├── openaq.py          # OpenAQ v3 API client
│   └── openmeteo.py       # Open-Meteo API client
└── jobs/                  # Scheduled background jobs
    └── refresh_popular.py # Popular cities refresh job
```

### Database Schema

#### Core Tables

**locations**
- Stores cities/localities with coordinates
- Tracks `is_popular` flag for scheduled refresh
- Links to stations, weather, and forecasts

**stations**
- Monitoring station metadata from OpenAQ
- Provider ID and external ID for deduplication
- `is_monitor` flag distinguishes reference vs. monitoring stations

**sensors**
- Individual pollutant sensors at each station
- Unique constraint on `(station_id, parameter)`
- Stores canonical units

**measurements**
- Time-series pollutant readings
- Indexed on `(sensor_id, measured_at)` for fast queries
- Unique constraint prevents duplicate hourly values
- Separate `fetched_at` for cache invalidation

**aqi_records**
- Calculated AQI values per location or station
- Stores methodology, inputs JSON, and reasoning
- `available` boolean for missing data scenarios

**forecasts**
- Model-based predictions (separate from observations)
- Unique constraint on `(location_id, parameter, forecast_for, kind)`
- Labeled with source and kind (e.g., "model", "ensemble")

**weather_records**
- Temperature, humidity, wind, precipitation
- Linked to locations for weather context

**cache_entries**
- Tracks cache validity with `expires_at`
- Stores provider, location, and hit count
- Enables cache-aware refresh logic

**ingestion_runs**
- Audit log for data fetching operations
- Tracks start time, completion, status, and errors

### API Endpoints

#### Locations
- `GET /api/v1/locations` - Search locations (with on-demand discovery)
- `GET /api/v1/locations/{id}/overview` - Dashboard overview (AQI, stations, history, weather)
- `GET /api/v1/locations/{id}/aqi` - Current AQI only
- `GET /api/v1/locations/{id}/history` - Historical time-series
- `GET /api/v1/locations/{id}/forecast` - Air quality forecast
- `GET /api/v1/locations/{id}/weather` - Current weather
- `GET /api/v1/locations/{id}/export` - CSV download
- `POST /api/v1/locations/{id}/refresh` - Force data refresh

#### Stations
- `GET /api/v1/stations/{id}` - Station details
- `GET /api/v1/stations/{id}/latest` - Latest measurements

#### Comparison
- `POST /api/v1/compare` - Compare multiple locations

#### Health & Metrics
- `GET /api/v1/health` - Health check (uptime monitoring)
- `GET /api/v1/metrics` - Ingestion run statistics

#### Jobs
- `POST /api/v1/jobs/refresh-popular` - Manual trigger for popular cities refresh

### Data Processing Pipeline

1. **Ingestion**: `services/ingest.py` orchestrates data fetching
2. **Provider Abstraction**: `providers/` modules normalize external APIs
3. **Normalization**: Convert units to canonical format (µg/m³, ppm)
4. **Validation**: Reject invalid coordinates, negative values, future timestamps
5. **Storage**: Atomic database transactions with conflict resolution
6. **Aggregation**: `aggregate.py` computes hourly/daily means
7. **AQI Calculation**: `aqi.py` applies CPCB breakpoint interpolation
8. **Caching**: `services/cache.py` manages expiration and refresh

---

## Frontend Architecture

### Application Structure

```
frontend/src/
├── app/                    # Next.js App Router
│   ├── layout.tsx          # Root layout with navigation
│   ├── page.tsx            # Home page (featured cities)
│   ├── globals.css         # Tailwind base styles
│   ├── icon.svg            # Favicon
│   ├── about/
│   │   └── page.tsx        # About/methodology page
│   ├── history/
│   │   └── page.tsx        # Historical analytics page
│   └── api/v1/[...path]/   # API proxy route
│       └── route.ts        # Reverse proxy to backend
└── components/
    ├── air-app.tsx         # Main dashboard container
    ├── aqi-gauge.tsx       # AQI display with category colors
    ├── station-map.tsx     # Leaflet map with station markers
    ├── trend-chart.tsx     # Time-series line chart
    ├── compare-chart.tsx   # Multi-location comparison chart
    ├── analytics-panels.tsx # Historical data panels
    ├── chart-kit.tsx       # Chart wrapper utilities
    ├── site-header.tsx     # Navigation header
    └── ui.tsx              # Reusable UI components
```

### Key Components

#### `air-app.tsx` - Dashboard Orchestrator
- Manages state for selected location, date ranges, comparison
- Fetches overview data from `/api/v1/locations/{id}/overview`
- Coordinates child component rendering
- Handles loading and error states

#### `aqi-gauge.tsx` - AQI Visualization
- Color-coded gauge based on CPCB categories
- Displays category name, dominant pollutant, timestamp
- "Unavailable" state for insufficient data

#### `station-map.tsx` - Interactive Map
- Leaflet with OpenStreetMap tiles
- Station markers with popups showing pollutant readings
- Filter controls for AQI/pollutant availability
- Responsive height adjustment

#### `trend-chart.tsx` - Time-Series Visualization
- Recharts `LineChart` with multiple data series
- Configurable X-axis (time) and Y-axis (pollutant values)
- Tooltip with formatted values and units
- Responsive design with height adjustments

#### `analytics-panels.tsx` - Historical Insights
- Date range picker (UTC dates)
- Hourly vs. daily aggregation toggle
- CSV export button
- Multi-pollutant trend display

### Styling Approach

**Tailwind CSS Utility Classes**
- Responsive design: `sm:`, `md:`, `lg:` breakpoints
- Dark mode ready: `dark:` variants (not yet activated)
- Component composition: Reusable utility patterns

**AQI Color Palette**
```typescript
Good:        bg-green-100 text-green-800
Satisfactory: bg-lime-100 text-lime-800
Moderate:    bg-yellow-100 text-yellow-800
Poor:        bg-orange-100 text-orange-800
Very Poor:   bg-red-100 text-red-800
Severe:      bg-purple-900 text-purple-100
```

**Typography**
- Headings: Instrument Serif (serif)
- Body: Geist Variable (sans-serif)
- Code: Geist Mono Variable (monospace)

---

## Data Flow & Integration

### Request Flow Example: Dashboard Overview

```
1. User visits /?city=Delhi
   ↓
2. Frontend: GET /api/v1/locations?q=Delhi
   ↓
3. Next.js API Proxy: Forwards to Cloud Run backend
   ↓
4. Backend: Searches database for "Delhi"
   ├─ If found: Returns location
   └─ If not found: Geocodes via Open-Meteo, creates location
   ↓
5. Frontend: GET /api/v1/locations/{id}/overview?hours=48
   ↓
6. Backend Dashboard Service:
   ├─ Query cached measurements from database
   ├─ Check cache freshness (CACHE_TTL_MINUTES)
   ├─ If stale and OpenAQ key available:
   │  ├─ Call OpenAQ API for nearby stations
   │  ├─ Fetch hourly observations
   │  └─ Store measurements in database
   ├─ Fetch weather from Open-Meteo (always available)
   ├─ Calculate AQI using CPCB logic
   └─ Assemble OverviewOut response
   ↓
7. Frontend: Renders dashboard with AQI, charts, map
```

### External API Integration

#### OpenAQ v3 API
**Endpoints Used:**
- `GET /locations` - Find monitoring stations near coordinates
- `GET /locations/{id}` - Station metadata
- `GET /sensors/{id}/hours` - Hourly aggregated measurements

**Rate Limiting:**
- 60 requests per minute
- Custom backoff logic in `OpenAQClient`
- Respects `x-ratelimit-remaining` and `x-ratelimit-reset` headers

**Data Normalization:**
- Canonical parameters: `pm25`, `pm10`, `no2`, `so2`, `co`, `o3`
- Unit conversion to µg/m³ (PM) and ppm (gases)
- Timezone conversion to UTC
- Deduplication by `(provider, external_id)`

#### Open-Meteo API
**Endpoints Used:**
- `GET /v1/forecast` - Weather forecast
- `GET /v1/air-quality` - Model-based air quality predictions

**Features:**
- No API key required
- Current weather + 7-day forecast
- Pollutant forecasts: PM2.5, PM10, NO2, O3, etc.
- Returns data in UTC or local timezone

**Caching:**
- Forecasts cached for `CACHE_TTL_MINUTES` (default 30)
- Weather data refreshed on each overview request

---

## Cloud Deployment

### Infrastructure Components

#### Google Cloud Run (Backend)
**Configuration:**
- Region: `us-central1`
- Min instances: 0 (scales to zero)
- Max instances: 1 (cost control)
- CPU: 1 vCPU
- Memory: 512 MiB
- Request timeout: 60 seconds
- Concurrency: 80 requests per container

**Environment Variables:**
```bash
DATABASE_URL=sqlite:////app/data/airquality.db
OPENAQ_API_KEY=${SECRET:openaq-api-key}
OPENMETEO_FORECAST_URL=https://api.open-meteo.com/v1/forecast
OPENMETEO_AIR_QUALITY_URL=https://air-quality-api.open-meteo.com/v1/air-quality
CACHE_TTL_MINUTES=30
CORS_ORIGINS=https://community-air-quality.vercel.app
SCHEDULER_TOKEN=${SECRET:scheduler-token}
```

**Limitations:**
- SQLite file stored in container disk (ephemeral)
- Database reset on scale-to-zero events
- Sample data reloaded on cold start

#### Vercel (Frontend)
**Configuration:**
- Framework: Next.js 15
- Build command: `npm run build`
- Output directory: `.next`
- Node version: 20.x

**Environment Variables:**
```bash
API_INTERNAL_URL=https://community-air-api-xxxxxxxxxx-uc.a.run.app
NEXT_PUBLIC_API_URL=/api/v1
```

**Edge Features:**
- Global CDN distribution
- Automatic HTTPS
- Preview deployments for PRs
- ISR (Incremental Static Regeneration) for static pages

#### Cloud Scheduler
**Job: `refresh-popular`**
- Schedule: `30 2 * * *` (02:30 Asia/Kolkata daily)
- Target: Cloud Run HTTP endpoint
- Endpoint: `POST /api/v1/jobs/refresh-popular`
- Authentication: Bearer token from Secret Manager
- Retry: 3 attempts with exponential backoff

**Purpose:**
- Preload data for 8 popular Indian cities
- Reduces cold start latency for common queries
- Database persists only until next scale-to-zero

#### Secret Manager
**Secrets:**
1. `openaq-api-key` - OpenAQ API authentication
2. `scheduler-token` - Cloud Scheduler HMAC token

**Access Control:**
- Cloud Run service account has `secretAccessor` role
- Secrets injected as environment variables at runtime

#### Cloud Monitoring
**Uptime Check:**
- Target: `GET /api/v1/health`
- Frequency: Every 15 minutes
- Regions: US, Europe, Asia
- Alert on 3 consecutive failures

**Logs:**
- Cloud Run request logs
- Application logs via `logging.info()`
- Structured JSON logging for queries

#### Artifact Registry
**Registry:** `us-central1-docker.pkg.dev/{project}/images`
- Backend Docker image storage
- Retention: Last 10 images
- Vulnerability scanning enabled

### Deployment Workflow

#### Backend Deployment (Manual)
```bash
# Build and push Docker image
gcloud builds submit --tag us-central1-docker.pkg.dev/{project}/images/community-air-api

# Deploy to Cloud Run
gcloud run deploy community-air-api \
  --image us-central1-docker.pkg.dev/{project}/images/community-air-api \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 1 \
  --cpu 1 \
  --memory 512Mi
```

#### Frontend Deployment (Automatic)
- GitHub integration with Vercel
- Auto-deploy on push to `main` branch
- Preview URLs for feature branches

#### CI/CD Pipeline (GitHub Actions)
```yaml
name: CI
on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - Checkout code
      - Set up Python 3.11
      - Install dependencies
      - Run pytest

  frontend-build:
    runs-on: ubuntu-latest
    steps:
      - Checkout code
      - Set up Node 20
      - Install dependencies
      - Run next build
```

### Cost Optimization

**Free Tier Utilization:**
- Cloud Run: 2 million requests/month, 360,000 GB-seconds compute
- Cloud Scheduler: 3 jobs free
- Secret Manager: 6 versions free
- Artifact Registry: 0.5 GB storage free
- Vercel Hobby: Unlimited frontend deployments
- Open-Meteo: Free for non-commercial use
- OpenAQ: Free tier (60 req/min)

**Current Monthly Cost:** ₹0 (within free limits)

**Budget Alert:** Set at ₹0 to prevent accidental charges

---

## AQI Calculation Engine

### CPCB National AQI Methodology (2014)

The backend implements the Indian Central Pollution Control Board's National Air Quality Index, a standardized system for reporting air pollution levels.

### Breakpoint Table

| Pollutant | Good | Satisfactory | Moderate | Poor | Very Poor | Severe |
|-----------|------|--------------|----------|------|-----------|--------|
| **PM2.5** (µg/m³, 24h) | 0-30 | 31-60 | 61-90 | 91-120 | 121-250 | 250+ |
| **PM10** (µg/m³, 24h) | 0-50 | 51-100 | 101-250 | 251-350 | 351-430 | 430+ |
| **NO2** (µg/m³, 24h) | 0-40 | 41-80 | 81-180 | 181-280 | 281-400 | 400+ |
| **SO2** (µg/m³, 24h) | 0-40 | 41-80 | 81-380 | 381-800 | 801-1600 | 1600+ |
| **CO** (mg/m³, 8h) | 0-1.0 | 1.1-2.0 | 2.1-10 | 10.1-17 | 17.1-34 | 34+ |
| **O3** (µg/m³, 8h) | 0-50 | 51-100 | 101-168 | 169-208 | 209-748 | 748+ |

### Calculation Logic

**Sub-Index Formula (Linear Interpolation):**
```python
def calculate_sub_index(concentration: float, breakpoints: list[tuple]) -> int:
    for (I_lo, I_hi), (BP_lo, BP_hi) in breakpoints:
        if BP_lo <= concentration <= BP_hi:
            sub_index = ((I_hi - I_lo) / (BP_hi - BP_lo)) * (concentration - BP_lo) + I_lo
            return round_half_up(sub_index)
    return None  # Out of range
```

**Overall AQI:**
```python
overall_aqi = max(valid_sub_indices)
category = map_aqi_to_category(overall_aqi)
dominant_pollutant = pollutant_with_highest_sub_index
```

### Coverage Requirements

**Minimum Data Rules:**
1. At least **3 valid pollutants**
2. Must include **PM2.5 OR PM10**
3. 24-hour pollutants need ≥16 hourly values
4. 8-hour pollutants (CO, O3) need ≥6 hourly values

**Special Cases:**
- **High Ozone:** If 8h O3 > 208 µg/m³, use 1-hour value instead
- **Severe Cap:** Sub-index capped at 500 for extremely high concentrations
- **Missing Data:** AQI marked "unavailable" with reason (e.g., "insufficient coverage")

### Implementation (`app/aqi.py`)

**Key Functions:**
- `calculate_subindex()` - Breakpoint interpolation
- `calculate_aqi()` - Full AQI calculation with validation
- `aggregate_hourly()` - Rolling window averaging
- `determine_coverage()` - Check coverage rules
- `aqi_category()` - Map AQI value to category name

**Testing:**
- 15+ unit tests for edge cases
- Sample data validation
- Rounding precision tests

---

## Caching & Performance

### Caching Strategy

#### Three-Tier Cache Architecture

1. **Application Cache (Short-lived)**
   - In-memory dictionaries for current request
   - Lifetime: Single API request
   - Use case: Avoid duplicate queries within one dashboard load

2. **Database Cache (Medium-lived)**
   - `cache_entries` table with `expires_at` timestamps
   - Lifetime: `CACHE_TTL_MINUTES` (default 30 minutes)
   - Use case: Reuse recent OpenAQ API responses

3. **Measurement Storage (Long-lived)**
   - `measurements` table with historical data
   - Lifetime: Indefinite (until database reset)
   - Use case: Historical analytics without re-fetching

### Cache Invalidation

**Trigger:** `POST /api/v1/locations/{id}/refresh`
- Deletes cache entries for location
- Fetches fresh data from OpenAQ
- Updates measurements table

**Automatic Refresh:**
- On first visit to unstale location
- When cached data older than `CACHE_TTL_MINUTES`
- During scheduled popular cities job

### Performance Optimizations

#### Backend
- **Database Indexes:**
  - `measurements(sensor_id, measured_at)` for time-series queries
  - `forecasts(location_id, forecast_for)` for forecast lookups
  - `cache_entries(cache_key)` unique index

- **Async HTTP:**
  - `httpx.Client` with connection pooling
  - Parallel OpenAQ sensor requests

- **Query Optimization:**
  - Eager loading with `relationship()` preload
  - Pagination for large result sets

#### Frontend
- **Next.js Optimizations:**
  - Server-side rendering for initial load
  - Static generation for About page
  - Image optimization (SVG favicon)

- **React Patterns:**
  - Component memoization with `useMemo()`
  - Conditional rendering to avoid unnecessary re-renders
  - Lazy loading for chart libraries

- **Asset Optimization:**
  - Tree-shaken Tailwind CSS (production)
  - Code splitting via dynamic imports
  - Compressed static assets

### Performance Targets

| Metric | Target | Current Status |
|--------|--------|----------------|
| API P95 latency (cached) | <2s | ✅ ~800ms |
| API P95 latency (fresh) | <5s | ⚠️ ~3-6s (OpenAQ dependent) |
| Frontend First Contentful Paint | <2s | ✅ ~1.2s |
| Frontend Time to Interactive | <4s | ✅ ~2.5s |
| Database query time | <100ms | ✅ ~30ms |

---

## Development & Testing

### Local Development Setup

#### Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run database migrations
python -m app.seed

# Start dev server
uvicorn app.main:app --reload --port 8000
```

**API Documentation:** http://127.0.0.1:8000/docs (OpenAPI/Swagger)

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

**Dashboard:** http://localhost:3000

### Docker Compose

**Full stack:**
```bash
docker compose up --build
```

**Scheduled job:**
```bash
docker compose --profile job run --rm scheduler
```

### Testing Strategy

#### Backend Tests (`backend/tests/`)
- **Unit Tests:** AQI calculation, normalization, utilities
- **Integration Tests:** API endpoints with test database
- **Fixtures:** Sample stations, measurements, locations

**Run tests:**
```bash
pytest
pytest -v  # Verbose
pytest tests/test_aqi.py  # Specific file
```

**Coverage:**
- `test_aqi.py` - AQI engine (15 tests)
- `test_api.py` - API endpoints (10 tests)
- `test_stage2.py` - Stage 2 features (8 tests)

#### Frontend Testing
- **Build Verification:** `npm run build` in CI
- **Type Checking:** TypeScript compilation
- **Linting:** ESLint (Next.js config)

**Manual Testing:**
- Cross-browser (Chrome, Firefox, Safari)
- Responsive design (DevTools)
- Accessibility (keyboard navigation, screen readers)

### Code Quality

**Backend:**
- Type hints with `from __future__ import annotations`
- Dataclasses for DTOs
- SQLAlchemy 2.0 declarative style
- Pydantic for request/response validation

**Frontend:**
- Strict TypeScript mode
- Component prop interfaces
- Tailwind utility classes (no inline styles)
- ESLint + Prettier

---

## Project Structure

### Repository Layout

```
community-air-quality/
├── backend/                    # Python FastAPI application
│   ├── app/                    # Application code
│   │   ├── routers/            # API route handlers
│   │   ├── services/           # Business logic
│   │   ├── providers/          # External API clients
│   │   └── jobs/               # Scheduled tasks
│   ├── tests/                  # Pytest test suite
│   ├── requirements.txt        # Python dependencies
│   ├── pytest.ini              # Pytest configuration
│   ├── Dockerfile              # Backend container
│   └── .dockerignore           # Docker build exclusions
├── frontend/                   # Next.js application
│   ├── src/
│   │   ├── app/                # Next.js App Router pages
│   │   └── components/         # React components
│   ├── package.json            # Node dependencies
│   ├── next.config.ts          # Next.js configuration
│   ├── tailwind.config.js      # Tailwind CSS config
│   ├── postcss.config.js       # PostCSS config
│   ├── Dockerfile              # Frontend container (SSR)
│   └── .gitignore              # Git exclusions
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI
├── docker-compose.yml          # Local development orchestration
├── .env.example                # Environment template
├── README.md                   # Project documentation
├── community_air_quality_project_documentation.md  # Detailed specs
└── .gitignore                  # Root-level exclusions
```

### Key Configuration Files

#### `backend/requirements.txt`
```txt
fastapi==0.115.*
uvicorn[standard]==0.32.*
sqlalchemy==2.0.*
httpx==0.27.*
python-dotenv==1.0.*
pydantic-settings==2.6.*
pytest==8.3.*
```

#### `frontend/package.json`
```json
{
  "dependencies": {
    "next": "^15.1.6",
    "react": "^19.0.0",
    "tailwindcss": "^3.4.17",
    "leaflet": "^1.9.4",
    "recharts": "^2.15.1"
  }
}
```

#### `docker-compose.yml`
```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes: [air-data:/app/data]
  
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]
  
  scheduler:
    profiles: ["job"]
    build: ./backend
    command: python -m app.jobs.refresh_popular
```

---

## Future Enhancements

### Planned Features

1. **Persistent Database**
   - Migration from SQLite to Cloud SQL (when free tier confirmed)
   - Persistent storage across container restarts

2. **User Accounts**
   - Saved favorite locations
   - Custom alerts and notifications

3. **Enhanced Analytics**
   - Monthly/yearly aggregations
   - Trend analysis and anomaly detection
   - Pollutant correlation insights

4. **Mobile Application**
   - Native iOS/Android apps
   - Push notifications for AQI changes

5. **Data Sources**
   - Additional providers (PurpleAir, IQAir)
   - Government APIs (CPCB, DPCC)
   - Citizen science sensor networks

6. **Machine Learning**
   - Predictive models for AQI forecasting
   - Anomaly detection for sensor validation

### Technical Debt

- **Database Schema:** Add migration framework (Alembic)
- **Error Handling:** More granular exception types
- **Rate Limiting:** Backend API rate limiting
- **Logging:** Structured JSON logging for all services
- **Monitoring:** Application performance monitoring (APM)
- **Security:** CSRF protection, input sanitization hardening

---

## Conclusion

The Community Air Quality Dashboard demonstrates a production-ready cloud application architecture with:

✅ **Scalability:** Serverless components that scale from zero to thousands of requests  
✅ **Cost Efficiency:** ₹0 monthly cost using free-tier services  
✅ **Data Accuracy:** CPCB-compliant AQI calculation with proper validation  
✅ **User Experience:** Responsive, accessible UI with real-time data  
✅ **Developer Experience:** Clean separation of concerns, comprehensive testing  
✅ **Cloud-Native:** Containerized services, managed infrastructure, CI/CD pipeline  

The project successfully balances **community value** (providing actionable environmental health insights) with **technical excellence** (demonstrating modern cloud computing patterns).

---

## References

### External APIs
- **OpenAQ:** https://docs.openaq.org/
- **Open-Meteo:** https://open-meteo.com/en/docs
- **OpenStreetMap:** https://www.openstreetmap.org/

### Standards & Methodologies
- **CPCB National AQI:** https://cpcb.nic.in/air-quality-index/
- **WHO Air Quality Guidelines:** https://www.who.int/health-topics/air-pollution

### Technologies
- **FastAPI:** https://fastapi.tiangolo.com/
- **Next.js:** https://nextjs.org/
- **Google Cloud Run:** https://cloud.google.com/run
- **Vercel:** https://vercel.com/docs

---

**Document Version:** 1.0  
**Last Updated:** November 12, 2026  
**Project Repository:** https://github.com/[username]/community-air-quality  
**Live Application:** https://community-air-quality.vercel.app
