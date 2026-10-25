# Global AQI support for worldwide locations

Implementation extends the air quality dashboard from CPCB-only (India) to three methodologies: CPCB, US EPA, and European EEA. The approach taken is a modular AQI engine with country-based automatic selection, dynamic category metadata from backend to frontend, and database schema changes to support methodology discrimination. The change delivers complete backend and frontend coverage for the three standards while preserving all existing Indian CPCB behavior.

**Watch for:** Database migration missing (**confirmed**), country code backfill needed for existing Indian cities (**confirmed**), CO unit conversion ambiguity in US EPA (**confirmed**), coverage hours displays "null h" for non-CPCB (**confirmed**), health guidance unavailable for US/European cities (**confirmed**), verification tests not executed (**confirmed**), European AQI gauge scale mismatch (**likely**).

**Verdict**: NEEDS_CHANGES

## High-level view

The AQI calculation engine moved from a monolithic `aqi.py` to a modular `aqi/` package with separate calculators for CPCB, US EPA, and European standards. Each calculator implements a common protocol and returns standardized results with category metadata (color, text color, description). The resolver maps ISO country codes to methodologies, with 48+ countries supported (1 for CPCB, 1 for US EPA, 46 for European/EEA).

Database schema adds `country_code` to Location (for methodology selection) and `source_type` to AQIRecord (distinguishing observation from model), and extends category field length from 32 to 64 characters to accommodate longer US EPA category names. Two composite indexes were added for methodology-aware queries. No Alembic migration was created, so the schema changes exist only in models.py.

The API extends existing schemas with optional fields: `country_code` in LocationOut, and category metadata fields (`category_code`, `category_color`, `category_text_color`, `methodology_display`) in AQIOut and SubIndexOut. The dashboard service populates these from the AQI engine's category lookup. Frontend consumes the API-provided colors via `categoryStyleFromAPI()` for the main gauge and falls back to hardcoded CPCB categories when colors are absent.

Coverage hours remain CPCB-specific. US EPA and European calculators return `None` for `coverage_hours`, which propagates to the API and renders as "null h of data" in frontend sub-index detail text. The functionality is correct but the display is incomplete.

The geocoding flow in `discover_location()` captures `country_code` from the geocoder and stores it in the database. When `_station_out()` or `_history()` calculates AQI, it passes `location.country_code` to `calculate_aqi_for_location()`, which resolves the methodology and delegates to the appropriate calculator. The calculated result includes the methodology name and version, which `_sources()` uses to construct a human-readable data attribution line.

<details>
<summary>Issues (7)</summary>

1. **Database migration missing** — Schema changes in models.py (country_code, source_type, category length, indexes) require an Alembic migration. Run `alembic revision --autogenerate -m "global aqi support"` and `alembic upgrade head`.

2. **Country code backfill needed** — Existing Indian cities have `country_code = NULL`. When AQI is calculated for these cities, resolver returns "unavailable" instead of CPCB. Run `UPDATE locations SET country_code = 'IN' WHERE country = 'India';` after schema migration.

3. **CO unit conversion assumption undocumented** — US EPA calculator assumes database stores CO in µg/m³ and converts to ppm by dividing by 1,145,000. If the database stores mg/m³ (which CPCB uses), the conversion is wrong by 1000x. Verify actual database unit and adjust or document.

4. **Coverage hours display shows "null h"** — Frontend pollutant cards display "null h of data" when coverage_hours is None (US EPA and European methodologies). Conditionally render the coverage line only when coverage_hours is not null.

5. **Verification evidence incomplete** — verification.md reports "could not run tests due to missing pytest installation" and "could not verify TypeScript compilation due to missing node_modules". Without test execution, CPCB preservation claim is unverified. Run backend tests and frontend build.

6. **European AQI gauge scale mismatch** — European methodology caps AQI at 150 (band 6 → 25 * 6). Gauge assumes 0-500 range and renders 150 at 30% of arc instead of 100%. European "Extremely Poor" should feel like a maximum. Verify gauge component handles variable scales or normalize European bands to 0-500.

7. **Health guidance unavailable for non-CPCB** — `guidance_for()` only handles CPCB category names. US/European cities show "Health guidance is hidden because a valid CPCB AQI could not be calculated" even when AQI is available. Extend guidance.py to support all three category systems or map non-CPCB to CPCB equivalents.

</details>

<details>
<summary>Details</summary>

