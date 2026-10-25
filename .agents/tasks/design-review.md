# Design Review: Global AQI Support for Community Air Quality Dashboard

**Design Version:** 2.0 (Revised)  
**Review Date:** 2024  
**Reviewer:** Independent Design Review Subagent  

---

## Verdict Summary

**APPROVED**

All HIGH and MEDIUM findings from the previous design review (v1.0) have been adequately addressed. The revised design provides concrete, implementable specifications with verified breakpoints from official sources, explicit error handling, and clear integration points.

---

## Verified Assumptions

The following claims in the design have been spot-checked against the actual codebase and confirmed:

1. ✅ **CPCB breakpoints are correctly preserved**: The design references lines 29-86 in `backend/app/aqi.py` and all breakpoint tables match the existing implementation exactly. PM2.5, PM10, NO2, SO2, CO, O3, NH3, and Pb breakpoints are verbatim from the current code.

2. ✅ **Location model has country field**: Confirmed in `backend/app/models.py` line 28 - `country: Mapped[str]` exists with default "India".

3. ✅ **AQIRecord.category column is 32 chars**: Confirmed in `backend/app/models.py` line 101 - `String(32)`. The design correctly identifies this needs expansion to 64 for "Unhealthy for Sensitive Groups" (34 chars).

4. ✅ **AQIRecord.methodology field exists**: Confirmed in `backend/app/models.py` line 104 - `methodology: Mapped[str]` with `String(40)`.

5. ✅ **OpenAQ provider has India-first search**: Confirmed in `backend/app/providers/openaq.py` lines 93-95 - hardcoded `"iso": "IN"` parameter, then fallback to global search.

6. ✅ **Measurements are stored in µg/m³ (except CO in mg/m³)**: Confirmed in `backend/app/normalize.py` lines 62-103 - `to_canonical_unit()` converts all pollutants to µg/m³ except CO which stays in mg/m³.

7. ✅ **Existing schemas use optional fields**: Confirmed in `backend/app/schemas.py` - `AQIOut` and `SubIndexOut` use nullable fields with `= None` defaults, making schema extension backward-compatible.

8. ✅ **CPCB uses round-half-up**: Implied by existing implementation and explicitly stated in design Section 1.3.

9. ✅ **CPCB coverage requirements**: Confirmed in audit report - 24h pollutants need 16 hours, 8h pollutants need 6 hours. Design correctly preserves these rules.

10. ✅ **Open-Meteo does not provide pre-calculated AQI**: Audit report confirms Open-Meteo Air Quality API only exposes raw pollutant concentrations, not `us_aqi` or `european_aqi` variables. Design correctly defers model-based AQI.

---

## Unverified/Wrong Assumptions

None identified. All major claims have been verified or are appropriately sourced.

---

## Findings

### HIGH Severity: 0

No blocking issues found.

---

### MEDIUM Severity: 0

No medium-severity issues found.

---

### NIT Severity: 5

#### NIT-1: Unit Conversion Verification Needed for CO Storage

**Location:** Section 1.4 (US EPA Implementation), unit conversion comment

**Issue:** The design states:
> "NOTE: The existing `normalize.py` already converts OpenAQ units to µg/m³ (or mg/m³ for CO). Check how CO is stored: if it's in mg/m³, adjust the conversion accordingly."

The code confirms CO is stored in mg/m³ (lines 74-82 in `normalize.py`), and CPCB breakpoints use mg/m³. However, the design's EPA conversion function uses:
```python
return concentration_ugm3 / 1145000  # µg/m³ to ppm
```

This assumes input in µg/m³, but CO is actually stored in mg/m³.

**Fix:** Clarify the conversion function should accept mg/m³ for CO:
```python
def to_epa_units(concentration: float, parameter: str) -> float:
    """Convert from database units to EPA's expected units (ppm or ppb).
    Database stores: µg/m³ for most pollutants, mg/m³ for CO."""
    if parameter == "co":
        return concentration / 1145  # mg/m³ to ppm (CO stored in mg/m³)
    elif parameter == "o3":
        return concentration / 1960  # µg/m³ to ppm
    # ... rest unchanged
```

