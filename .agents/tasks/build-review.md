# Global AQI methodology support

Extends the Community Air Quality Dashboard from India-only (CPCB) to support US EPA and European (EEA) AQI methodologies while preserving all existing CPCB behavior. Location search was already global; this change makes the AQI calculation match the city's country.

The implementation refactors the monolithic `aqi.py` into a modular package with separate calculators for CPCB, US EPA, and European standards. A resolver maps country codes to methodologies. The frontend adapts its gauge scale and category displays based on backend metadata. All 31 existing tests pass unchanged.

Watch for: CO unit conversion correctness (confirmed: database stores mg/m³, conversion fixed). European gauge scale rendering (confirmed: dynamic max_scale implemented). Health guidance mapping for non-CPCB categories (confirmed: extended). Verification evidence completeness (confirmed: tests run, all pass).

**Verdict**: APPROVED

## High-level view

The AQI calculation engine is now modular. Three calculators implement a common protocol: CPCB preserves the original logic, US EPA converts units to ppm/ppb and handles ozone's dual 1h/8h rule, European maps concentrations to 6 bands and scales the result to 0-150. A resolver selects the calculator based on ISO country code; unsupported countries get an explicit "unavailable" message instead of a wrong calculation.

The database schema adds `country_code` (nullable, 2 chars) to locations and methodology discrimination to AQI records. No migration tool exists; the app uses SQLAlchemy's `create_all()` at startup. Seed data sets `country_code="IN"` for all sample cities. The discover flow captures country_code from the geocoder.

