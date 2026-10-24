from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def hour_floor(value: datetime) -> datetime:
    value = as_utc(value)
    return value.replace(minute=0, second=0, microsecond=0)


def db_time(value: datetime) -> datetime:
    """Naive UTC for SQLite, which does not round-trip timezone-aware values reliably."""
    return as_utc(value).replace(tzinfo=None)
