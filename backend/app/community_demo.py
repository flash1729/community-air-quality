"""Server-side demo readings for community sensors (COMMUNITY_DEMO_MODE).

The deployed API scales to zero and has no simulator process, so in demo mode the
read endpoints call ensure_demo_readings() to fill in the readings a device would
have sent since the last read. Rows are stored with quality_status='simulated'
so they stay distinguishable from real device data ('accepted').
"""

from __future__ import annotations

import random
import threading
import time
import zlib
from datetime import datetime, timezone

from sqlalchemy import desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import CommunitySensor, CommunitySensorReading
from app.simulator.virtual_sensors import random_bengaluru_location
from app.timeutils import as_utc, utcnow

QUALITY_STATUS = "simulated"
# One reading per minute keeps last_seen inside the frontend's 2-minute online window.
INTERVAL_SECONDS = 60
INITIAL_HISTORY_ROWS = 120  # two hours on first touch
MAX_BACKFILL_ROWS = 60  # cap per sensor per call after that
THROTTLE_SECONDS = 3.0

_lock = threading.Lock()
_last_run: dict[str, float] = {}


def _seed(*parts: object) -> int:
    return zlib.crc32(":".join(str(p) for p in parts).encode())


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _baseline(sensor_id: str) -> dict[str, float]:
    rng = random.Random(_seed(sensor_id))
    return {
        "pm25": rng.uniform(25, 90),
        "temperature": rng.uniform(23, 29),
        "humidity": rng.uniform(45, 75),
        "pm10_ratio": rng.uniform(1.4, 1.9),
    }


def _step(sensor_id: str, slot: int, state: dict[str, float], base: dict[str, float]) -> dict[str, float]:
    """Advance a mean-reverting random walk by one interval, seeded per sensor and slot."""
    rng = random.Random(_seed(sensor_id, slot))
    pm25 = _clamp(state["pm25"] + 0.15 * (base["pm25"] - state["pm25"]) + rng.gauss(0, 3), 15, 120)
    temperature = _clamp(
        state["temperature"] + 0.1 * (base["temperature"] - state["temperature"]) + rng.gauss(0, 0.15), 20, 32
    )
    humidity = _clamp(state["humidity"] + 0.1 * (base["humidity"] - state["humidity"]) + rng.gauss(0, 0.6), 35, 85)
    ratio = _clamp(base["pm10_ratio"] + rng.gauss(0, 0.05), 1.3, 2.0)
    return {"pm25": pm25, "pm10": pm25 * ratio, "temperature": temperature, "humidity": humidity}


def _fill_sensor(session: Session, sensor: CommunitySensor, now_slot: int) -> int:
    latest = session.scalar(
        select(CommunitySensorReading)
        .where(CommunitySensorReading.sensor_id == sensor.id)
        .order_by(desc(CommunitySensorReading.recorded_at))
        .limit(1)
    )
    base = _baseline(sensor.id)
    if latest is None:
        first_slot = now_slot - (INITIAL_HISTORY_ROWS - 1) * INTERVAL_SECONDS
        state = {"pm25": base["pm25"], "temperature": base["temperature"], "humidity": base["humidity"]}
    else:
        latest_ts = int(as_utc(latest.recorded_at).timestamp())
        next_slot = latest_ts - latest_ts % INTERVAL_SECONDS + INTERVAL_SECONDS
        first_slot = max(next_slot, now_slot - (MAX_BACKFILL_ROWS - 1) * INTERVAL_SECONDS)
        state = {
            "pm25": _clamp(latest.pm25, 15, 120),
            "temperature": _clamp(latest.temperature if latest.temperature is not None else base["temperature"], 20, 32),
            "humidity": _clamp(latest.humidity if latest.humidity is not None else base["humidity"], 35, 85),
        }
    if first_slot > now_slot:
        return 0

    max_seq = session.scalar(
        select(func.max(CommunitySensorReading.sequence_number)).where(CommunitySensorReading.sensor_id == sensor.id)
    ) or 0
    count = 0
    recorded_at = None
    for slot in range(first_slot, now_slot + 1, INTERVAL_SECONDS):
        state = _step(sensor.id, slot, state, base)
        recorded_at = datetime.fromtimestamp(slot, tz=timezone.utc)
        count += 1
        session.add(
            CommunitySensorReading(
                sensor_id=sensor.id,
                sequence_number=max_seq + count,
                pm25=round(state["pm25"], 1),
                pm10=round(state["pm10"], 1),
                temperature=round(state["temperature"], 1),
                humidity=round(state["humidity"], 1),
                latitude=sensor.latitude,
                longitude=sensor.longitude,
                recorded_at=recorded_at,
                received_at=recorded_at,
                quality_status=QUALITY_STATUS,
            )
        )
    # Same sensor updates the ingestion endpoint makes for an accepted reading.
    sensor.last_seen = recorded_at
    return count


def ensure_demo_readings(session: Session) -> int:
    """Assign locations and backfill simulated readings for active sensors. Returns rows added.

    Does nothing unless COMMUNITY_DEMO_MODE is on. Runs at most once every few
    seconds per database, unless a sensor is still waiting for a location.
    """
    if not get_settings().community_demo_mode:
        return 0
    if not _lock.acquire(blocking=False):
        return 0  # another request in this process is already filling
    try:
        key = str(session.get_bind().url)
        started = time.monotonic()
        if started - _last_run.get(key, float("-inf")) < THROTTLE_SECONDS:
            unlocated = session.scalar(
                select(func.count())
                .select_from(CommunitySensor)
                .where(CommunitySensor.status == "active")
                .where(or_(CommunitySensor.latitude.is_(None), CommunitySensor.longitude.is_(None)))
            )
            if not unlocated:
                return 0

        sensors = session.scalars(select(CommunitySensor).where(CommunitySensor.status == "active")).all()
        taken = [(s.latitude, s.longitude) for s in sensors if s.latitude is not None and s.longitude is not None]
        now_ts = int(utcnow().timestamp())
        now_slot = now_ts - now_ts % INTERVAL_SECONDS
        added = 0
        for sensor in sensors:
            if sensor.latitude is None or sensor.longitude is None:
                location = random_bengaluru_location(taken, random.Random(_seed(sensor.id, "location")))
                sensor.latitude = location["latitude"]
                sensor.longitude = location["longitude"]
                taken.append((sensor.latitude, sensor.longitude))
            added += _fill_sensor(session, sensor, now_slot)
        try:
            session.commit()
        except IntegrityError:
            # Another process inserted the same sequence numbers first; its rows win.
            session.rollback()
            return 0
        _last_run[key] = started
        return added
    finally:
        _lock.release()
