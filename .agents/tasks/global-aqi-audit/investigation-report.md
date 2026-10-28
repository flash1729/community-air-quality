# Global AQI Support - Codebase Investigation Report

**Date:** Investigation conducted on worktree at `/home/vishwas/Desktop/CC/community-air-quality/.worktrees/global-aqi`  
**Scope:** Comprehensive audit of existing implementation to support global AQI methodology extension

---

## Executive Summary

The application is a **local Indian air-quality dashboard** currently implementing only **CPCB National AQI (2014)**. Location search is **already global** via Open-Meteo geocoding, but the AQI calculation, data providers, database schema, and frontend are all **tightly coupled to CPCB methodology** with no support for other standards.

### Key Findings

1. **Location search is already global** — Open-Meteo geocoding supports worldwide cities with no India-only restrictions
2. **AQI calculation is CPCB-only** — hardcoded to Indian methodology with no abstraction layer for other standards
3. **Database schema lacks methodology discrimination** — no columns to store which AQI standard was used or whether data came from observations vs. models
4. **Frontend hardcodes CPCB categories** — color scheme, category names, and breakpoints are fixed to Indian AQI
5. **OpenAQ provider has India-first fallback** — explicitly tries `iso=IN` first, then falls back to global search
6. **Open-Meteo does not expose pre-calculated AQI** — only raw pollutant model data; task requirements to use "us_aqi/european_aqi variables" cannot be satisfied with current API

---

## 1. AQI Calculation (CPCB-only)

**File:** `backend/app/aqi.py`

### Current Implementation

- **Methodology:** CPCB National AQI (2014) — segmented linear sub-indices
- **Version constant:** `METHODOLOGY_VERSION = "CPCB-NAQI-2014"` (line 17)
- **Overall AQI:** Maximum of all valid sub-indices (line 168-175)
- **Minimum requirements:** 3 valid pollutants, including PM2.5 or PM10 (lines 18-20, 154-164)
- **Coverage rules:**
  - 24-hour pollutants (PM2.5, PM10, NO2, SO2, NH3, Pb): minimum 16 hours (line 19, 123-124)
  - 8-hour CO: minimum 6 hours (line 20, 125-126)
  - 8-hour O3: minimum 6 hours; uses 1-hour if > 208 µg/m³ (lines 127-129)

### Breakpoints (lines 29-86)

All breakpoints are CPCB-specific with 6 bands: Good (0-50), Satisfactory (51-100), Moderate (101-200), Poor (201-300), Very Poor (301-400), Severe (401-500).

**Examples:**
- PM2.5: `(0,30,0,50), (31,60,51,100), (61,90,101,200), (91,120,201,300), (121,250,301,400), (251,380,401,500)`
- PM10: `(0,50,0,50), (51,100,51,100), (101,250,101,200), (251,350,201,300), (351,430,301,400), (431,510,401,500)`
- CO in mg/m³: `(0,1.0,0,50), (1.1,2.0,51,100), (2.1,10,101,200), (10.1,17,201,300), (17.1,34,301,400), (34.1,50,401,500)`

### Categories (line 108-116)

```python
CATEGORIES: list[tuple[int, int, str]] = [
    (0, 50, "Good"),
    (51, 100, "Satisfactory"),
    (101, 200, "Moderate"),
    (201, 300, "Poor"),
    (301, 400, "Very Poor"),
    (401, 500, "Severe"),
]
```

### Calculation Flow

1. **Input:** `list[PollutantAverage]` with parameter, concentration, averaging_period, coverage_hours (lines 133-140)
2. **Validation:** Each pollutant checks period validity via `_period_is_valid()` (lines 142-151)
3. **Truncation:** Concentrations truncated before lookup — integers for most, 1 decimal for CO/Pb (lines 96-99)
4. **Sub-index calculation:** Linear interpolation within breakpoint bands, rounded half-up (lines 101-122)
5. **Result:** `AQIResult` dataclass (lines 153-179) with `available`, `aqi`, `category`, `dominant_pollutants`, `sub_indices`, `reason`, `methodology`

### What Must Change

- **No abstraction:** All logic is in one file with no interface for alternative methodologies
- **Hardcoded rules:** Category names, breakpoint tables, coverage minimums, and rounding are CPCB-specific
- **Single methodology:** No resolver to select standard based on location country
- **No versioning beyond constant:** The methodology version is stored but never checked at runtime

**Preservation requirements:**
- Existing CPCB calculation must produce identical results for Indian cities
- Test cases in `backend/tests/test_aqi.py` (lines 11-136) validate CPCB breakpoints and must continue passing

---

## 2. Location Search (Already Global)

**Files:**
- `backend/app/cities.py` — hardcoded popular Indian cities
- `backend/app/routers/locations.py` — search and geocoding endpoints
- `backend/app/services/dashboard.py` — location discovery and selection
- `backend/app/providers/openmeteo.py` — geocoding client

### Current Implementation

