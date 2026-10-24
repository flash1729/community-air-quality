from datetime import datetime, timedelta, timezone

from app.aqi import PollutantAverage, calculate_aqi, sub_index_for
from app.normalize import canonical_parameter, to_canonical_unit
from app.providers.openaq import RemoteSensor, _parse_hourly_item


def test_pm25_breakpoints_match_cpcb_examples():
    assert sub_index_for("pm25", 0) == 0
    assert sub_index_for("pm25", 30) == 50
    assert sub_index_for("pm25", 31) == 51
    assert sub_index_for("pm25", 45) == 75
    assert sub_index_for("pm25", 60) == 100
    assert sub_index_for("pm25", 90) == 200
    assert sub_index_for("pm25", 250) == 400
    assert sub_index_for("pm25", 251) == 401
    assert sub_index_for("pm25", 380) == 500
    assert sub_index_for("pm25", 500) == 500


def test_concentration_is_truncated_before_lookup():
    assert sub_index_for("pm25", 30.9) == 50
    assert sub_index_for("co", 1.09) == 50
    assert sub_index_for("co", 1.1) == 51


def test_overall_aqi_is_the_worst_valid_sub_index():
    result = calculate_aqi(
        [
            PollutantAverage("pm25", 45, "24h", 20),
            PollutantAverage("pm10", 40, "24h", 20),
            PollutantAverage("no2", 90, "24h", 18),
        ]
    )
    assert result.available is True
    assert result.aqi == sub_index_for("no2", 90)
    assert result.category == "Moderate"
    assert result.dominant_pollutants == ["NO2"]


def test_aqi_unavailable_without_three_pollutants_or_particulate():
    two = calculate_aqi(
        [
            PollutantAverage("pm25", 80, "24h", 20),
            PollutantAverage("pm10", 120, "24h", 20),
        ]
    )
    assert two.available is False
    assert two.aqi is None

    no_pm = calculate_aqi(
        [
            PollutantAverage("no2", 50, "24h", 20),
            PollutantAverage("so2", 20, "24h", 20),
            PollutantAverage("co", 0.8, "8h", 8),
        ]
    )
    assert no_pm.available is False
    assert no_pm.sub_indices


def test_short_coverage_does_not_count_and_zero_is_not_invented():
    short = calculate_aqi(
        [
            PollutantAverage("pm25", 80, "24h", 10),
            PollutantAverage("pm10", 100, "24h", 24),
            PollutantAverage("no2", 40, "24h", 24),
            PollutantAverage("so2", 10, "24h", 24),
        ]
    )
    assert short.available is True
    assert all(item.parameter != "pm25" for item in short.sub_indices)

    zero = calculate_aqi(
        [
            PollutantAverage("pm25", 0, "24h", 24),
            PollutantAverage("pm10", 0, "24h", 24),
            PollutantAverage("no2", 0, "24h", 24),
        ]
    )
    assert zero.available is True
    assert zero.aqi == 0
    assert zero.category == "Good"


def test_hourly_value_is_not_accepted_as_a_24_hour_average():
    result = calculate_aqi([PollutantAverage("pm25", 80, "1h", 1)])
    assert result.available is False
    assert result.sub_indices == []


def test_unit_conversion_and_unknown_units_are_rejected():
    assert canonical_parameter("PM2.5") == "pm25"
    assert canonical_parameter("pm2_5") == "pm25"
    assert to_canonical_unit("co", 1000, "µg/m³") == 1
    assert round(to_canonical_unit("co", 1, "ppm"), 3) == 1.145
    assert to_canonical_unit("pm25", 12, "ppm") is None
    assert to_canonical_unit("pm25", -1, "µg/m³") is None


def test_docs_example_with_spaced_units_parses():
    sensor = RemoteSensor(external_id="1", parameter="o3", unit="ppm")
    parsed = _parse_hourly_item(
        {
            "value": 0.043,
            "parameter": {"id": 10, "name": " o3", "units": " ppm", "displayName": None},
            "period": {
                "label": " raw",
                "interval": " 01:00:00",
                "datetimeTo": {"utc": " 2016-03-06T20:00:00Z", "local": " 2016-03-06T13:00:00-07:00"},
            },
        },
        sensor,
    )
    assert parsed is not None
    assert parsed.parameter == "o3"
    assert abs(parsed.value - 84.28) < 0.01


def test_missing_provider_value_is_skipped():
    sensor = RemoteSensor(external_id="9", parameter="pm25", unit="µg/m³")
    assert _parse_hourly_item({"value": None, "period": {}}, sensor) is None
    parsed = _parse_hourly_item(
        {
            "value": 41.2,
            "parameter": {"name": "pm25", "units": "µg/m³"},
            "period": {"datetimeTo": {"utc": "2026-01-01T05:00:00Z"}},
        },
        sensor,
    )
    assert parsed is not None
    assert parsed.value == 41.2
    assert parsed.measured_at == datetime(2026, 1, 1, 5, tzinfo=timezone.utc)


def test_ozone_above_208_uses_the_one_hour_value():
    from app.aggregate import averages_at

    end = datetime(2026, 1, 2, tzinfo=timezone.utc)
    points = []
    for hour in range(8, 0, -1):
        points.append((end - timedelta(hours=hour - 1), 300))
    points[-1] = (end, 220)
    series = {"o3": points}
    averages = averages_at(series, end)
    assert len(averages) == 1
    assert averages[0].averaging_period == "1h"
    assert averages[0].concentration == 220
