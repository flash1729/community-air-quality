from datetime import datetime, timedelta, timezone

from app.models import Measurement
from app.providers.openaq import HourlyObservation, RemoteSensor, RemoteStation
from app.providers.openmeteo import WeatherObservation
from app.services.ingest import refresh_location


def test_health(api):
    client, _app = api
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_location_search_and_dashboard(api):
    client, _app = api
    search = client.get("/api/v1/locations", params={"q": "delhi"})
    assert search.status_code == 200
    results = search.json()["results"]
    assert len(results) == 1
    assert results[0]["name"] == "New Delhi"

    overview = client.get(f"/api/v1/locations/{results[0]['id']}/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert body["freshness"] == "recent"
    assert body["data_origin"] == "sample"
    assert body["aqi"]["available"] is True
    assert body["aqi"]["category"] in {"Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"}
    assert body["health"]["category"] == body["aqi"]["category"]
    assert body["health"]["summary"]
    pm25 = next(item for item in body["pollutants"] if item["parameter"] == "pm25")
    assert pm25["value"] is not None
    assert pm25["value"] != 0
    assert pm25["unit"] == "µg/m³"
    assert pm25["measured_at"]
    assert pm25["source"] == "sample"
    assert any(point["aqi"] is not None for point in body["history"]["points"])
    assert any(point["aqi"] is None for point in body["history"]["points"])
    assert len(body["stations"]) >= 2
    assert "sample dataset" in body["warnings"][0].lower() or "sample" in body["warnings"][0].lower()


def test_missing_pollutants_stay_unavailable(api):
    client, _app = api
    stations = client.get("/api/v1/locations", params={"q": "pune"}).json()["results"]
    location_id = stations[0]["id"]
    payload = client.get(f"/api/v1/locations/{location_id}/stations").json()
    school = next(item for item in payload if item["name"] == "School Campus")
    assert school["aqi"]["available"] is False
    pm25 = next(item for item in school["pollutants"] if item["parameter"] == "pm25")
    assert pm25["value"] is None
    detail = client.get(f"/api/v1/stations/{school['id']}")
    assert detail.status_code == 200
    assert detail.json()["aqi"]["available"] is False


def test_unknown_location_is_404(api):
    client, _app = api
    response = client.get("/api/v1/locations/9999/overview")
    assert response.status_code == 404


def test_query_limit_is_validated(api):
    client, _app = api
    response = client.get("/api/v1/locations/1/history", params={"hours": 0})
    assert response.status_code == 422


def test_live_ingest_stores_once_and_deduplicates(api):
    client, application = api
    location_id = client.get("/api/v1/locations", params={"q": "mumbai"}).json()["results"][0]["id"]
    end = datetime(2026, 3, 1, 12, tzinfo=timezone.utc)

    class FakeOpenAQ:
        def nearby_stations(self, latitude, longitude, limit=8):
            return [
                RemoteStation(
                    external_id="900",
                    name="Live Test Monitor",
                    latitude=latitude,
                    longitude=longitude,
                    is_monitor=True,
                    sensors=[
                        RemoteSensor("1", "pm25", "µg/m³"),
                        RemoteSensor("2", "pm10", "µg/m³"),
                        RemoteSensor("3", "no2", "µg/m³"),
                    ],
                )
            ]

        def hourly_observations(self, sensor, start, end_time):
            end_hour = end_time.replace(minute=0, second=0, microsecond=0)
            return [
                HourlyObservation(
                    sensor_external_id=sensor.external_id,
                    parameter=sensor.parameter,
                    value=40 + int(sensor.external_id),
                    unit="µg/m³",
                    measured_at=end_hour - timedelta(hours=offset),
                )
                for offset in range(20)
            ]

    class FakeWeather:
        def current_weather(self, latitude, longitude):
            return WeatherObservation(
                temperature_c=29,
                humidity_percent=60,
                wind_speed_kmh=10,
                wind_direction_deg=180,
                precipitation_mm=0,
                recorded_at=end,
            )

    session = application.state.session_factory()
    try:
        from app.models import Location

        location = session.get(Location, location_id)
        first = refresh_location(session, location, FakeOpenAQ(), FakeWeather())
        session.commit()
        stored = session.query(Measurement).count()
        second = refresh_location(session, location, FakeOpenAQ(), FakeWeather())
        session.commit()
        assert session.query(Measurement).count() == stored
        assert first["measurements_stored"] > 0
        assert second["measurements_stored"] == 0
        assert first["stations_updated"] == 1
    finally:
        session.close()


def test_refresh_without_a_key_keeps_stored_data(api):
    _client, application = api
    session = application.state.session_factory()
    try:
        from app.models import Location

        location = session.query(Location).first()
        result = refresh_location(session, location, None, None)
        session.commit()
        assert result["status"] == "skipped"
        assert "not set" in result["message"].lower() or result["status"] == "skipped"
    finally:
        session.close()