**Popular cities** (`backend/app/cities.py`, lines 6-90):
- 8 Indian cities: New Delhi, Mumbai, Bengaluru, Kolkata, Chennai, Hyderabad, Pune, Ahmedabad
- Each with name, city, country ("India"), lat/lon, timezone ("Asia/Kolkata"), and sample stations
- Comment (line 3): "Stage 3 will refresh only this list on a schedule. Other places stay on demand."

**Search flow** (`backend/app/routers/locations.py`, lines 29-47):
1. Query local database (all locations, case-insensitive LIKE on name/city)
2. If empty and query exists, call `discover_location()` which geocodes via Open-Meteo
3. Store new location with `is_popular=False`
4. Return `LocationSearchOut` with results

**Geocoding** (`backend/app/providers/openmeteo.py`, lines 68-85):
- Open-Meteo geocoding API: `https://geocoding-api.open-meteo.com/v1/search`
- Parameters: `name`, `count=5`, `language=en`, `format=json`
- Returns: `Place` dataclass with name, country, country_code, latitude, longitude, timezone
- **No India restrictions in geocoding itself**

**Location selection** (`backend/app/services/dashboard.py`, lines 54-75):
- `discover_location()`: geocodes query, chooses best match via `_choose_place()` (lines 77-86)
- **India preference** (line 84): `india = [place for place in matches if place.country_code == "IN"]`
- If India match exists, prefer it; otherwise use first match
- Check for duplicate locations at same coordinates and reuse existing

### India-Only Restrictions

**None in geocoding**, but:
1. **Popular cities list is India-only** (line 6-90 in `backend/app/cities.py`)
2. **Preference for Indian matches** when multiple results exist (`backend/app/services/dashboard.py:84`)
3. **Timezone defaults to Asia/Kolkata** in `backend/app/models.py:25`

### What Must Change

- **Remove or document India preference** in place selection logic
- **Popular cities should remain Indian** (requirement: "Preserve the existing seeded Indian cities")
- **No changes needed to geocoding client** — already supports global search

---

## 3. Data Providers

### 3.1 OpenAQ Provider

**File:** `backend/app/providers/openaq.py`

**Purpose:** Real monitoring station observations worldwide

**Configuration:**
- API base: configurable (default: `https://api.openaq.org/v3`)
- API key required (free tier: 60 requests/minute)
- Rate limiting: tracked via headers, 60-second sleep on exhaustion (lines 38-48)

**Station search** (`nearby_stations()`, lines 68-105):
- Endpoint: `GET /locations`
- **India-first behavior** (lines 74-84):
  ```python
  payload = self._get("/locations", {
      "coordinates": f"{latitude:.4f},{longitude:.4f}",
      "radius": 25000,
      "limit": 100,
      "page": 1,
      "iso": "IN",  # <-- India-only search first
  })
  results = payload.get("results") or []
  if not results:
      # Falls back to global search without "iso" parameter
      payload = self._get(..., {..., no iso})
  ```
- Filters: exclude mobile stations, only stations with recent data (within `RECENT_DAYS=14`)
- Ranking: prefer `isMonitor=True`, then most recent reporting time
- Returns: `RemoteStation` with `external_id`, `name`, `latitude`, `longitude`, `is_monitor`, `sensors`

**Tracked parameters** (line 14): `pm25`, `pm10`, `no2`, `so2`, `co`, `o3` (no NH3 or Pb)

**Hourly observations** (`hourly_observations()`, lines 107-122):
- Endpoint: `GET /sensors/{sensor_id}/hours`
- Parameters: `datetime_from`, `datetime_to` (UTC ISO format), `limit=200`, `page=1`
- Parsing: extracts value, unit, timestamp from nested JSON (lines 150-183)
- Unit conversion: via `normalize.py` — ppm to µg/m³, mg/m³ for CO (lines 180-183)
- Returns: `HourlyObservation` with `sensor_external_id`, `parameter`, `value`, `unit`, `measured_at`

**Unit handling** (`backend/app/normalize.py`, lines 62-103):
- CO: accepts mg/m³, µg/m³, ppm, ppb → converts to mg/m³
- Others: accepts µg/m³, mg/m³, ppm, ppb → converts to µg/m³
- Molecular weight conversions use standard factors (lines 8-13)
- Returns `None` for unsafe/unknown units

### What Must Change

- **Remove `iso=IN` parameter** or make it location-dependent
- **Provider is otherwise global-ready** — no hardcoded restrictions beyond that one parameter

---

### 3.2 Open-Meteo Provider

**File:** `backend/app/providers/openmeteo.py`

**Purpose:** Model-based weather and air-quality forecasts (not station observations)

**Air quality endpoint** (lines 86-104):
- API: `https://air-quality-api.open-meteo.com/v1/air-quality`
- Parameters: `latitude`, `longitude`, `hourly` (comma-separated field list), `forecast_days=3`, `timezone=UTC`
- **Fields requested** (lines 23-30):
  ```python
  AQ_FIELDS = {
      "pm2_5": ("pm25", "µg/m³", 1.0),
      "pm10": ("pm10", "µg/m³", 1.0),
      "carbon_monoxide": ("co", "mg/m³", 0.001),  # API reports in µg/m³
      "nitrogen_dioxide": ("no2", "µg/m³", 1.0),
      "sulphur_dioxide": ("so2", "µg/m³", 1.0),
      "ozone": ("o3", "µg/m³", 1.0),
  }
  ```
