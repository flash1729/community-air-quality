"""Turn hourly observations into the averages CPCB AQI requires."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.aqi import (
    EIGHT_HOUR,
    MIN_COVERAGE_8H,
    MIN_COVERAGE_24H,
    TWENTY_FOUR_HOUR,
    PollutantAverage,
)
from app.timeutils import as_utc

Series = dict[str, list[tuple[datetime, float]]]


def _in_window(
    points: list[tuple[datetime, float]],
    end: datetime,
    hours: int,
) -> list[float]:
    start = end - timedelta(hours=hours)
    return [value for measured_at, value in points if start < as_utc(measured_at) <= end]


def average_ending(
    points: list[tuple[datetime, float]],
    end: datetime,
    hours: int,
    minimum: int,
) -> tuple[float, int] | None:
    selected = _in_window(points, end, hours)
    if len(selected) < minimum:
        return None
    return sum(selected) / len(selected), len(selected)


def averages_at(series: Series, end: datetime) -> list[PollutantAverage]:
    """Build valid CPCB inputs for one moment. Hours with no value are omitted."""
    end = as_utc(end)
    results: list[PollutantAverage] = []
    for parameter, points in series.items():
        if parameter in TWENTY_FOUR_HOUR:
            averaged = average_ending(points, end, 24, MIN_COVERAGE_24H)
            if averaged is None:
                continue
            mean, count = averaged
            results.append(PollutantAverage(parameter, mean, "24h", count))
            continue
        if parameter == "co":
            averaged = average_ending(points, end, 8, MIN_COVERAGE_8H)
            if averaged is None:
                continue
            mean, count = averaged
            results.append(PollutantAverage(parameter, mean, "8h", count))
            continue
        if parameter == "o3":
            eight = average_ending(points, end, 8, MIN_COVERAGE_8H)
            if eight is None:
                continue
            mean, count = eight
            if mean <= 208:
                results.append(PollutantAverage(parameter, mean, "8h", count))
                continue
            one = average_ending(points, end, 1, 1)
            if one is None:
                continue
            results.append(PollutantAverage(parameter, one[0], "1h", one[1]))
    return results


def latest_value(
    points: list[tuple[datetime, float]],
    end: datetime | None = None,
) -> tuple[datetime, float] | None:
    if end is None:
        eligible = points
    else:
        end = as_utc(end)
        eligible = [(measured_at, value) for measured_at, value in points if as_utc(measured_at) <= end]
    if not eligible:
        return None
    return max(eligible, key=lambda item: as_utc(item[0]))