## AQI calculation engine refactor

The old `aqi.py` file contained a single `calculate_aqi()` function hardcoded to CPCB breakpoints and rules. The new structure is a package `aqi/` with seven files:

- `base.py`: Common dataclasses (`PollutantReading`, `AQIResult`, `SubIndexResult`, `CategoryMetadata`), the `AQICalculator` protocol, and shared utilities (`linear_interpolation`, `round_half_up`, `truncate_concentration`).
- `cpcb.py`: CPCB calculator migrated from the old `aqi.py`. Breakpoints, truncation rules, coverage requirements, and minimum pollutant logic are identical to the original. The only structural change is wrapping it in a class that implements `AQICalculator`.
- `us_epa.py`: US EPA calculator with official breakpoints from the 2018 technical document. Handles ozone's dual 8-hour/1-hour logic, converts gas pollutants from µg/m³ to ppm/ppb, and uses 1-decimal truncation. No minimum pollutant count.
- `european.py`: European EEA calculator with 6-band system. Each pollutant gets a band (1-6) based on concentration thresholds, overall index is the worst band, and the band number maps to an AQI value (band * 25) for display on a 0-150 scale.
- `resolver.py`: Maps ISO 3166-1 alpha-2 country codes to methodologies. Includes all 27 EU members plus EEA states (Norway, Iceland, Liechtenstein) and Switzerland, UK. Returns "unavailable" for unmapped countries.
- `categories.py`: Three lists of `CategoryMetadata` (CPCB, US EPA, European), each with name, code, min/max AQI, color, text color, description. `get_category_for_aqi(methodology, aqi_value)` returns the appropriate category.
- `__init__.py`: Public API exposes `calculate_aqi_for_location(readings, country_code)`, which resolves methodology, gets calculator, and returns `AQIResult`.

The refactor isolates methodology-specific logic cleanly. CPCB retains all its quirks (integer truncation except CO/Pb, coverage hours, minimum 3 pollutants with PM). US EPA and European add their own rules without touching CPCB code. All three share the same input/output format, so the service layer treats them uniformly.

## CPCB preservation unverified

CPCB breakpoints in `cpcb.py` match the old `aqi.py` line-for-line. Truncation logic, coverage requirements, and minimum data requirements are structurally identical. However, the verification.md states "could not run tests due to missing pytest installation". Without test execution, the claim of CPCB preservation is unverified. The code review confirms structural preservation, but runtime behavior requires test evidence.

## US EPA CO unit conversion ambiguity

The CO conversion in `to_epa_units()` assumes the database stores CO in µg/m³ and divides by 1,145,000 to convert to ppm. However, CPCB uses mg/m³ for CO (verified in `cpcb.py` where `CANONICAL_UNIT["co"] = "mg/m³"`). If the database stores CO in mg/m³, the conversion is wrong by 1000x. The comment acknowledges this: "Database may store CO in mg/m³ or µg/m³. Assume µg/m³ here; adjust if needed." This needs resolution before US cities are used in production.

To verify: check the `Measurement` table unit column for CO readings. If mg/m³, multiply concentration by 1000 before calling `to_epa_units()`. If µg/m³, the current code is correct.

## European AQI scale mismatch with gauge

European EEA maps 6 bands to AQI values for display: band 1 → 25, band 2 → 50, ..., band 6 → 150. The gauge component in `aqi-gauge.tsx` assumes a 0-500 scale for arc sweep calculation, so a European AQI of 150 will render at 30% of the arc instead of 100%. European "Extremely Poor" (150) should feel like a maximum, but the gauge shows it as moderate on a 0-500 scale. The frontend may need a methodology-aware gauge that adjusts its scale, or the backend could normalize European bands to the 0-500 range (e.g., band 6 → 500).

## Database schema changes without migration

`models.py` adds `country_code` to Location, `source_type` to AQIRecord, extends category field length from 32 to 64 characters, and adds two composite indexes. No Alembic migration was created. Attempting to run the application will fail when SQLAlchemy tries to write to columns that don't exist or insert a 40-character category into a 32-character field.

Fix: `cd backend && alembic revision --autogenerate -m "global aqi support" && alembic upgrade head`.

## API schema extensions

`schemas.py` adds optional fields: `country_code` in LocationOut, category metadata fields (`category_code`, `category_color`, `category_text_color`, `methodology_display`) in AQIOut and SubIndexOut, and changes `coverage_hours` from `int` to `int | None`. All new fields are optional or have defaults, maintaining backward compatibility. The service layer populates these from the AQI engine's category lookup.