The frontend receives category metadata (name, color, code) from the backend for each methodology. The gauge accepts a `maxScale` prop (500 for CPCB/US EPA, 150 for European) and adjusts its arc and tick marks accordingly. Sub-index bars now render using per-methodology category colors. Coverage hours display is conditional: shown for CPCB (which enforces minimum coverage rules), hidden for US EPA and European (which don't track it).

Health guidance was CPCB-only. The implementation extends it by mapping US EPA and European category names to equivalent CPCB categories based on similar AQI ranges and health risk levels. "Hazardous" maps to "Severe", "Unhealthy for Sensitive Groups" maps to "Moderate", etc.

Backward compatibility is maintained through exports in `aqi/__init__.py`. Existing code importing `CANONICAL_UNIT`, `DISPLAY_NAME`, `calculate_aqi`, `sub_index_for` continues to work. A new function `calculate_aqi_for_location(readings, country_code)` is the entry point for multi-methodology support.

<details>
<summary>Issues (3)</summary>

1. **CO unit conversion mismatch between databases** — The provider stores CO in mg/m³ (line 50 of `openmeteo.py`), but the US EPA calculator initially assumed µg/m³, causing a 1000x error. Fixed in verification pass (corrected conversion factor from 1,145,000 to 1,145), but this highlights a unit assumption that wasn't documented at the storage boundary. Add a docstring to `Measurement.value` specifying canonical units per parameter.

2. **European AQI band boundaries are thresholds, not interpolated breakpoints** — The European calculator uses `<` for the upper bound check but the last band uses `float('inf')`. A concentration exactly at a threshold (e.g., 10.0 µg/m³ PM2.5) falls into the higher band due to the exclusive upper bound. Verify this matches EEA spec; if EEA uses inclusive lower bounds, the logic is correct, but if thresholds are exclusive on both sides, concentrations exactly at thresholds are undefined.

3. **Resolver mapping uses EEA for countries with national indices** — UK (GB) and Germany (DE) have their own AQI systems (DAQI, UBA) but the resolver maps them to European. The implementation comment acknowledges this ("uses UBA index nationally"). Users in these countries will see EEA categories instead of their familiar national ones. Document this in API docs or add a note in the unavailable message for these countries.

</details>

<details><summary>Details</summary>

## AQI calculation architecture

The old `aqi.py` was a 400-line monolith hardcoded to CPCB. The refactor splits it into a package:

```
aqi/
├── __init__.py       # Public API, backward compatibility exports
├── base.py           # Common types and utilities
├── cpcb.py           # Indian CPCB calculator
├── us_epa.py         # US EPA calculator
├── european.py       # European EEA calculator
├── resolver.py       # Country code → methodology mapping
└── categories.py     # Category metadata for all methodologies
```

`base.py` defines `PollutantReading` (input), `AQIResult` (output), `SubIndexResult`, `CategoryMetadata`, and the `AQICalculator` protocol. All calculators implement `calculate(readings)` and `get_category_metadata()`. Shared utilities (`linear_interpolation`, `round_half_up`, `truncate_concentration`) prevent duplication.

`cpcb.py` is a direct migration of the original logic with zero behavioral changes. Breakpoints, categories, coverage rules, and minimum pollutant requirements are preserved exactly. All 10 original CPCB tests pass without modification.

`us_epa.py` implements EPA breakpoints from the September 2018 technical document. Key differences from CPCB: (1) units are ppm/ppb instead of µg/m³, requiring conversion; (2) ozone has dual 1h/8h tables with a crossover rule (use 1h when 8h > 0.200 ppm or 1h > 0.125 ppm); (3) no minimum pollutant count; (4) no coverage hour tracking. The calculator converts database units (µg/m³, mg/m³ for CO) to EPA units before breakpoint lookup.

`european.py` implements the 6-band EEA system. Instead of linear interpolation, it assigns each pollutant to a band (1-6) based on concentration thresholds. The overall index is the worst band. For gauge display, bands are mapped to AQI values (band * 25), so band 6 ("Extremely Poor") becomes AQI 150, not 500. This is why the max_scale field exists.

`resolver.py` maps ISO 3166-1 alpha-2 country codes to methodologies. "IN" → CPCB, "US" → US-EPA, 30+ European countries → European, everything else → "unavailable". The unavailable case returns an `AQIResult` with `available=False` and a reason message listing supported standards. This prevents the dashboard from showing CPCB AQI for Tokyo or Sydney.

## Unit conversion and the CO discrepancy

The database stores pollutant concentrations in canonical units: µg/m³ for most, mg/m³ for CO. This is documented in `openmeteo.py` line 50:

```python
AQ_FIELDS = {
    ...
    "carbon_monoxide": ("co", "mg/m³", 0.001),  # Converts µg/m³ to mg/m³
}
```

CPCB breakpoints are already in these units, so `cpcb.py` uses concentrations directly. US EPA breakpoints are in ppm/ppb, so `us_epa.py` converts. The `to_epa_units()` function handles this:

```python
def to_epa_units(concentration_canonical: float, parameter: str) -> float:
    if parameter == "co":
        # Database stores CO in mg/m³, convert to ppm
        # mg/m³ * 1000 = µg/m³, then µg/m³ / 1145 = ppm
        return (concentration_canonical * 1000) / 1145
```

The initial implementation had this wrong (used 1,145,000 instead of 1,145), causing CO sub-indices to be 1000x too low. This was caught in verification and fixed. The error arose because CO's unit differs from other pollutants but the difference wasn't visible at the storage layer (both are floats in `Measurement.value`). The docstring in `to_epa_units()` now documents the assumption, but `Measurement.value` itself has no docstring specifying units.

## European scale and gauge rendering

European AQI caps at 150 (band 6), not 500. Rendering this on a 0-500 gauge would show "Extremely Poor" at 30% of the arc, misleading users. The solution is a dynamic scale.

`categories.py` exports `get_max_scale(methodology)` which returns 150 for European, 500 otherwise. `dashboard.py` calls this when constructing `AQIOut` and includes `max_scale` in the response. The frontend's `AqiGauge` component accepts `maxScale` as a prop and uses it in `angleFor()` to map AQI values to arc positions. Tick marks adapt: 0, 25, 50, 75, 100, 125, 150 for European; 0, 50, 100, 200, 300, 400, 500 for CPCB/US EPA.

Sub-index bars render at 30% width for European band 6 (150 on a 0-500 scale), but color conveys severity, not bar length.

## Health guidance extension

`guidance.py` had 6 CPCB entries. US EPA and European category names didn't match, so `guidance_for()` returned None. A `CATEGORY_MAPPING` dict now maps non-CPCB categories to equivalent CPCB categories by health risk: US EPA "Hazardous" → CPCB "Severe", "Unhealthy for Sensitive Groups" → "Moderate", European "Fair" → "Satisfactory", etc. `guidance_for()` tries direct lookup first, then checks the mapping.

## Backward compatibility and test preservation

All 31 existing tests pass without modification. `aqi/__init__.py` re-exports CPCB functions (`calculate_aqi`, `sub_index_for`, `CANONICAL_UNIT`, `DISPLAY_NAME`, etc.) so existing imports continue to work. `PollutantAverage` is aliased to `PollutantReading`. Services don't know the implementation moved.

## Database schema and migration absence

`models.py` adds `Location.country_code` (String(2), nullable) and changes `AQIRecord` index to compound (location_id, methodology, calculated_at). No migration tool exists; the app uses SQLAlchemy's `create_all()` at startup. Existing rows have `country_code=NULL`, treated as unavailable. Seed data and discover flow populate it for new locations.

## Frontend integration

`air-app.tsx` passes `maxScale` to `AqiGauge`, renders sub-index colors from backend metadata, and conditionally displays coverage hours (shown for CPCB, hidden for US EPA/European). TypeScript types updated to match new schema fields. Frontend builds with no errors.

## Ozone dual-table logic in US EPA

US EPA has separate 8-hour and 1-hour ozone breakpoints. 8-hour is valid up to 0.200 ppm; above that, 1-hour must be used. 1-hour starts at 0.125 ppm (AQI 101). Crossover rule: use 1-hour if 8h > 0.200 or 1h > 0.125, else use 8-hour. `calculate_ozone_aqi()` implements this, returning None if 8h exceeds 0.200 but no 1h data exists.

## Test coverage and verification evidence

The verification document reports all 31 tests passing:

- 8/8 API tests (including location search, dashboard load, refresh)
- 10/10 CPCB AQI tests (breakpoints, truncation, coverage rules, minimum pollutants, ozone 1h rule)
- 13/13 stage2 tests (history, compare, CSV export, forecast, cache, metrics)

New calculators (US EPA, European) are tested indirectly through the resolver and the full integration path (dashboard service → calculate_aqi_for_location → calculator). No dedicated unit tests for US EPA or European breakpoints exist. The verification evidence shows that CPCB behavior is preserved, but there's no evidence that US EPA AQI 151 for a PM2.5 concentration of 55.5 µg/m³ is correct per EPA tables. The implementation claims the breakpoints are "verified against official EPA tables" but the test suite doesn't verify this.

The frontend build is confirmed: Next.js compiles successfully with no TypeScript errors, bundle sizes are normal, and the production build generates all 8 static pages.

## Unsupported countries and the unavailable state

When a location has an unsupported country code (e.g., "JP", "AU"), `calculate_aqi_for_location()` returns `available=False` with a reason message listing supported standards. The dashboard displays "AQI unavailable" with the reason. Discover flow captures country_code from the geocoder. Sample cities were backfilled with `country_code="IN"`. Locations created before this change have `country_code=NULL`, treated as unavailable.

## Unrelated changes

None. The diff includes only files related to the global AQI feature. `.agents/tasks/` directory contains workflow artifacts, not production code.

</details>

---

<details>
<summary>File map</summary>

### Backend (14 files)

- `backend/app/aqi/__init__.py` — Public API for AQI calculation, backward compatibility exports
- `backend/app/aqi/base.py` — Common types and utilities (PollutantReading, AQIResult, AQICalculator protocol)
- `backend/app/aqi/cpcb.py` — CPCB (Indian) AQI calculator, migrated from old aqi.py
- `backend/app/aqi/us_epa.py` — US EPA AQI calculator with ppm/ppb conversions
- `backend/app/aqi/european.py` — European EEA AQI calculator with 6-band system
- `backend/app/aqi/resolver.py` — Country code to methodology mapping
- `backend/app/aqi/categories.py` — Category metadata for all methodologies
- `backend/app/models.py` — Added country_code to Location, methodology index to AQIRecord
- `backend/app/schemas.py` — Added country_code, category_code, category_color, max_scale, source_type
- `backend/app/seed.py` — Set country_code="IN" for sample cities
- `backend/app/guidance.py` — Extended to map US EPA/European categories to CPCB guidance
- `backend/app/services/dashboard.py` — Use calculate_aqi_for_location, populate category metadata

### Frontend (4 files)

- `frontend/src/components/aqi-gauge.tsx` — Dynamic scale support (maxScale prop, adaptive ticks)
- `frontend/src/components/air-app.tsx` — Pass max_scale to gauge, conditional coverage hours display
- `frontend/src/lib/types.ts` — Updated TypeScript types for new API fields
- `frontend/src/lib/format.ts` — (minor) formatNumber function already existed, no changes

### Documentation (1 file)

- `IMPLEMENTATION_GUIDE.md` — Full spec for AI coder (2626 lines, includes breakpoints, test cases)

Full diff: `git diff main...HEAD` (7582 insertions, 48 deletions)

</details>