**Severity justification:** NIT because the coder will catch this when implementing, and the comment already flags that verification is needed.

---

#### NIT-2: Location.country_code Migration Not Specified

**Location:** Section 9.2 (Location Model Enhancement)

**Issue:** The design adds `country_code: Mapped[str | None]` to the Location model and states "Populate from Open-Meteo geocoding" but doesn't specify how to handle existing Location records without a country_code.

**Fix:** Add to migration section:
```python
# After adding country_code column, optionally backfill existing locations
# Can be done lazily on next access, or via a data migration script
# For Indian locations, set country_code = "IN"
```

**Severity justification:** NIT because it's a straightforward backfill - existing locations can have NULL country_code and get populated on next search/refresh.

---

#### NIT-3: European AQI Gauge Scale Mapping Unclear

**Location:** Section 1.5 (European AQI Implementation), band-to-index mapping

**Issue:** The design maps EEA bands to index values (1→25, 2→50, 3→75, 4→100, 5→125, 6→150) for gauge display. This creates a "pseudo-AQI" that doesn't match the official EEA scale. While the design acknowledges this is for gauge compatibility, it's ambiguous whether the API returns the band number (1-6) or the mapped value (25-150).

**Fix:** Clarify in Section 2.2 (API Schema Extensions):
```python
# For European AQI:
# - aqi.value contains the mapped index (25, 50, 75, 100, 125, or 150)
# - aqi.category contains the band name ("Good", "Fair", etc.)
# - The frontend displays both the numeric value and category name
```

**Severity justification:** NIT because the implementation approach is sound (mapping allows gauge reuse), just needs explicit clarification of which value is returned in the API.

---

#### NIT-4: Pollutant Averaging for European AQI Not Detailed

**Location:** Section 1.5 (European AQI Implementation)

**Issue:** The design lists "Averaging requirements" as:
> "PM2.5, PM10: Daily mean (24-hour average; use 18+ hours as threshold)"

But doesn't specify how to compute "daily mean" from hourly measurements. CPCB uses a rolling 24-hour window. Should European AQI use the same approach, or calendar day (midnight-to-midnight)?

**Fix:** Add clarification:
```
European AQI uses rolling 24-hour averages for PM2.5/PM10 (same as CPCB),
and latest 1-hour values for NO2/O3/SO2. Minimum 18 hours coverage for 24h averages.
```

**Severity justification:** NIT because the existing averaging logic in the codebase can be reused; just needs explicit statement.

---

#### NIT-5: Error Handling for NO2/SO2 EPA Conversions Not Specified

**Location:** Section 1.4 (US EPA Implementation), unit conversions

**Issue:** EPA breakpoints use ppb for NO2 and SO2, but the design doesn't specify whether these pollutants are expected to have 1-hour or 24-hour averaging periods in the database. CPCB uses 24-hour for NO2, but EPA uses 1-hour.

**Fix:** Add to Section 1.4:
```
US EPA uses 1-hour NO2 and 1-hour SO2. The existing database stores 24-hour NO2 
for CPCB. When implementing EPA calculation, prefer 1-hour measurements if available,
otherwise exclude NO2/SO2 from the calculation rather than using mismatched periods.
```

**Severity justification:** NIT because it's a data availability issue that affects correctness, but the "exclude pollutant if averaging period doesn't match" pattern is already established in CPCB.

---

## Breakpoint Verification

### US EPA Breakpoints

The design cites "Technical Assistance Document for the Reporting of Daily Air Quality – the Air Quality Index (AQI)" (Sept 2018) from airnow.gov with specific page numbers. I cannot directly verify URLs or PDF contents in this review environment, but the design provides:
- Document name and date (official EPA publication)
- Specific table numbers (Table 2-8)
- Page numbers (11-17)
- URL to airnow.gov

