# Implementation Plan: Global AQI Support

## Overview

This plan refactors the existing CPCB-only AQI system into a modular, multi-standard architecture supporting India (CPCB), United States (EPA), and Europe (EEA) methodologies. The implementation preserves all existing functionality, maintains backward compatibility, and follows the discovered project patterns.

### Implementation Approach

1. **Modular AQI Engine First**: Create the abstraction layer and implement each standard in isolation with comprehensive tests
2. **Database Schema Evolution**: Add methodology discrimination without breaking existing data
3. **Provider Updates**: Remove India bias and verify global coordinate support
4. **Backend Integration**: Wire the new engine into services with methodology resolution
5. **Frontend Dynamic Categories**: Replace hardcoded CPCB display with backend-driven metadata
6. **End-to-End Testing**: Verify multi-city scenarios with real coordinates

### Key Design Decisions

**AQI Methodology Resolution**: Country-based mapping (IN → CPCB, US → EPA, EU countries → European, others → unavailable with pollutant display). The resolver lives in `backend/app/aqi/resolver.py` and is the single source of truth for methodology selection.

**Breakpoint Sources**: 
- CPCB: Existing implementation (verified correct)
- US EPA: [Official breakpoint table](https://aqs.epa.gov/aqsweb/documents/codetables/aqi_breakpoints.html) (content rephrased for compliance with licensing restrictions)
- European AQI: [EEA methodology](https://airindex.eea.europa.eu/) using 6-band hourly concentration thresholds

**Cache Key Strategy**: Extend existing cache keys to include methodology identifier (e.g., `aqi:location:42:CPCB-NAQI-2014`) to prevent cross-methodology reuse.

**Unavailable State Handling**: When no implemented standard matches the location's country, display raw pollutant concentrations with clear message: "AQI calculation unavailable. Supported methodologies: CPCB (India), US EPA (United States), European AQI (EU countries)."

**Open-Meteo AQI Variables**: Investigation shows Open-Meteo API supports `us_aqi` and `european_aqi` variables in the air-quality endpoint. These will be used as model-based estimates, clearly labeled distinct from station observations.

---

## Implementation Steps

### Phase 1: AQI Calculation Engine Refactor

- [ ] **1. Create AQI module structure**
  
  Create the new modular architecture in `backend/app/aqi/` to replace the monolithic `backend/app/aqi.py`.
  
  **Files to create:**
  - `backend/app/aqi/__init__.py` - Public API exports
  - `backend/app/aqi/base.py` - Abstract base classes and shared utilities
  - `backend/app/aqi/categories.py` - Category definitions per standard
  - `backend/app/aqi/cpcb.py` - Existing CPCB logic migrated
  - `backend/app/aqi/us_epa.py` - US EPA implementation
  - `backend/app/aqi/european.py` - European AQI implementation
  - `backend/app/aqi/resolver.py` - Country-to-methodology mapping
  
  **Verify:** Run `python -c "from app.aqi import calculate_aqi; print('Import successful')"` after activating venv. Module structure is valid when import succeeds without errors.

- [ ] **2. Implement base.py with shared abstractions**
  
  Define `AQICalculator` abstract base class with `calculate(readings: list[PollutantAverage]) -> AQIResult` interface. Include shared utilities: `round_half_up()`, `linear_interpolation()`, `truncate_concentration()`. Define `PollutantAverage` and `AQIResult` dataclasses (reuse existing from `aqi.py`).
  
  **Files:** `backend/app/aqi/base.py`
  
  **Verify:** Run `python -c "from app.aqi.base import AQICalculator; print(AQICalculator.__subclasses__())"` - should print empty list initially, confirming abstract class is importable.

- [ ] **3. Implement categories.py with all standard definitions**
  
  Define category metadata for each standard:
  - **CPCB**: 6 categories (Good, Satisfactory, Moderate, Poor, Very Poor, Severe), 0-500 scale, existing color codes
  - **US EPA**: 6 categories (Good, Moderate, Unhealthy for Sensitive Groups, Unhealthy, Very Unhealthy, Hazardous), 0-500 scale, EPA standard colors
  - **European**: 6 categories (Good, Fair, Moderate, Poor, Very Poor, Extremely Poor), hourly concentration-based, EEA colors
  
  Each standard includes: category name, index range (min/max), color hex codes, health messages for general and sensitive populations.
  
  **Files:** `backend/app/aqi/categories.py`
  
  **Verify:** Run `python -c "from app.aqi.categories import CPCB_CATEGORIES, US_EPA_CATEGORIES, EUROPEAN_CATEGORIES; print(len(CPCB_CATEGORIES), len(US_EPA_CATEGORIES), len(EUROPEAN_CATEGORIES))"` - should print `6 6 6`.

- [ ] **4. Migrate CPCB implementation to cpcb.py**
  
  Copy existing `backend/app/aqi.py` logic into `backend/app/aqi/cpcb.py` as `CPCBAQICalculator(AQICalculator)` class. Preserve all existing breakpoints, coverage rules, averaging period requirements, and rounding behavior. Update imports to use `base.py` abstractions. Set `methodology = "CPCB-NAQI-2014"`.
  
  **Files:** `backend/app/aqi/cpcb.py`
  
  **Verify:** Run existing CPCB tests against new module: `cd backend && source .venv/bin/activate && python -m pytest tests/test_aqi.py -v`. All existing tests must pass without modification.

- [ ] **5. Implement US EPA calculator in us_epa.py**
  
  Implement `USEPAAQICalculator(AQICalculator)` using official EPA breakpoints (content rephrased for compliance):
  - PM2.5 (24h): 0-12→0-50, 12.1-35.4→51-100, 35.5-55.4→101-150, 55.5-150.4→151-200, 150.5-250.4→201-300, 250.5-500.4→301-500
  - PM10 (24h): 0-54→0-50, 55-154→51-100, 155-254→101-150, 255-354→151-200, 355-424→201-300, 425-604→301-500
  - O3 (8h): 0-54→0-50, 55-70→51-100, 71-85→101-150, 86-105→151-200, 106-200→201-300 (1h for >200ppb)
  - NO2 (1h): 0-53→0-50, 54-100→51-100, 101-360→101-150, 361-649→151-200, 650-1249→201-300, 1250-2049→301-500
  - SO2 (1h): 0-35→0-50, 36-75→51-100, 76-185→101-150, 186-304→151-200, 305-604→201-300, 605-1004→301-500
  - CO (8h): 0-4.4→0-50, 4.5-9.4→51-100, 9.5-12.4→101-150, 12.5-15.4→151-200, 15.5-30.4→201-300, 30.5-50.4→301-500
  
  EPA requires valid PM2.5 or PM10 for overall AQI. Set `methodology = "US-EPA-AQI-2024"`.
  
  **Files:** `backend/app/aqi/us_epa.py`
  
  **Verify:** Write and run EPA-specific tests in `backend/tests/test_us_epa.py` with official EPA examples. Confirm PM2.5=35.5 yields AQI=101, PM2.5=55.5 yields AQI=151.

- [ ] **6. Implement European AQI calculator in european.py**
  
  Implement `EuropeanAQICalculator(AQICalculator)` using EEA hourly thresholds (content rephrased for compliance):
  - PM2.5: 0-5→Good, 6-15→Fair, 16-50→Moderate, 51-90→Poor, 91-140→Very Poor, >140→Extremely Poor
  - PM10: 0-15→Good, 16-45→Fair, 46-120→Moderate, 121-195→Poor, 196-270→Very Poor, >270→Extremely Poor
  - O3: 0-60→Good, 61-100→Fair, 101-120→Moderate, 121-160→Poor, 161-180→Very Poor, >180→Extremely Poor
  - NO2: 0-10→Good, 11-25→Fair, 26-60→Moderate, 61-100→Poor, 101-150→Very Poor, >150→Extremely Poor
  - SO2: 0-20→Good, 21-40→Fair, 41-125→Moderate, 126-190→Poor, 191-275→Very Poor, >275→Extremely Poor
  
  European index uses hourly concentrations (not 24h averages). Overall index = worst pollutant category. Requires PM (PM2.5 or PM10) + NO2 + O3 for background/industrial stations; PM + NO2 for traffic stations. Set `methodology = "European-AQI-2024"`.
  
  **Files:** `backend/app/aqi/european.py`
  
  **Verify:** Write and run European tests in `backend/tests/test_european_aqi.py`. Confirm PM2.5=15 µg/m³ (hourly) yields "Fair" category.

- [ ] **7. Implement methodology resolver**
  
  Create `resolve_methodology(country_code: str) -> str | None` function that maps country codes to methodology identifiers:
  - "IN" → "CPCB-NAQI-2014"
  - "US" → "US-EPA-AQI-2024"
  - EU country codes (AT, BE, BG, HR, CY, CZ, DK, EE, FI, FR, DE, GR, HU, IE, IT, LV, LT, LU, MT, NL, PL, PT, RO, SK, SI, ES, SE) → "European-AQI-2024"
  - UK codes (GB, UK) → "European-AQI-2024" (UK continues using EEA index)
  - All others → None (unavailable)
  
  Create `get_calculator(methodology: str) -> AQICalculator` factory returning appropriate calculator instance.
  
  **Files:** `backend/app/aqi/resolver.py`
  
  **Verify:** Unit tests in `backend/tests/test_resolver.py`. Assert `resolve_methodology("IN") == "CPCB-NAQI-2014"`, `resolve_methodology("US") == "US-EPA-AQI-2024"`, `resolve_methodology("FR") == "European-AQI-2024"`, `resolve_methodology("JP") is None`.

- [ ] **8. Update aqi module exports**
  
  Re-export necessary classes and functions from `backend/app/aqi/__init__.py` to maintain backward compatibility with existing imports (`from app.aqi import calculate_aqi`). Export `calculate_aqi`, `PollutantAverage`, `AQIResult`, `resolve_methodology`, `get_calculator`, category dictionaries.
  
  **Files:** `backend/app/aqi/__init__.py`
  
  **Verify:** Run all existing backend tests: `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`. Zero import errors and all CPCB tests still pass.

---

### Phase 2: Database Schema and Models

- [ ] **9. Add source_type field to AQIRecord model**
  
  Add `source_type: Mapped[str] = mapped_column(String(24), nullable=False, default="observation")` to `AQIRecord` class in `backend/app/models.py`. Valid values: "observation" (station-based), "model" (Open-Meteo estimate). Default to "observation" for backward compatibility with existing records.
  
  **Files:** `backend/app/models.py`
  
  **Verify:** Start the backend locally (`uvicorn app.main:app --reload --port 8000`). SQLAlchemy auto-creates the new column with default value. Confirm no startup errors and existing data remains intact.

- [ ] **10. Add availability_status and version fields to AQIRecord**
  
  Add two fields to `AQIRecord`:
  - `availability_status: Mapped[str | None] = mapped_column(String(32), nullable=True)` - Values: "available", "insufficient_coverage", "unsupported_methodology", "missing_pollutants"
  - `methodology_version: Mapped[str | None] = mapped_column(String(64), nullable=True)` - Full version string (e.g., "CPCB-NAQI-2014-v1.0")
  
  **Files:** `backend/app/models.py`
  
  **Verify:** Restart backend. Check database schema with `sqlite3 backend/data/airquality.db ".schema aqi_records"` - new columns present.

- [ ] **11. Add composite index on location_id, methodology, calculated_at**
  
  Add index to `AQIRecord.__table_args__` to optimize queries filtering by location and methodology: `Index("ix_aqi_location_methodology_time", "location_id", "methodology", "calculated_at")`. This supports efficient retrieval of the latest AQI for a specific methodology.
  
  **Files:** `backend/app/models.py`
  
  **Verify:** Restart backend. Run `sqlite3 backend/data/airquality.db ".indexes aqi_records"` - new index appears in output.

- [ ] **12. Update AQIOut schema with new fields**
  
  Add fields to `AQIOut` Pydantic schema in `backend/app/schemas.py`:
  - `source_type: str = "observation"` - Distinguishes station vs model
  - `availability_status: str | None = None` - Why AQI is/isn't available
  - `methodology_version: str | None = None` - Detailed version info
  
  Keep existing `methodology` field (already present). Maintain backward compatibility by providing sensible defaults.
  
  **Files:** `backend/app/schemas.py`
  
  **Verify:** Run `python -c "from app.schemas import AQIOut; print(AQIOut.model_json_schema())"` - new fields appear in schema definition.

- [ ] **13. Update cache key generation to include methodology**
  
  Modify cache key functions in `backend/app/services/cache.py` (or wherever cache keys are generated) to include methodology identifier. Pattern: `aqi:{location_id}:{methodology}:{timestamp_bucket}`. Ensures CPCB and EPA AQI for the same location are cached separately.
  
  **Files:** `backend/app/services/*.py` (locate cache key generation)
  
  **Verify:** Run backend with test data. Query cache_entries table: `sqlite3 backend/data/airquality.db "SELECT cache_key FROM cache_entries WHERE provider='aqi' LIMIT 5;"` - keys include methodology.

---

### Phase 3: Provider Updates

- [ ] **14. Remove India-first bias from OpenAQ provider**
  
  In `backend/app/providers/openaq.py`, method `nearby_stations()`, remove the initial request with `"iso": "IN"` parameter. Make only one request with coordinates and radius, no country filter. This ensures equal treatment of all global locations.
  
  **Files:** `backend/app/providers/openaq.py`
  
  **Verify:** Write test in `backend/tests/test_openaq.py` mocking OpenAQ API. Confirm only one API call is made for non-Indian coordinates and no "iso" parameter is sent.

- [ ] **15. Verify Open-Meteo global coordinate support**
  
  Read `backend/app/providers/openmeteo.py` and confirm `air_quality_forecast()` and `current_weather()` methods accept any valid latitude/longitude without country restrictions. Add docstring confirming global support.
  
  **Files:** `backend/app/providers/openmeteo.py`
  
  **Verify:** Write integration test with coordinates for New York (40.7128, -74.0060), London (51.5074, -0.1278), Tokyo (35.6762, 139.6503). Mock responses and confirm no errors.

- [ ] **16. Investigate Open-Meteo native AQI variables**
  
  Check Open-Meteo air-quality API documentation for `us_aqi` and `european_aqi` variables. If available, add them to `AQ_FIELDS` dictionary in `backend/app/providers/openmeteo.py` as separate parameters (e.g., `"us_aqi": ("us_aqi_model", "index", 1.0)`). These provide model-based AQI estimates.
  
  **Files:** `backend/app/providers/openmeteo.py`
  
  **Verify:** Make test API request to `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=40.7128&longitude=-74.0060&hourly=us_aqi,european_aqi`. If variables return data, integration successful. If not available, document findings and skip this feature.

---

### Phase 4: Backend Service Integration

- [ ] **17. Update aggregate.py to support methodology-specific averaging**
  
  Review `backend/app/aggregate.py` (or equivalent module handling pollutant averaging). Ensure averaging logic can handle both 24-hour (CPCB, EPA PM/gaseous) and 1-hour (European AQI) requirements. Add `methodology` parameter to averaging functions if needed.
  
  **Files:** `backend/app/aggregate.py`
  
  **Verify:** Unit tests confirming 24h averaging for CPCB/EPA pollutants and 1h for European AQI. Mock time-series data and verify correct period selection.

- [ ] **18. Update dashboard service to resolve and apply methodology**
  
  In `backend/app/services/dashboard.py`, function `build_overview()`:
  1. Get location's country code from Location model
  2. Call `resolve_methodology(country_code)` to determine standard
  3. If methodology is None, set `aqi.available=False`, `aqi.availability_status="unsupported_methodology"`, populate pollutants list, return
  4. Otherwise, get calculator with `get_calculator(methodology)` and compute AQI
  5. Populate new AQI fields: `source_type="observation"`, `availability_status="available"`, `methodology_version`
  
  **Files:** `backend/app/services/dashboard.py`
  
  **Verify:** Start backend, query Delhi (`/api/v1/locations/{delhi_id}/overview`) → CPCB methodology. Query New York location → EPA methodology or unavailable with pollutants displayed.

- [ ] **19. Store AQI records with complete methodology metadata**
  
  Update AQI persistence logic (likely in `backend/app/services/dashboard.py` or `backend/app/services/aqi.py`) to populate all new fields when creating `AQIRecord`:
  - Set `methodology` to resolved value (e.g., "CPCB-NAQI-2014")
  - Set `source_type` to "observation" for station data, "model" for Open-Meteo
  - Set `availability_status` based on calculation result
  - Set `methodology_version` with detailed version string
  
  **Files:** `backend/app/services/dashboard.py`, `backend/app/services/aqi.py` (if exists)
  
  **Verify:** Trigger AQI calculation for test location. Query database: `sqlite3 backend/data/airquality.db "SELECT methodology, source_type, availability_status FROM aqi_records LIMIT 5;"` - new fields populated correctly.

- [ ] **20. Update health advice to be methodology-aware**
  
  In `backend/app/services/dashboard.py` (or health module), function generating health messages (returns `HealthOut`), select appropriate health advice based on AQI methodology. Each standard has different category names and health recommendations:
  - CPCB: Existing messages for "Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"
  - EPA: Messages for "Good", "Moderate", "Unhealthy for Sensitive Groups", "Unhealthy", "Very Unhealthy", "Hazardous"
  - European: Messages for "Good", "Fair", "Moderate", "Poor", "Very Poor", "Extremely Poor"
  
  **Files:** `backend/app/services/dashboard.py`
  
  **Verify:** Query `/api/v1/locations/{location_id}/overview` for different countries. Confirm health advice matches the methodology's category names.

- [ ] **21. Update comparison endpoint to handle mixed methodologies**
  
  In `backend/app/routers/compare.py` (or equivalent), update comparison logic to:
  1. Display each location's methodology in comparison results
  2. Add disclaimer when comparing locations with different methodologies (e.g., "Locations use different AQI standards and cannot be directly compared")
  3. Show raw pollutant concentrations alongside AQI for cross-methodology comparison
  
  **Files:** `backend/app/routers/compare.py`, `backend/app/services/analytics.py`
  
  **Verify:** Call `/api/v1/compare?location_ids=1,2` with Delhi (CPCB) and New York (EPA). Response includes methodology field for each location and disclaimer about different standards.

- [ ] **22. Update CSV export to include methodology column**
  
  In `backend/app/services/analytics.py`, function `export_csv()`, add "AQI Methodology" column to exported CSV. Each row with AQI should show which standard was used (CPCB-NAQI-2014, US-EPA-AQI-2024, European-AQI-2024, or blank if unavailable).
  
  **Files:** `backend/app/services/analytics.py`
  
  **Verify:** Export CSV for location with AQI data (`/api/v1/locations/{location_id}/export`). Open downloaded CSV, confirm "AQI Methodology" column present and populated.

---

### Phase 5: Frontend Updates

- [ ] **23. Create dynamic category system in format.ts**
  
  Replace hardcoded `CATEGORIES` and `AQI_SCALE` in `frontend/src/lib/format.ts` with dynamic system:
  1. Add type `CategoryMetadata = { name: string; min: number; max: number; color: string; textColor: string; }[]`
  2. Keep CPCB as fallback but prepare to accept backend metadata
  3. Create `getCategoryStyle(category: string, metadata?: CategoryMetadata)` that looks up colors from provided metadata or falls back to existing
  
  **Files:** `frontend/src/lib/format.ts`
  
  **Verify:** Build frontend (`npm run build`). No TypeScript errors. Existing pages still render with CPCB colors.

- [ ] **24. Update API types to include new AQI fields**
  
  Create or update TypeScript types matching backend schemas. Add fields to AQI type:
  - `source_type: string` - "observation" or "model"
  - `availability_status: string | null` - Why AQI is unavailable
  - `methodology_version: string | null` - Detailed version
  
  Existing `methodology` field should already exist from backend.
  
  **Files:** `frontend/src/types/api.ts` (create if needed) or inline types
  
  **Verify:** TypeScript compilation succeeds. Run `npm run build` with no type errors.

- [ ] **25. Extend backend schema to include category metadata in AQI response**
  
  Update `AQIOut` schema in `backend/app/schemas.py` to include optional `categories` field:
  ```python
  categories: list[dict[str, Any]] = Field(default_factory=list)  # [{"name": "Good", "min": 0, "max": 50, "color": "#00e400"}, ...]
  ```
  
  Populate this field in dashboard service with category metadata from `app.aqi.categories` based on methodology.
  
  **Files:** `backend/app/schemas.py`, `backend/app/services/dashboard.py`
  
  **Verify:** Query API `/api/v1/locations/{location_id}/aqi`. Response includes `categories` array with name, range, and color for each category.

- [ ] **26. Update AQI gauge component to use dynamic categories**
  
  Locate AQI gauge component (likely `frontend/src/components/AQIGauge.tsx` or similar). Update to:
  1. Accept `categories` prop from API response
  2. Render gauge segments dynamically from categories array
  3. Use provided colors instead of hardcoded CSS variables
  4. Display methodology name below gauge (e.g., "CPCB National AQI" or "US EPA AQI")
  
  **Files:** `frontend/src/components/AQIGauge.tsx` (or equivalent)
  
  **Verify:** Open location overview page. Gauge renders correctly for both CPCB and EPA methodologies with appropriate colors and scale (0-500 for both, but different segment boundaries).

- [ ] **27. Display methodology and source type in location overview**
  
  Update overview page/component to show:
  1. AQI methodology name prominently (e.g., "US EPA Air Quality Index")
  2. Source type badge ("Station Observation" vs "Model Estimate")
  3. Methodology version in tooltip or details section
  4. When unavailable, show: "AQI calculation not available. Supported methodologies: CPCB (India), US EPA (United States), European AQI (EU countries)."
  
  **Files:** `frontend/src/app/locations/[id]/page.tsx` (or equivalent Next.js page)
  
  **Verify:** Navigate to location pages for Delhi, New York (create test location), and a city in unsupported country (e.g., Tokyo). Each displays correct methodology or unavailable message.

- [ ] **28. Update pollutant cards to show when AQI is unavailable**
  
  When `aqi.available === false`, display prominent message in AQI card:
  - If `availability_status === "unsupported_methodology"`: "AQI not available for this location. Displaying raw pollutant concentrations."
  - If `availability_status === "insufficient_coverage"`: "Not enough data to calculate AQI. At least 3 pollutants including PM required."
  - If `availability_status === "missing_pollutants"`: "Key pollutants unavailable for AQI calculation."
  
  Show individual pollutant cards below with concentrations and units.
  
  **Files:** `frontend/src/components/PollutantCard.tsx`, overview page
  
  **Verify:** Create test location in unsupported country with pollutant data. Page shows unavailable message and pollutant concentrations without AQI value.

- [ ] **29. Update health advice display to use methodology-specific messages**
  
  Health advice component should display messages returned by backend (already methodology-aware from backend step 20). Verify frontend doesn't override or transform these messages. Display category name as returned by API (e.g., "Unhealthy for Sensitive Groups" for EPA vs "Moderate" for CPCB).
  
  **Files:** `frontend/src/components/HealthAdvice.tsx` (or equivalent)
  
  **Verify:** View health advice for locations with different methodologies. Category names and precautions match the methodology's standard terminology.

- [ ] **30. Update map markers to handle multiple AQI scales**
  
  Station map markers currently use hardcoded CPCB color ranges. Update to:
  1. Pass methodology and categories to map component
  2. Color markers based on provided category metadata
  3. Show methodology in marker popup/tooltip
  4. Handle European AQI's different scale if needed
  
  **Files:** `frontend/src/components/StationMap.tsx` (or equivalent)
  
  **Verify:** View map with stations showing different methodologies. Markers colored correctly per their methodology's scale. Popup shows methodology name.

- [ ] **31. Update analytics/comparison views for mixed methodologies**
  
  In comparison page/component:
  1. Display methodology for each compared location
  2. Show disclaimer: "These locations use different AQI standards. Values are not directly comparable." when methodologies differ
  3. Optionally, display pollutant concentrations side-by-side for actual comparison
  
  **Files:** `frontend/src/app/compare/page.tsx` (or equivalent)
  
  **Verify:** Compare Delhi (CPCB) with New York (EPA). Disclaimer appears. Both methodologies labeled. Pollutant concentrations allow meaningful comparison.

- [ ] **32. Update history charts to display methodology**
  
  Historical AQI charts should:
  1. Label Y-axis with methodology (e.g., "CPCB AQI" or "US EPA AQI")
  2. Use methodology-specific colors for category bands
  3. Note if methodology changed over time (edge case for future)
  
  **Files:** `frontend/src/components/HistoryChart.tsx` (or equivalent)
  
  **Verify:** View history page for location. Chart Y-axis and legend reflect the methodology used. Colors match category definitions.

---

### Phase 6: Testing

- [ ] **33. Write comprehensive AQI calculation tests**
  
  Create test files:
  - `backend/tests/test_cpcb_aqi.py` - All existing CPCB tests (migrate from `test_aqi.py`)
  - `backend/tests/test_us_epa_aqi.py` - EPA breakpoint tests with official examples
  - `backend/tests/test_european_aqi.py` - European thresholds with example concentrations
  
  Test cases must cover:
  - Boundary values for each breakpoint
  - Sub-index calculations
  - Overall AQI = worst pollutant
  - Missing pollutants (not replaced with 0)
  - Insufficient coverage
  - Unit conversions
  - Rounding rules
  - Negative values rejected
  
  **Files:** `backend/tests/test_cpcb_aqi.py`, `backend/tests/test_us_epa_aqi.py`, `backend/tests/test_european_aqi.py`
  
  **Verify:** Run `cd backend && source .venv/bin/activate && python -m pytest tests/test_*_aqi.py -v`. All tests pass. Coverage >80% for aqi/ module.

- [ ] **34. Write methodology resolver tests**
  
  Test `resolve_methodology()` function:
  - India country code → CPCB
  - US country code → EPA
  - All EU country codes → European
  - Non-supported countries → None
  - Edge cases: lowercase codes, empty strings, invalid codes
  
  Test `get_calculator()` factory:
  - Valid methodology → correct calculator instance
  - Invalid methodology → raises appropriate error
  
  **Files:** `backend/tests/test_resolver.py`
  
  **Verify:** Run `python -m pytest tests/test_resolver.py -v`. All tests pass.

- [ ] **35. Write integration tests for global locations**
  
  Create end-to-end test in `backend/tests/test_global_integration.py`:
  1. Mock OpenAQ and Open-Meteo responses for 6 test cities: Delhi, Mumbai (India), New York (US), London (UK), Paris (France), Tokyo (Japan)
  2. Create locations via geocoding
  3. Trigger overview API call for each
  4. Assert correct methodology selected:
     - Delhi, Mumbai → CPCB
     - New York → US EPA
     - London, Paris → European
     - Tokyo → None (unavailable, pollutants shown)
  5. Verify AQI values match expected calculations
  6. Confirm category names match methodology
  
  **Files:** `backend/tests/test_global_integration.py`
  
  **Verify:** Run `python -m pytest tests/test_global_integration.py -v`. All 6 locations process correctly with appropriate methodologies.

- [ ] **36. Write regression tests for existing Indian functionality**
  
  Ensure existing features still work:
  - Search for seeded Indian cities (Delhi, Mumbai, Bengaluru, etc.)
  - Load overview with CPCB AQI
  - View history (hourly and daily)
  - Compare multiple Indian cities
  - Export CSV with CPCB AQI
  - Map shows stations with CPCB colors
  - Pune "School Campus" station still shows unavailable AQI (no PM data)
  
  **Files:** `backend/tests/test_indian_cities_regression.py`
  
  **Verify:** Run `python -m pytest tests/test_indian_cities_regression.py -v`. All existing functionality preserved.

- [ ] **37. Test Open-Meteo model-based AQI variables (if available)**
  
  If step 16 confirmed `us_aqi` and `european_aqi` variables exist:
  1. Write tests fetching these variables for US and EU locations
  2. Store as `source_type="model"` in AQIRecord
  3. Verify frontend displays "Model Estimate" badge
  4. Ensure model AQI is separate from station-based AQI (different cache keys, different records)
  
  If variables unavailable, document and skip feature.
  
  **Files:** `backend/tests/test_openmeteo_aqi.py`
  
  **Verify:** Run `python -m pytest tests/test_openmeteo_aqi.py -v` or skip if feature unavailable.

- [ ] **38. Manual frontend testing checklist**
  
  Perform manual testing in local development environment:
  
  **Test Indian cities (CPCB)**:
  - [ ] Search Delhi → overview loads → CPCB AQI displayed → colors match existing design
  - [ ] Categories: Good, Satisfactory, Moderate, Poor, Very Poor, Severe
  - [ ] Health advice uses CPCB terminology
  - [ ] History chart shows CPCB scale (0-500)
  - [ ] Map markers use CPCB colors
  - [ ] CSV export includes "CPCB-NAQI-2014" methodology
  
  **Test US cities (EPA)**:
  - [ ] Create New York location → overview loads → US EPA AQI displayed
  - [ ] Categories: Good, Moderate, Unhealthy for Sensitive Groups, Unhealthy, Very Unhealthy, Hazardous
  - [ ] Health advice uses EPA terminology
  - [ ] Gauge uses EPA colors and breakpoints
  - [ ] "US EPA Air Quality Index" label visible
  
  **Test European cities (European AQI)**:
  - [ ] Create London location → overview loads → European AQI displayed
  - [ ] Categories: Good, Fair, Moderate, Poor, Very Poor, Extremely Poor
  - [ ] Health advice matches EEA recommendations
  - [ ] Hourly data used (not 24h average)
  
  **Test unsupported cities**:
  - [ ] Create Tokyo location → overview loads → AQI unavailable message shown
  - [ ] Pollutant concentrations displayed in cards
  - [ ] No AQI gauge or category shown
  - [ ] Message: "AQI calculation not available for this location"
  
  **Test comparison**:
  - [ ] Compare Delhi + New York → both methodologies shown → disclaimer about different standards
  - [ ] Compare Delhi + Mumbai → same methodology → no disclaimer
  
  **Files:** N/A (manual testing)
  
  **Verify:** Create testing checklist document in `.agents/tasks/manual-testing-results.md` and check off each item.

---

### Phase 7: Documentation and Final Verification

- [ ] **39. Update README with global AQI support**
  
  Update `README.md`:
  1. Change description from "Indian AQI" to "Global AQI with multi-standard support"
  2. List supported methodologies: CPCB (India), US EPA (United States), European AQI (EU countries)
  3. Update "What this version does" section to mention global location search and methodology resolution
  4. Add methodology version section explaining each standard
  5. Note that unsupported countries show pollutant data without AQI
  
  **Files:** `README.md`
  
  **Verify:** Read updated README. All claims are accurate and tested.

- [ ] **40. Update API documentation comments**
  
  Add docstrings to key functions mentioning multi-methodology support:
  - `backend/app/aqi/resolver.py` - Document country-to-methodology mapping
  - `backend/app/services/dashboard.py` - Document methodology resolution flow
  - `backend/app/routers/locations.py` - Update endpoint docs to mention methodology field
  
  **Files:** Multiple backend Python files
  
  **Verify:** Generate API docs at http://127.0.0.1:8000/docs - Swagger UI shows updated descriptions mentioning global support.

- [ ] **41. Create migration notes for deployment**
  
  Document deployment considerations in `.agents/tasks/deployment-notes.md`:
  1. Database changes are backward compatible (new columns have defaults)
  2. Existing AQI records keep working (methodology field already exists, defaults to CPCB)
  3. Cache invalidation recommended on deploy (methodology now in cache keys)
  4. No data migration scripts needed (SQLAlchemy auto-adds columns)
  5. No breaking API changes (new fields are optional/have defaults)
  6. Cloud Run and Vercel deployments work as-is
  
  **Files:** `.agents/tasks/deployment-notes.md`
  
  **Verify:** Review with deployment checklist. No actions needed beyond normal deploy process.

- [ ] **42. Run full test suite**
  
  Execute complete test suite to confirm no regressions:
  ```bash
  cd backend
  source .venv/bin/activate
  python -m pytest tests/ -v --tb=short
  ```
  
  All tests must pass. Fix any failures before proceeding.
  
  **Files:** N/A
  
  **Verify:** Test output shows 100% pass rate. No skipped tests except Open-Meteo native AQI if unavailable.

- [ ] **43. Build and verify frontend production build**
  
  Build frontend for production:
  ```bash
  cd frontend
  npm run build
  ```
  
  Build must succeed with zero errors. Warnings acceptable if not breaking.
  
  **Files:** N/A
  
  **Verify:** Build completes successfully. Output shows Next.js production build statistics.

- [ ] **44. Test with Docker Compose**
  
  Run full stack with Docker Compose to verify containerized deployment:
  ```bash
  docker compose up --build
  ```
  
  Verify:
  - Backend starts on port 8000
  - Frontend starts on port 3000
  - Can search locations globally
  - AQI calculated with correct methodology per country
  - All endpoints respond
  
  **Files:** N/A
  
  **Verify:** Both containers run. Manual testing through http://localhost:3000 shows global AQI working.

---

## Known Risks and Mitigation

### Risk 1: Open-Meteo Native AQI Variables Unavailable
**Likelihood:** Medium  
**Impact:** Low  
**Mitigation:** If `us_aqi` and `european_aqi` variables don't exist in Open-Meteo API, we simply don't use them. Feature is optional. Model-based pollutant forecasts (PM2.5, NO2, etc.) still work and can be used to estimate AQI on frontend if desired in future iteration.

### Risk 2: European AQI Hourly vs 24-Hour Averaging Mismatch
**Likelihood:** Low  
**Impact:** Medium  
**Mitigation:** European AQI explicitly uses hourly concentrations per EEA specification. Existing averaging logic in `aggregate.py` already handles 1-hour, 8-hour, and 24-hour periods. Separate code path for European methodology ensures correct period selection.

### Risk 3: Database Schema Changes Break Existing Deployments
**Likelihood:** Low  
**Impact:** High  
**Mitigation:** All new columns have sensible defaults (`source_type="observation"`, nullable fields). Existing records remain valid. SQLAlchemy auto-migration creates columns on startup. Cloud Run's ephemeral SQLite means fresh database each instance, so no migration issues.

### Risk 4: Frontend Build Breaks Due to TypeScript Type Changes
**Likelihood:** Low  
**Impact:** Medium  
**Mitigation:** New fields added as optional with default values. Existing components continue working with CPCB data. TypeScript strict mode catches issues at build time. Each frontend change includes immediate build verification.

### Risk 5: API Response Size Increases with Category Metadata
**Likelihood:** Low  
**Impact:** Low  
**Mitigation:** Category metadata adds ~500 bytes per response (6 categories × ~80 bytes each). Negligible compared to existing payload. Can be optimized later with client-side caching of category definitions per methodology if needed.

### Risk 6: Cache Invalidation Issues with Methodology in Keys
**Likelihood:** Medium  
**Impact:** Low  
**Mitigation:** Cache key change means old cached AQI records won't be found initially, triggering recalculation. This is desired behavior (old keys lacked methodology discrimination). Short TTL (30 min default) means cache naturally refreshes. Recommend manual cache clear on first deploy if possible.

### Risk 7: Mixed Methodology Comparisons Confuse Users
**Likelihood:** Medium  
**Impact:** Medium  
**Mitigation:** Explicit disclaimer when comparing locations with different methodologies. Display methodology name prominently. Show raw pollutant concentrations for actual cross-city comparison. Future enhancement: normalize to one standard for comparison view.

### Risk 8: Insufficient Test Coverage for Edge Cases
**Likelihood:** Low  
**Impact:** Medium  
**Mitigation:** Comprehensive test plan covers boundary values, missing data, unsupported countries, mixed scenarios. Manual testing checklist ensures real-world usability. Regression tests lock in existing Indian functionality.

---

## Verification Commands Summary

**Backend Tests:**
```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

**Frontend Build:**
```bash
cd frontend
npm run build
```

**Full Stack:**
```bash
docker compose up --build
```

**Database Schema Check:**
```bash
sqlite3 backend/data/airquality.db ".schema aqi_records"
```

**Manual API Test:**
```bash
# Start backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# In another terminal
curl http://localhost:8000/api/v1/locations/1/overview | jq '.aqi.methodology'
```

---

## Success Criteria

1. ✅ All existing CPCB tests pass without modification
2. ✅ New EPA and European AQI tests pass with official reference values
3. ✅ Indian cities continue showing CPCB AQI with identical results
4. ✅ US and EU locations show appropriate methodology or unavailable state
5. ✅ Frontend displays dynamic categories and colors per methodology
6. ✅ Database schema updated without breaking existing data
7. ✅ OpenAQ provider treats all countries equally
8. ✅ API responses include methodology, source type, and availability status
9. ✅ Health advice uses methodology-specific category names
10. ✅ Comparison page handles mixed methodologies gracefully
11. ✅ CSV export includes methodology column
12. ✅ Frontend production build succeeds
13. ✅ Docker Compose deployment works end-to-end
14. ✅ No breaking changes to existing API endpoints
15. ✅ Documentation updated to reflect global support

---

## Notes

- **Implementation Order:** Steps are ordered by dependency. Complete each phase before starting the next. Within a phase, steps can sometimes be parallelized (e.g., multiple calculator implementations), but test verification should happen sequentially.

- **Incremental Commits:** Commit after each completed step or logical group of steps (e.g., all of Phase 1, then Phase 2). This allows rollback to known-good states.

- **CPCB Preservation:** The existing CPCB implementation in `backend/app/aqi.py` has been tested and is known correct. When migrating to `backend/app/aqi/cpcb.py`, copy logic verbatim rather than refactoring. Only change imports and class structure.

- **Testing Philosophy:** Write tests before or alongside implementation, not after. Each calculator implementation (steps 5-6) includes creating its test file. This catches issues early.

- **Frontend Flexibility:** Frontend changes (Phase 5) can be done in parallel with backend work if working in a team. API schema must be finalized first (Phase 2) so frontend knows what fields to expect.

- **Deployment:** This implementation maintains backward compatibility. Existing Cloud Run deployment continues working. Fresh SQLite database on each cold start means schema changes apply automatically. No manual migration needed.

- **Future Enhancements:** This plan focuses on the three primary methodologies (CPCB, EPA, European). Additional standards (Australia, Canada, China) can be added later by implementing new calculators following the established pattern.
