from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import community_demo
from app.config import get_settings
from app.seed_community_sensors import SENSORS

REGISTER = {
    "name": "Balcony",
    "hardware_id": "ESP32-1",
    "hardware_model": "ESP32 + PMS5003",
    "contributor_name": "Asha",
}


def _client(tmp_path, monkeypatch, demo: bool):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("OPENAQ_API_KEY", "")
    monkeypatch.setenv("COMMUNITY_DEMO_MODE", "true" if demo else "false")
    monkeypatch.setenv("SIMULATOR_AUTO_PROVISION", "false")
    get_settings.cache_clear()
    community_demo._last_run.clear()
    from app.main import create_app

    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _reset_settings():
    yield
    get_settings.cache_clear()


def _in_bengaluru(lat, lon):
    return 12.85 <= lat <= 13.10 and 77.50 <= lon <= 77.75


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None, value
    return parsed


def test_demo_mode_seeds_sensors_with_recent_readings(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, demo=True) as client:
        sensors = client.get("/api/v1/community/sensors").json()

    assert {s["id"] for s in sensors} == {s["id"] for s in SENSORS}
    now = datetime.now(timezone.utc)
    for sensor in sensors:
        assert sensor["latest_reading"]["quality_status"] == "simulated"
        assert now - _parse(sensor["last_seen"]) < timedelta(minutes=2)
        _parse(sensor["latest_reading"]["recorded_at"])
        _parse(sensor["latest_reading"]["received_at"])


def test_demo_mode_locates_and_fills_new_sensor_on_next_read(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, demo=True) as client:
        client.get("/api/v1/community/sensors")  # starts the throttle window
        sensor_id = client.post("/api/v1/community/sensors/register", json=REGISTER).json()["sensor_id"]

        sensor = client.get(f"/api/v1/community/sensors/{sensor_id}").json()
        readings = client.get(f"/api/v1/community/sensors/{sensor_id}/readings?limit=50").json()
        map_ids = {s["id"] for s in client.get("/api/v1/community/map").json()["sensors"]}

    assert _in_bengaluru(sensor["latitude"], sensor["longitude"])
    assert sensor["latest_reading"] is not None
    assert sensor_id in map_ids
    assert len(readings) == 50
    sequences = [r["sequence_number"] for r in readings]
    assert sequences == sorted(sequences, reverse=True)
    assert all(15 <= r["pm25"] <= 120 and 1.3 * r["pm25"] - 0.2 <= r["pm10"] <= 2.0 * r["pm25"] + 0.2 for r in readings)
    assert all((r["latitude"], r["longitude"]) == (sensor["latitude"], sensor["longitude"]) for r in readings)


def test_demo_mode_backfills_only_elapsed_intervals(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, demo=True) as client:
        first = client.get("/api/v1/community/sensors/SENSOR_001/readings?limit=1000").json()
        community_demo._last_run.clear()
        again = client.get("/api/v1/community/sensors/SENSOR_001/readings?limit=1000").json()

    assert len(first) == community_demo.INITIAL_HISTORY_ROWS
    # A second read in the same minute adds at most the next slot.
    assert len(again) - len(first) <= 1


def test_demo_mode_off_leaves_new_sensor_without_location(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, demo=False) as client:
        sensor_id = client.post("/api/v1/community/sensors/register", json=REGISTER).json()["sensor_id"]
        sensors = client.get("/api/v1/community/sensors").json()
        readings = client.get(f"/api/v1/community/sensors/{sensor_id}/readings").json()

    assert [s["id"] for s in sensors] == [sensor_id]
    assert sensors[0]["latitude"] is None and sensors[0]["latest_reading"] is None
    assert readings == []
    _parse(sensors[0]["created_at"])