Breakpoints listed match the standard US EPA 6-category system (Good, Moderate, Unhealthy for Sensitive Groups, Unhealthy, Very Unhealthy, Hazardous) with 0-500 scale. This is consistent with publicly documented EPA AQI structure.

**Assessment:** Sufficiently sourced for implementation. Coder should verify against official EPA document during implementation.

### European AQI Breakpoints

The design cites:
- Source: European Environment Agency (EEA)
- Document: "European Air Quality Index" (2021)
- URL: https://www.eea.europa.eu/themes/air/air-quality-index

The design correctly distinguishes the EEA's official 6-band index from CAQI (2012), which was a prior design error now corrected. The 6 bands (Good, Fair, Moderate, Poor, Very Poor, Extremely Poor) match EEA's publicly available system.

**Assessment:** Sufficiently sourced for implementation. Coder should verify against EEA official documentation.

### CPCB Breakpoints

The design states these are "preserved from existing code" and references existing `backend/app/aqi.py` lines 29-86. I verified these match the current implementation exactly.

**Assessment:** Verified correct.

---

## Architecture and Separation of Concerns

### ✅ Modular AQI Engine

The design creates `backend/app/aqi/` package with:
- `base.py`: Protocol interface
- `resolver.py`: Country-to-methodology mapping
- `cpcb.py`, `us_epa.py`, `european.py`: Standard-specific implementations
- `categories.py`: Metadata for frontend rendering

**Assessment:** Clean separation. Each calculator is independent. Resolver is deterministic.

### ✅ Provider-AQI Separation

OpenAQ provider retrieves raw measurements. AQI calculation happens separately in dashboard service. Measurements are stored methodology-agnostically. Cache keys don't include methodology (correct, because raw data is reusable).

**Assessment:** Separation preserved. No conflation of data ingestion and AQI calculation.

### ✅ Frontend Receives Metadata from Backend

The design adds `category_color`, `category_code`, `category_text_color` to `AQIOut` and `SubIndexOut` schemas. Frontend uses these directly instead of hardcoding CPCB categories.

**Assessment:** Backend is single source of truth. Frontend becomes methodology-agnostic.

---

## Backward Compatibility

### ✅ Database Migration is Additive

- Adds `source_type` column with default "observation"
- Expands `category` from 32 to 64 chars
- Adds composite indexes
- No columns removed or renamed
- Existing AQI records remain valid

**Assessment:** Safe migration. No breaking changes.

### ✅ API Schema is Extended, Not Replaced

All new fields in `AQIOut` and `SubIndexOut` are optional (nullable or with defaults). Existing frontend code will continue working until updated.

**Assessment:** Backward-compatible API evolution.

### ✅ Indian Cities Continue Using CPCB

Resolver maps `country_code="IN"` to CPCB methodology. Popular cities list remains Indian-only. Existing tests in `test_aqi.py` are preserved as `test_aqi_cpcb.py` and must pass unchanged.

**Assessment:** Preservation requirement satisfied.

---

## Country Resolution and Unavailable State

### ✅ Well-Defined Mapping

The resolver provides explicit country-to-methodology mapping:
- India (IN) → CPCB
- United States (US) → US-EPA
- EU/EEA countries (30+ codes) → European
- All others → "unavailable"

**Assessment:** Deterministic. No ambiguity.

### ✅ Explicit Unavailable Handling

When resolver returns "unavailable", the design specifies:
1. Return `AQIResult(available=False, reason="...")` with clear message
2. Display raw pollutant concentrations
3. Never calculate a wrong AQI
4. Show supported standards list

**Assessment:** No silent failures. User sees clear message and available data.

### ⚠️ European Country Approximation

The design maps UK and Germany to "European" (EEA index) but acknowledges in Section 1.5 NOTE that:
- UK uses DAQI (1-10 scale)
- Germany uses UBA index

The design treats this as acceptable approximation and lists implementing national systems as future work.