- Returns: `list[ForecastPoint]` with `parameter`, `value`, `unit`, `forecast_for`, `kind="air_quality"`

**Critical finding: No pre-calculated AQI variables**

The task requirements state: "Investigate available AQI variables, including US AQI and European AQI, in the current API documentation. Use supported variables rather than deriving an index from incomplete model data."

**Open-Meteo Air Quality API does NOT expose `us_aqi` or `european_aqi` variables.** The API documentation ([open-meteo.com/en/docs/air-quality-api](https://open-meteo.com/en/docs/air-quality-api)) lists only:
- Raw pollutant concentrations (pm10, pm2_5, carbon_monoxide, nitrogen_dioxide, sulphur_dioxide, ozone, etc.)
- European AQI is available **only as a deprecated variable** in the older v1 API
- US AQI is **not available** in any Open-Meteo API

The current code correctly uses Open-Meteo only for model-based pollutant forecasts and weather, **never for AQI calculation**. This is architecturally sound: station observations from OpenAQ drive the official AQI; model data stays separate in the `forecasts` table (lines 228-240 in `backend/app/models.py`).

### What Must Change

- **Provider is global-ready** — no changes needed
- **Do not attempt to fetch AQI from Open-Meteo** — it doesn't exist in a reliable form
- **Model data must stay distinguished** from station observations in the database and UI

---

## 4. Database Models

**File:** `backend/app/models.py`

### 4.1 Location Table (lines 21-32)

```python
class Location(Base):
    id: Mapped[int] = primary_key
    name: Mapped[str]
    city: Mapped[str]
    country: Mapped[str] = default="India"  # <-- Default hardcoded
    latitude: Mapped[float]
    longitude: Mapped[float]
    timezone: Mapped[str] = default="Asia/Kolkata"  # <-- India default
    is_popular: Mapped[bool] = default=True
```

**Already global-ready:** Country is stored, no constraints. Defaults are India-centric but overridden during geocoding.

---

### 4.2 Station Table (lines 35-51)

```python
class Station(Base):
    id: Mapped[int] = primary_key
    location_id: Mapped[int] = ForeignKey("locations.id")
    provider: Mapped[str]  # "openaq", "sample"
    external_id: Mapped[str]
    name: Mapped[str]
    latitude: Mapped[float]
    longitude: Mapped[float]
    is_monitor: Mapped[bool] = default=True
    
    __table_args__ = (UniqueConstraint("provider", "external_id"),)
```

**Global-ready:** No India-specific fields.

---

### 4.3 Sensor and Measurement Tables (lines 54-88)

```python
class Sensor(Base):
    id: Mapped[int] = primary_key
    station_id: Mapped[int] = ForeignKey("stations.id")
    external_id: Mapped[str | None]
    parameter: Mapped[str]  # "pm25", "pm10", "no2", etc.
    unit: Mapped[str]
```

```python
class Measurement(Base):
    id: Mapped[int] = primary_key
    sensor_id: Mapped[int] = ForeignKey("sensors.id")
    value: Mapped[float]
    unit: Mapped[str]
    measured_at: Mapped[datetime]
    fetched_at: Mapped[datetime]
    source: Mapped[str]  # "openaq", "sample", "open-meteo"
    averaging_period: Mapped[str] = default="1h"
```

**Global-ready:** Source is stored but not whether it's observation vs. model.

---

### 4.4 AQIRecord Table (lines 91-106) — **CRITICAL**

```python
class AQIRecord(Base):
    id: Mapped[int] = primary_key
    location_id: Mapped[int | None] = ForeignKey("locations.id")
    station_id: Mapped[int | None] = ForeignKey("stations.id")
    aqi: Mapped[int | None]
    category: Mapped[str | None]
    dominant_pollutant: Mapped[str | None]
    available: Mapped[bool] = default=False
    reason: Mapped[str | None]
    methodology: Mapped[str]  # "CPCB-NAQI-2014" <-- STORED BUT NOT INDEXED
    inputs_json: Mapped[str | None]  # JSON of sub-indices
    calculated_at: Mapped[datetime]
```

**Issues:**
1. **Methodology stored but not used** — no unique constraint, no filtering by methodology
2. **No observation vs. model discrimination** — cannot distinguish official AQI from model-based estimate
3. **Dominant pollutant as comma-separated string** (line 98) — stored as `", ".join(...)` in `dashboard.py:425`
4. **No methodology version** separate from methodology name

**What Must Change:**
- Add index/constraint on `(location_id, station_id, methodology, calculated_at)` to prevent duplicate calculations
- Add `source_type` or `kind` column: "observation" vs. "model_estimate"
- Add `methodology_version` if standards evolve (optional, can stay in methodology string)
- Add `availability_reason` separate from `reason` to distinguish unavailable states

---

### 4.5 Forecast Table (lines 215-232)

```python
class Forecast(Base):
    """Model output. Kept out of measurements so it cannot be read as a station observation."""
    id: Mapped[int] = primary_key
    location_id: Mapped[int] = ForeignKey("locations.id")
    parameter: Mapped[str]
    value: Mapped[float]
    unit: Mapped[str]
    forecast_for: Mapped[datetime]
    fetched_at: Mapped[datetime]
    source: Mapped[str]  # "open-meteo"
    kind: Mapped[str]  # "air_quality", "weather"
```

**Architectural decision (line 215 comment):** Forecasts are separate from measurements to prevent model data from being treated as station observations. This separation must be preserved.

---

### 4.6 CacheEntry Table (lines 235-244)

```python
class CacheEntry(Base):
    id: Mapped[int] = primary_key
    cache_key: Mapped[str] = unique  # e.g., "openaq:{location_id}"
    provider: Mapped[str]
    location_id: Mapped[int | None] = ForeignKey("locations.id")
    fetched_at: Mapped[datetime]
    expires_at: Mapped[datetime]
    payload_ref: Mapped[str | None]
    hit_count: Mapped[int] = default=0
```

**Issue:** Cache key is `f"openaq:{location_id}"` (line 24 in `cache.py`) — **does not include methodology**. A cached fetch for CPCB calculation would be reused for US EPA calculation, leading to stale/incorrect AQI.

**What Must Change:**
- Cache key must include methodology: `f"{provider}:{location_id}:{methodology}"`
- Or separate AQI calculation cache from provider data cache (recommended)

---

## 5. API Schemas and Responses

**File:** `backend/app/schemas.py`

### 5.1 AQIOut (lines 18-30)

```python
class AQIOut(BaseModel):
    available: bool
    value: int | None = None
    category: str | None = None
    dominant_pollutants: list[str] = Field(default_factory=list)
    calculated_at: datetime | None = None
    methodology: str  # e.g., "CPCB-NAQI-2014"
    reason: str | None = None
    sub_indices: list[SubIndexOut] = Field(default_factory=list)
    station_id: int | None = None
    station_name: str | None = None
```

**Good:** Methodology is already exposed. Category names are dynamic (returned from backend).

**Missing:**
- No `source_type` or `kind` field to distinguish observation-based vs. model-based AQI
- No `methodology_version` separate from methodology string
- No structured `availability_status` enum

---

### 5.2 SubIndexOut (lines 11-19)

```python
class SubIndexOut(BaseModel):
    parameter: str
    display_name: str
    sub_index: int
    concentration_used: float
    unit: str
    averaging_period: str
    coverage_hours: int
```

**CPCB-specific fields:** `coverage_hours` is a CPCB requirement. US EPA and European AQI may not use coverage rules.

---

### 5.3 OverviewOut (lines 174-189) — Main Dashboard Response

```python
class OverviewOut(BaseModel):
    location: LocationOut
    freshness: str  # "recent", "stale", "unavailable"
    data_origin: str  # "sample", "openaq", "unavailable"
    warnings: list[str]
    summary_station: StationOut | None
    aqi: AQIOut
    pollutants: list[PollutantOut]
    health: HealthOut | None
    weather: WeatherOut | None
    stations: list[StationOut]
    history: HistoryOut
    sources: list[str]
```

**Good:** `data_origin` distinguishes sample/live data. `sources` lists methodology and providers (lines 645-655 in `dashboard.py`).

**Missing:** No explicit `aqi_standard` field at top level (though `aqi.methodology` provides it).

---

## 6. Frontend AQI Display

### 6.1 Category Styling

**File:** `frontend/src/lib/format.ts`

**Hardcoded CPCB categories** (lines 19-26):
```typescript
export const CATEGORIES: Record<string, CategoryStyle> = {
  Good: style("good"),
  Satisfactory: style("satisfactory"),
  Moderate: style("moderate"),
  Poor: style("poor"),
  "Very Poor": style("very-poor"),
  Severe: style("severe", "var(--aqi-severe-on)"),
};
```

**AQI scale** (lines 29-36):
```typescript
export const AQI_SCALE = [
  { category: "Good", min: 0, max: 50 },
  { category: "Satisfactory", min: 51, max: 100 },
  { category: "Moderate", min: 101, max: 200 },
  { category: "Poor", min: 201, max: 300 },
  { category: "Very Poor", min: 301, max: 400 },
  { category: "Severe", min: 401, max: 500 },
] as const;
```

**CSS variables** (implied by `style()` function, lines 11-17):
- `--aqi-good`, `--aqi-satisfactory`, `--aqi-moderate`, `--aqi-poor`, `--aqi-very-poor`, `--aqi-severe`
- `--aqi-{category}-text` for readable text color
- `--aqi-unknown` for unavailable state

**Issue:** US EPA categories are "Good", "Moderate", "Unhealthy for Sensitive Groups", "Unhealthy", "Very Unhealthy", "Hazardous" — **completely different names**. European AQI uses 5 bands with different names. Frontend will break if backend returns non-CPCB category names.

---

### 6.2 AQI Gauge Component

**File:** `frontend/src/components/aqi-gauge.tsx`

**Dial rendering** (lines 27-33):
```typescript
const BANDS = AQI_SCALE.map((band, index) => ({
  category: band.category,
  from: index === 0 ? 0 : band.min - 1,
  to: band.max,
}));
const TICKS = [0, ...BANDS.map((band) => band.to)]; // [0, 50, 100, 200, 300, 400, 500]
```

**Dial uses CPCB breakpoints** — 6 bands from 0-500. US EPA uses 0-500 but different breakpoints. European AQI uses 0-100+.

**Category badge** (lines 82-87):
```typescript
<span
  className="mt-3 rounded-full px-3.5 py-1 text-sm font-semibold"
  style={{ background: current.soft, color: current.text }}
>
  {available ? category : "Unavailable"}
</span>
```

**Issue:** If backend returns "Unhealthy for Sensitive Groups", the CSS lookup will fail (`CATEGORIES["Unhealthy for Sensitive Groups"]` is undefined).

---

### 6.3 Dashboard Display

**File:** `frontend/src/components/air-app.tsx` (truncated at line 728, but key sections visible)

**AQI card** (lines 532-560):
- Displays `overview.aqi.value`, `overview.aqi.category`
- Shows methodology: `overview.aqi.methodology` (line 540)
- Dominant pollutant with `<Formula>` component (lines 542-553)
- Gauge: `<AqiGauge value={...} category={...} available={...} />` (line 556)

**Sources footer** (visible at line 728+, implemented in `backend/app/services/dashboard.py:645-655`):
```python
def _sources(origin: str, weather: WeatherOut | None) -> list[str]:
    sources = []
    if origin == "openaq":
        sources.append("Station observations: OpenAQ")
    elif origin == "sample":
        sources.append("Station observations: bundled sample dataset")
    else:
        sources.append("Station observations: unavailable")
    sources.append("Indian AQI: calculated in this app with CPCB NAQI methodology")  # <-- Hardcoded
    if weather is not None:
        sources.append(f"Weather: {weather.label}")
    return sources
```

**Issue:** "Indian AQI" string is hardcoded (line 652). Must become dynamic based on methodology.

---

### 6.4 Pollutant Cards (Moderate Hardcoding)

**File:** `frontend/src/components/air-app.tsx` (lines 586-639, estimated)

Each pollutant card shows:
- Parameter name (via `<Formula>` — dynamic)
- Value and unit (from API)
- Sub-index progress bar colored by category (lines 617-627 estimated)
- "Dominant" badge if in `dominant_pollutants` list

**Sub-index rendering** depends on `categoryForIndex()` (in `format.ts:46-50`) which uses `AQI_SCALE` — CPCB breakpoints.

**Issue:** Sub-index coloring will be incorrect for non-CPCB methodologies. A sub-index of 150 is "Moderate" in CPCB but might be different in US EPA.

---

## 7. Caching Architecture

### 7.1 Three-Tier Cache (as documented in README)

1. **Provider fetch cache** (`CacheEntry` table) — prevents repeat OpenAQ calls
2. **Measurement storage** — database persists hourly observations
3. **Forecast cache** — model data expires after TTL

### 7.2 Cache Service

**File:** `backend/app/services/cache.py`

**Key construction** (lines 15-31):
```python
def provider_fetch_is_fresh(session: Session, location_id: int, ttl_minutes: int, now) -> bool:
    entry = _entry(session, location_id)  # Looks up by cache_key
    if entry is not None and as_utc(entry.expires_at) > now:
        return True
    # Falls back to checking Measurement.fetched_at for openaq provider
    ...

def _entry(session: Session, location_id: int) -> CacheEntry | None:
    return session.scalar(select(CacheEntry).where(CacheEntry.cache_key == f"openaq:{location_id}"))
```

**Critical issue:** Cache key is `f"openaq:{location_id}"` — **does not include methodology or AQI standard**. 

**Scenario:**
1. User requests Delhi with CPCB → fetches OpenAQ data, caches as `openaq:1`
2. User requests Delhi with US EPA → cache hit, no new fetch
3. US EPA AQI calculated from same measurements (which is correct), but cache doesn't prevent methodology-specific reprocessing

**Actually not a problem for provider fetch** (measurements are methodology-agnostic), but **could be a problem for AQI calculation cache** if one is added.

---

### 7.3 Popular City Refresh

**File:** `backend/app/jobs/refresh_popular.py`

**Scheduled job** (lines 28-41):
- Queries `Location` where `is_popular=True`
- Calls `refresh_location()` for each
- Commits after each location

**Documented behavior** (README line 133, `backend/app/cities.py` line 3):
> "Stage 3 will refresh only this list on a schedule. Other places stay on demand."

**Cloud deployment** (README lines 188-189):
- Cloud Scheduler job `refresh-popular` runs once/day at 02:30 Asia/Kolkata
- Sends `POST /api/v1/jobs/refresh-popular` to the API
- On-demand cities are fetched when dashboard is opened

**What Must Change:**
- **Popular cities should remain Indian** (requirement: "Do not schedule global data collection for every city")
- **Methodology selection** must occur during refresh (current: always CPCB)

---

## 8. Testing Coverage

### 8.1 AQI Tests

**File:** `backend/tests/test_aqi.py`

**Coverage:**
- CPCB breakpoint validation (lines 11-19)
- Concentration truncation before lookup (lines 22-25)
- Overall AQI = worst sub-index (lines 28-37)
- Minimum 3 pollutants + PM required (lines 40-50)
- Coverage rules (lines 53-68)
- 1-hour vs. 24-hour averaging period rejection (lines 71-73)
- Unit conversion (lines 76-81)
- OpenAQ response parsing (lines 84-101)
- Ozone > 208 uses 1-hour value (lines 104-114)

**All tests are CPCB-specific.** New tests needed for US EPA and European AQI.

---

### 8.2 API Integration Tests

**File:** `backend/tests/test_api.py`

**Coverage:**
- Location search and dashboard overview (lines 13-40)
- Missing pollutants stay unavailable (lines 43-51) — tests Pune "School Campus" station with no PM data
- Live ingest stores and deduplicates (lines 64-104)
- Refresh without API key keeps stored data (lines 155-165)

**Providers are mocked** via test doubles (lines 73-97, 130-148). No live API calls in tests.

---

### 8.3 Stage 2 Tests (Advanced Features)

**File:** `backend/tests/test_stage2.py`

**Coverage:**
- Model parser (Open-Meteo) (lines 10-23)
- History date ranges and buckets (lines 26-60)
- Compare multiple cities (lines 63-75)
- CSV export (lines 78-92)
- Forecast caching (lines 107-135)
- Scheduled job refreshes only popular cities (lines 138-158)
- Metrics endpoint (lines 161-170)
- Location discovery deduplication (lines 173-189)
- Compare fetches city with no stored readings (lines 192-278)
- Expired cache refreshes once then reuses (lines 317-399)
- Provider failure keeps stored readings, marks stale (lines 402-456)

**Excellent coverage of edge cases.** Global AQI tests should follow same mocking pattern.

---

### 8.4 Test Infrastructure

**File:** `backend/tests/conftest.py`

```python
@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("OPENAQ_API_KEY", "")
    get_settings.cache_clear()
    from app.main import create_app
    application = create_app()
    with TestClient(application) as client:
        yield client, application
    get_settings.cache_clear()
```

**Uses in-memory SQLite** for isolation. **OpenAQ key set to empty string** forces sample data mode.

---

## 9. Critical Backward Compatibility Constraints

### 9.1 Existing Endpoints Must Not Break

**API routes** (`backend/app/routers/locations.py`):
- `GET /api/v1/locations` — search (lines 29-47)
- `GET /api/v1/locations/{id}/overview` — main dashboard (lines 50-72)
- `GET /api/v1/locations/{id}/aqi` — AQI only (lines 75-82)
- `GET /api/v1/locations/{id}/history` — historical data (lines 85-119)
- `GET /api/v1/locations/{id}/forecast` — model forecast (lines 122-134)
- `GET /api/v1/locations/{id}/export` — CSV (lines 137-161)
- `GET /api/v1/locations/{id}/weather` — weather data (lines 164-173)
- `POST /api/v1/locations/{id}/refresh` — force refresh (lines 176-192)

**Constraint:** All existing Indian city queries must return the same structure with CPCB AQI. Frontend expects `overview.aqi.value`, `overview.aqi.category`, `overview.aqi.methodology`.

**Adding new fields is safe.** Renaming or removing fields breaks frontend.

---

### 9.2 Sample Data for Tests

**File:** `backend/app/sample.py` (not read, but referenced in tests)

Sample stations are loaded when `OPENAQ_API_KEY` is empty (line 2 in `conftest.py`). Tests depend on this behavior. Sample data must remain CPCB-compatible.

---

### 9.3 Indian Cities Must Use CPCB

**Requirement (from task description):**
> "Preserve all existing functionality and ensure Indian cities continue using CPCB methodology."

**Implementation impact:**
- Resolver must map `country="India"` → CPCB
- Database queries for Indian cities must filter by methodology to return CPCB results
- Popular city refresh must specify CPCB for Indian cities

---

## 10. Summary of Required Changes

### 10.1 Backend Changes (High Priority)

1. **AQI calculation refactor** (create `backend/app/aqi/` module):
   - `base.py`: Common interface (`AQICalculator` protocol)
   - `resolver.py`: Select methodology by country code
   - `cpcb.py`: Move existing `aqi.py` logic here
   - `us_epa.py`: Implement US EPA AQI (new)
   - `european.py`: Implement European AQI (new)
   - `categories.py`: Standard-specific category metadata

2. **Database schema additions**:
   - `AQIRecord`: Add `source_type` enum ("observation" | "model_estimate")
   - `AQIRecord`: Add index on `(location_id, methodology, calculated_at)`
   - Migration to preserve existing data

3. **API schema extensions**:
   - `AQIOut`: Add `source_type` field
   - `OverviewOut`: Document that `aqi.methodology` is dynamic
   - Existing fields remain unchanged (backward compatible)

4. **OpenAQ provider**:
   - Remove `iso=IN` parameter or make location-dependent
   - Already global-capable otherwise

5. **Dashboard service**:
   - Inject methodology resolver into AQI calculation (lines 279-285 in `dashboard.py`)
   - Update sources footer generation (line 652) to be methodology-aware
   - Pass country code from location to resolver

6. **Cache keys**:
   - Review whether methodology should be in cache key (likely not needed — measurements are reusable)

---

### 10.2 Frontend Changes (Medium Priority)

1. **Category styling** (`frontend/src/lib/format.ts`):
   - Make `CATEGORIES` dynamic or expand to include US EPA, European AQI names
   - Add fallback for unknown categories
   - Keep CPCB color scheme as default

2. **AQI gauge** (`frontend/src/components/aqi-gauge.tsx`):
   - Accept `scale` prop to render different breakpoints
   - Or render based on methodology returned from API
   - Keep existing gauge for CPCB

3. **Dashboard display** (`frontend/src/components/air-app.tsx`):
   - Display `aqi.methodology` more prominently
   - Show "Indian AQI" / "US AQI" / "European AQI" label dynamically
   - Distinguish observation vs. model-based AQI with visual indicator

4. **Sub-index coloring**:
   - Use category returned from backend, not `categoryForIndex()` lookup
   - Backend should return category for each sub-index

---

### 10.3 Testing Changes (High Priority)

1. **AQI calculation tests**:
   - New file: `test_us_epa_aqi.py` with EPA reference examples
   - New file: `test_european_aqi.py` with EEA reference examples
   - Preserve all existing `test_aqi.py` tests (CPCB)

2. **Integration tests for global locations**:
   - Test Delhi → CPCB
   - Test New York → US EPA (or unavailable if not implemented)
   - Test London → European AQI (or unavailable)
   - Test Tokyo → unavailable (no standard implemented)

3. **Mock OpenAQ global responses**:
   - Test non-Indian coordinates without `iso=IN` restriction

---

## 11. Architecture Recommendations

### 11.1 Modular AQI Calculation

**Suggested structure:**
```
backend/app/aqi/
├── __init__.py          # Exports calculate_aqi(readings, methodology)
├── base.py              # Protocol/ABC for AQI calculators
├── resolver.py          # Country → methodology mapping
├── cpcb.py              # Existing Indian implementation
├── us_epa.py            # US EPA implementation (new)
├── european.py          # European AQI implementation (new)
└── categories.py        # Category metadata per standard
```

**Benefits:**
- Existing code moves to `cpcb.py` with minimal changes
- New standards are isolated modules
- Resolver handles methodology selection
- Frontend remains agnostic (receives category name + color from API)

---

### 11.2 Methodology Selection Strategy

**Option A: Country-based (recommended):**
```python
METHODOLOGY_MAP = {
    "IN": "CPCB",
    "US": "US-EPA",
    "GB": "European",  # UK
    "FR": "European",  # France
    "DE": "European",  # Germany
    # ... all EU countries
}
```

**Option B: Explicit user selection:**
- Add `?methodology=CPCB` query parameter
- Let users compare different standards for same location
- More complex UX

**Recommendation:** Use Option A (country-based) with Option B as future enhancement.

---

### 11.3 Handling Unsupported Standards

**When a country has no implemented standard:**
1. Return `AQIOut(available=False, reason="AQI calculation unavailable for this country.")`
2. Display raw pollutant concentrations
3. Show message: "Supported AQI standards: CPCB (India), US EPA (United States), European AQI (EU). This location uses [country], which is not yet supported."

**Do not:**
- Silently display CPCB AQI for non-Indian locations
- Invent or approximate breakpoints

---

## 12. Open Questions and Risks

### 12.1 Open-Meteo AQI Variables (Resolved)

**Question:** Can we use Open-Meteo's `us_aqi` or `european_aqi` variables?

**Answer:** **No.** Open-Meteo air-quality API does not expose pre-calculated AQI in a reliable, standardized form. The current architecture (raw pollutant data only) is correct.

---

### 12.2 OpenAQ Coverage Outside India

**Risk:** OpenAQ may have limited station coverage in some countries. Many cities may return zero stations.

**Mitigation:**
- Display "No monitoring stations found within 25 km" message
- Show model-based Open-Meteo forecast as fallback (already implemented)
- Document coverage limitations in UI

---

### 12.3 Category Name Conflicts

**Risk:** US EPA uses "Unhealthy for Sensitive Groups" (25 characters). Frontend CSS uses class names. Long category names may break layout.

**Mitigation:**
- Use category abbreviations or codes in CSS: `uso` instead of `unhealthy-for-sensitive-groups`
- Backend returns both `category` (display name) and `category_code` (short form)
- Frontend maps codes to colors

---

### 12.4 Migration Strategy

**Risk:** Existing `AQIRecord` rows have no `source_type`. After migration, old records are ambiguous.

**Mitigation:**
- Backfill `source_type="observation"` for all existing rows (they're all station-based)
- Set `methodology="CPCB-NAQI-2014"` explicitly if NULL
- Add NOT NULL constraint after backfill

---

## 13. Files Requiring Modification (Summary Table)

| File | Change Type | Priority | Description |
|------|-------------|----------|-------------|
| `backend/app/aqi.py` | Refactor → `aqi/cpcb.py` | High | Move to modular structure |
| `backend/app/aqi/base.py` | New | High | Common AQI calculator interface |
| `backend/app/aqi/resolver.py` | New | High | Country → methodology mapping |
| `backend/app/aqi/us_epa.py` | New | High | US EPA AQI implementation |
| `backend/app/aqi/european.py` | New | High | European AQI implementation |
| `backend/app/aqi/categories.py` | New | Medium | Category metadata per standard |
| `backend/app/models.py` | Modify | High | Add `AQIRecord.source_type`, index |
| `backend/app/schemas.py` | Extend | Medium | Add `AQIOut.source_type` |
| `backend/app/services/dashboard.py` | Modify | High | Inject methodology resolver (line 279-285, 652) |
| `backend/app/providers/openaq.py` | Modify | Medium | Remove `iso=IN` restriction (line 80) |
| `backend/tests/test_aqi.py` | Preserve | High | Ensure CPCB tests still pass |
| `backend/tests/test_us_epa_aqi.py` | New | High | US EPA test cases |
| `backend/tests/test_european_aqi.py` | New | High | European AQI test cases |
| `backend/tests/test_api.py` | Extend | Medium | Add global location tests |
| `frontend/src/lib/format.ts` | Modify | Medium | Dynamic categories (lines 19-26, 29-36) |
| `frontend/src/components/aqi-gauge.tsx` | Modify | Medium | Support multiple scales |
| `frontend/src/components/air-app.tsx` | Modify | Low | Dynamic methodology label |

---

## 14. Verification Checklist

After implementation, verify:

- [ ] Delhi returns CPCB AQI with identical values to current implementation
- [ ] New York returns US EPA AQI (if implemented) or unavailable message
- [ ] London returns European AQI (if implemented) or unavailable message
- [ ] Tokyo returns unavailable message with clear reason
- [ ] Frontend displays correct category colors for each methodology
- [ ] Sub-indices are colored per their methodology's scale
- [ ] Model-based AQI (if calculated) is labeled differently from station-based AQI
- [ ] Cached OpenAQ data is reused across methodologies
- [ ] Existing tests in `test_aqi.py` pass without modification
- [ ] Sample data mode (no OpenAQ key) still works for Indian cities
- [ ] Popular city refresh still targets only Indian cities
- [ ] On-demand global cities are stored and reused
- [ ] CSV export includes methodology column
- [ ] History and comparison features work for global cities
- [ ] OpenAQ `iso=IN` restriction is removed or conditional

---

## 15. Key Preservation Requirements (from Task Description)

1. ✅ **Location search is already global** — Open-Meteo geocoding works worldwide
2. ⚠️ **OpenAQ has India-first restriction** — `iso=IN` parameter must be removed
3. ✅ **Open-Meteo is global** — no changes needed
4. ❌ **AQI calculation is CPCB-only** — requires full refactor
5. ⚠️ **Database lacks methodology discrimination** — needs schema changes
6. ⚠️ **Frontend hardcodes CPCB categories** — needs dynamic handling
7. ✅ **Caching is location-based** — should work for global locations
8. ✅ **Popular cities are Indian-only** — must stay that way
9. ✅ **Tests use mocked providers** — pattern is reusable for global tests

---

## Conclusion

The application is architecturally sound but **tightly coupled to CPCB methodology**. Location search and data providers are largely global-ready, but AQI calculation, database schema, and frontend display all assume Indian standards.

**Estimated effort:**
- **Backend refactor:** 2-3 days (modular AQI, schema changes, resolver)
- **US EPA implementation:** 1-2 days (official breakpoints, testing)
- **European AQI implementation:** 1-2 days (official breakpoints, testing)
- **Frontend updates:** 1 day (dynamic categories, layout)
- **Testing:** 2 days (new test suites, integration tests)
- **Documentation:** 0.5 day (update README, API docs)

**Total:** 7.5-10.5 days for full global AQI support with three methodologies.

**Recommended phasing:**
1. **Phase 1:** Backend refactor (modular structure, CPCB preservation)
2. **Phase 2:** US EPA implementation (highest demand outside India)
3. **Phase 3:** European AQI implementation
4. **Phase 4:** Frontend polish and global testing

---

**Report complete. Investigation conducted on: `/home/vishwas/Desktop/CC/community-air-quality/.worktrees/global-aqi`**