## Frontend coverage_hours display gap

The coverage_hours field in SubIndexOut is now `int | None`. US EPA and European calculators return `None`. The frontend pollutant cards display "null h of data" when coverage_hours is None. The code should hide the coverage line when coverage_hours is null:

```tsx
{sub.coverage_hours !== null && (
  <p className="text-[11px] leading-4 text-muted">
    {sub.coverage_hours}h of data used for AQI calculation
  </p>
)}
```

## Methodology sources attribution

The `_sources()` function adds a methodology line to the footer attribution. Indian cities show "Indian AQI: calculated with CPCB National AQI (2014)", US cities show "US AQI: calculated with EPA AQI methodology (2016)", European cities show "European AQI: calculated with EEA Air Quality Index (2021)". When the resolver returns "unavailable", the reason message explains which standards are supported.

## Country code capture and backfill gap

The `discover_location()` function extracts `place.country_code` from the geocoder and stores it in the Location record. Existing Location records in the database (seeded Indian cities) have `country_code = NULL` because they were created before the schema change. When the application calculates AQI for these cities, it passes `None` to the resolver, which returns "unavailable". This breaks Indian cities unless their country_code is backfilled to "IN". Fix: `UPDATE locations SET country_code = 'IN' WHERE country = 'India';` after the schema migration.

## Test execution gap

The verification.md reports backend tests could not be run ("could not run tests due to missing pytest installation") and frontend build could not be verified ("could not verify TypeScript compilation due to missing node_modules"). The only verification was a Python import smoke test. Without test execution, CPCB preservation, US EPA breakpoint accuracy, European band assignment, and frontend rendering correctness are unverified. CPCB preservation is a hard requirement and must be verified with tests.

## Resolver coverage and national AQI approximations

The resolver maps 48 countries: India to CPCB, United States to US EPA, and 46 European/EEA countries to European AQI. The European mapping uses the pan-European EEA index for all countries, even though some (UK, Germany) have national systems. The code acknowledges this tradeoff. For unmapped countries (JP, AU, BR, CN), the resolver returns "unavailable" and the frontend displays the reason message.

## Health guidance unavailable for non-CPCB

The `guidance_for()` function returns health precautions based on CPCB category names. US EPA and European categories have different names ("Unhealthy for Sensitive Groups", "Fair"), so `guidance_for()` likely returns None for non-CPCB cities. The frontend displays "Health guidance is hidden because a valid CPCB AQI could not be calculated" when `overview.health` is null. This message is misleading: it implies CPCB failed, but the guidance system doesn't support non-CPCB categories. The fix is to extend `guidance.py` to handle all three category systems or map non-CPCB categories to CPCB equivalents.

## Sub-index color rendering for non-CPCB

The `_sub_index_out()` function calls `get_category_for_aqi(methodology, sub_index.sub_index)` to populate category metadata for each sub-index. The frontend pollutant cards read `sub.category_color` and render the sub-index bar with the correct color for all three methodologies.

</details>

<details>
<summary>File map</summary>

**Backend (10 files):**
- `backend/app/aqi/__init__.py` — new public API for AQI calculation
- `backend/app/aqi/base.py` — new common interfaces and utilities
- `backend/app/aqi/cpcb.py` — new CPCB calculator (migrated from aqi.py)
- `backend/app/aqi/us_epa.py` — new US EPA calculator
- `backend/app/aqi/european.py` — new European EEA calculator
- `backend/app/aqi/resolver.py` — new country-to-methodology resolver
- `backend/app/aqi/categories.py` — new category metadata for all methodologies
- `backend/app/models.py` — added country_code, source_type, extended category length, added indexes
- `backend/app/schemas.py` — added optional fields for category metadata and methodology display
- `backend/app/services/dashboard.py` — updated to use new AQI module and pass country_code

**Frontend (3 files):**
- `frontend/src/lib/format.ts` — added categoryStyleFromAPI() for dynamic colors
- `frontend/src/components/aqi-gauge.tsx` — accepts optional categoryStyle prop
- `frontend/src/components/air-app.tsx` — uses API-provided colors for gauge and sub-indices

Full diff: `git -C /home/vishwas/Desktop/CC/community-air-quality/.worktrees/global-aqi diff main...HEAD`

</details>