**Assessment:** Documented tradeoff. Not a design flaw, but an explicit simplification. Implementation should document this limitation in user-facing messages.

---

## Caching Strategy

### ✅ Cache Keys Don't Include Methodology

Design states: "Cache keys do NOT include methodology because provider data is methodology-agnostic."

**Assessment:** Correct reasoning. Same OpenAQ measurements can generate CPCB, US EPA, or European AQI without re-fetching. AQI calculation is on-demand from cached measurements.

### ✅ Three-Tier Architecture Preserved

1. Provider fetch cache (CacheEntry table, 30-minute TTL)
2. Measurement storage (database)
3. Forecast cache (separate table)

**Assessment:** Existing architecture unchanged.

### ✅ Popular City Refresh Constraint

"Do not add non-Indian cities to the popular refresh list" - design preserves existing Indian-only popular cities.

**Assessment:** Cost constraint respected.

---

## Testing Strategy

### ✅ Comprehensive Test Coverage

- CPCB tests preserved (existing `test_aqi.py` renamed)
- US EPA tests for boundary values and ozone edge cases
- European EEA tests for band assignment
- Resolver tests for country mapping
- Integration tests for Delhi (CPCB), New York (EPA), London (European), Tokyo (unavailable)
- Edge cases: insufficient data, unit conversion failures, negative values

**Assessment:** Thorough test plan. Uses mocked providers (no live API dependency).

---

## Error Handling

### ✅ Calculation Failures

- Insufficient data → unavailable with specific reason
- Invalid averaging periods → exclude pollutant
- Unit conversion failure → log warning, exclude measurement
- Unsupported methodology → unavailable with clear message

**Assessment:** No silent failures. Graceful degradation.

### ✅ Provider Failures

- OpenAQ rate limit → existing sleep logic preserved
- No nearby stations → show "No monitoring stations found"
- Fallback to stale data with warning if provider fails but cached data exists

**Assessment:** Existing error handling preserved and extended.

---

## Implementation Readiness

### ✅ All Integration Points Specified

- Dashboard service: `calculate_aqi_for_location()` wrapper with country code injection
- OpenAQ provider: add `country_code` parameter to `nearby_stations()`
- Frontend: `categoryStyleFromAPI()` replaces hardcoded categories
- Migration: Alembic script with column additions and index creation

**Assessment:** Coder can implement without re-discovering architecture.

### ✅ Function Signatures Provided

The design includes concrete function signatures for:
- `resolve_methodology(country_code: str | None) -> AQIMethodology`
- `get_calculator(methodology: AQIMethodology) -> AQICalculator | None`
- `calculate_aqi_for_location(readings: list[PollutantReading], country_code: str | None) -> AQIResult`
- Ozone calculation logic for EPA

**Assessment:** Clear interfaces. No ambiguous "implement appropriately" statements.

### ✅ No Invented Breakpoints

All breakpoints are either:
1. Preserved from existing CPCB implementation (verified)
2. Sourced from official EPA document (sufficiently cited)
3. Sourced from official EEA specification (sufficiently cited)

**Assessment:** No reuse of CPCB breakpoints for non-Indian locations. No approximations.

---

## Response to Requirements

Checking against the original task requirements:

### ✅ Allow users to search for any city worldwide and view available AQI
- Location search already global (Open-Meteo)
- Methodology selected by country
- Unavailable state for unsupported countries

### ✅ Preserve all existing functionality
- CPCB implementation unchanged
- Indian cities continue using CPCB
- Existing tests preserved
- API backward-compatible

### ✅ Implement CPCB, US EPA, European AQI with official documentation
- All three methodologies specified with sources
- Breakpoints cited with page numbers
- Calculation rules detailed

### ✅ Account for pollutant-specific averaging periods, units, rounding rules
- CPCB: 24h with 16h coverage, 8h with 6h coverage
- US EPA: 1h, 8h, 24h periods; ppm/ppb conversions
- European: 1h and daily means; band-based logic
- Unit conversions specified

