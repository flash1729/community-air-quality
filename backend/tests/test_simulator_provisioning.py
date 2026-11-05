import json
import random

from app.config import get_settings
from app.simulator import virtual_sensors
from app.simulator.virtual_sensors import BENGALURU_BOUNDS, random_bengaluru_location, sync_sensors

REGISTER = {
    "name": "Balcony",
    "hardware_id": "ESP32-1",
    "hardware_model": "ESP32 + PMS5003",
    "contributor_name": "Asha",
}


def test_registration_provisions_simulator_token_only_when_enabled(tmp_path, monkeypatch):
    tokens_file = tmp_path / "sim" / "sensor_tokens.json"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("SIMULATOR_TOKENS_FILE", str(tokens_file))
    from fastapi.testclient import TestClient
    from app.main import create_app

    for enabled in ("false", "true"):
        monkeypatch.setenv("SIMULATOR_AUTO_PROVISION", enabled)
        get_settings.cache_clear()
        with TestClient(create_app()) as client:
            body = client.post("/api/v1/community/sensors/register", json=REGISTER).json()
        if enabled == "false":
            assert not tokens_file.exists()
    get_settings.cache_clear()

    assert json.loads(tokens_file.read_text()) == {body["sensor_id"]: body["token"]}


def test_random_location_is_inside_bengaluru_and_away_from_taken_points():
    rng = random.Random(7)
    taken = [(12.9352, 77.6245)]
    for _ in range(50):
        loc = random_bengaluru_location(taken, rng)
        assert BENGALURU_BOUNDS["lat_min"] <= loc["latitude"] <= BENGALURU_BOUNDS["lat_max"]
        assert BENGALURU_BOUNDS["lon_min"] <= loc["longitude"] <= BENGALURU_BOUNDS["lon_max"]
        assert loc not in [{"latitude": a, "longitude": b} for a, b in taken]
        taken.append((loc["latitude"], loc["longitude"]))


def test_sync_assigns_and_persists_location_for_new_sensor(tmp_path, monkeypatch):
    tokens = tmp_path / "tokens.json"
    locations = tmp_path / "locations.json"
    tokens.write_text(json.dumps({"SENSOR_001": "a", "SENSOR_011": "b"}))
    locations.write_text(json.dumps({"SENSOR_001": {"latitude": 12.9352, "longitude": 77.6245}}))
    monkeypatch.setattr(
        virtual_sensors,
        "_fetch_sensor_metadata",
        lambda url: {"SENSOR_011": {"name": "Balcony", "latitude": None, "longitude": None, "latest_reading": None}},
    )

    sensors = sync_sensors({}, tokens, locations, "http://api", random.Random(1))
    saved = json.loads(locations.read_text())

    assert set(sensors) == {"SENSOR_001", "SENSOR_011"}
    assert saved["SENSOR_011"] == {"latitude": sensors["SENSOR_011"].latitude, "longitude": sensors["SENSOR_011"].longitude}
    assert sensors["SENSOR_011"].name == "Balcony"

    # A restart reuses the saved location instead of picking a new one.
    again = sync_sensors({}, tokens, locations, "http://api", random.Random(99))
    assert again["SENSOR_011"].latitude == sensors["SENSOR_011"].latitude
    assert again["SENSOR_011"].longitude == sensors["SENSOR_011"].longitude