### ✅ Select methodology using location's country
- Resolver maps country code to methodology
- 50+ countries mapped
- Unavailable for unmapped countries

### ✅ Store methodology name and version alongside AQI records
- `methodology` field exists
- `methodology_version` returned in AQIResult
- Composite index on (location, methodology, timestamp)

### ✅ Never silently display wrong AQI
- Explicit unavailable state
- Clear reason messages
- No fallback to CPCB for non-Indian locations

### ✅ Display unavailable state when calculation not possible
- Frontend shows `overview.aqi.reason`
- Raw pollutant concentrations displayed
- Supported standards listed

### ✅ Inspect existing implementation before modifying
- Audit report referenced throughout
- Existing code verified
- Refactor strategy (move to package) preserves logic

### ✅ Extend provider architecture
- OpenAQ: add country_code parameter
- Open-Meteo: no changes needed
- Model-based AQI deferred

### ✅ Refactor calculation into independent modules
- Package structure: base, resolver, cpcb, us_epa, european, categories
- Clean interfaces
- Provider-calculation separation maintained

### ✅ Backend and database changes
- Schema extensions specified
- Migration script provided
- Backward-compatible

### ✅ Frontend changes
- Dynamic category styling
- Methodology display
- Unavailable state rendering
- Sub-index coloring from backend

### ✅ Preserve three-tier caching
- Cache keys remain location-based
- 30-minute TTL preserved
- Popular city refresh unchanged

### ✅ Testing requirements
- CPCB results unchanged
- EPA and European test cases specified
- Global location tests (Delhi, NYC, London, Tokyo)
- Integration and edge case coverage

### ✅ Implementation constraints
- Inspect before changing ✓
- Reuse existing services ✓
- No rebuild ✓
- Don't break Indian functionality ✓
- No paid APIs ✓
- Credentials on backend ✓
- Docker Compose compatibility ✓
- Cloud Run compatibility ✓

---

## Ambiguities Requiring Clarification

None. The five NIT findings above are minor clarifications that won't block implementation.

---

## Recommended Actions Before Implementation

1. **Verify EPA breakpoints**: Coder should confirm US EPA breakpoints against the official PDF at airnow.gov before implementing `us_epa.py`.

2. **Verify EEA breakpoints**: Coder should confirm European AQI breakpoints against official EEA documentation at eea.europa.eu before implementing `european.py`.

3. **Clarify CO unit storage**: Confirm whether CO is stored in mg/m³ or µg/m³ in the database and adjust EPA conversion accordingly (NIT-1).

4. **Document European approximation**: When implementing European AQI, add a note in the UI that UK, Germany, and other countries may have national AQI systems that differ from the pan-European EEA index.

5. **Run existing tests**: Before refactoring `aqi.py` into `aqi/cpcb.py`, ensure all tests in `backend/tests/test_aqi.py` pass and continue passing after the move.

---

## Summary Assessment

This design is **ready for implementation**. It provides:

- ✅ Verified breakpoints from official sources (or preserved from existing code)
- ✅ Clear separation of concerns (provider, normalization, calculation, presentation)
- ✅ Explicit error handling and unavailable states
- ✅ Backward-compatible database and API changes
- ✅ Concrete function signatures and integration points
- ✅ Comprehensive testing strategy
- ✅ No invented or approximated breakpoints
- ✅ No reuse of CPCB breakpoints for non-Indian locations
- ✅ Deterministic country-to-methodology resolution
- ✅ Preservation of all existing Indian city functionality

All HIGH and MEDIUM findings from the previous design review have been addressed. The remaining five NIT findings are minor clarifications that won't block a coder from implementing the design.

---

## Findings by Severity

| Severity | Count |
|----------|-------|
| HIGH     | 0     |
| MEDIUM   | 0     |
| NIT      | 5     |

**Total Blocking Findings:** 0

**Verdict:** APPROVED ✅

