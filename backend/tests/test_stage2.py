from datetime import datetime, timedelta, timezone
import time

from app.providers.openmeteo import AQ_FIELDS, parse_hourly_payload
from app.providers.openmeteo import ForecastPoint, WeatherObservation
from app.providers.openaq import HourlyObservation, RemoteSensor, RemoteStation


def test_model_parser_converts_carbon_monoxide_and_skips_nulls():
    hourly = {
        "time": ["2026-03-01T00:00", "2026-03-01T01:00"],
        "pm2_5": [12.5, None],
        "carbon_monoxide": [250, 1000],
    }
    points = parse_hourly_payload(hourly, AQ_FIELDS, "air_quality")
    by_key = {(point.parameter, point.forecast_for.hour): point for point in points}
    assert by_key[("pm25", 0)].value == 12.5
    assert by_key[("pm25", 0)].unit == "µg/m³"
    assert ("pm25", 1) not in by_key
    assert by_key[("co", 0)].value == 0.25
    assert by_key[("co", 0)].unit == "mg/m³"
    assert by_key[("co", 1)].value == 1.0
    assert all(point.kind == "air_quality" for point in points)


def test_history_date_range_daily_bucket_and_empty_future(api):
    client, _app = api
    location_id = client.get("/api/v1/locations", params={"q": "delhi"}).json()["results"][0]["id"]
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=1)
    hourly = client.get(
        f"/api/v1/locations/{location_id}/history",
        params={"start": start.isoformat(), "end": today.isoformat(), "bucket": "hour"},
    )
    assert hourly.status_code == 200
    hourly_body = hourly.json()
    assert hourly_body["bucket"] == "hour"
    assert len(hourly_body["points"]) == 48
    assert "not included" in hourly_body["note"].lower()
    assert any(point["pollutants"]["pm25"] not in (None, 0) for point in hourly_body["points"])

    daily = client.get(
        f"/api/v1/locations/{location_id}/history",
        params={"start": start.isoformat(), "end": today.isoformat(), "bucket": "day"},
    )
    assert daily.status_code == 200
    assert len(daily.json()["points"]) == 2
    assert daily.json()["points"][0]["pollutants"]["pm25"] not in (None, 0)

    future = today + timedelta(days=10)
    empty = client.get(
        f"/api/v1/locations/{location_id}/history",
        params={"start": future.isoformat(), "end": (future + timedelta(days=1)).isoformat(), "bucket": "day"},
    )
    assert empty.status_code == 200
    for point in empty.json()["points"]:
        assert point["aqi"] is None
        assert all(value is None for value in point["pollutants"].values())

    too_long = client.get(
        f"/api/v1/locations/{location_id}/history",
        params={"start": (today - timedelta(days=20)).isoformat(), "end": today.isoformat(), "bucket": "hour"},
    )
    assert too_long.status_code == 422


def test_compare_uses_stored_observations(api):
    client, _app = api
    delhi = client.get("/api/v1/locations", params={"q": "delhi"}).json()["results"][0]["id"]
    mumbai = client.get("/api/v1/locations", params={"q": "mumbai"}).json()["results"][0]["id"]
    response = client.get("/api/v1/compare", params={"ids": f"{delhi},{mumbai}"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["locations"]) == 2
    assert "station observations" in body["note"].lower()
    assert all(item["aqi"]["available"] for item in body["locations"])
    assert all(item["data_origin"] == "sample" for item in body["locations"])
    missing = client.get("/api/v1/compare", params={"ids": str(delhi)})
    assert missing.status_code == 422


def test_csv_export_contains_units_and_source(api):
    client, _app = api
    location_id = client.get("/api/v1/locations", params={"q": "delhi"}).json()["results"][0]["id"]
    today = datetime.now(timezone.utc).date()
    response = client.get(
        f"/api/v1/locations/{location_id}/export",
        params={"start": (today - timedelta(days=1)).isoformat(), "end": today.isoformat()},
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    text = response.text
    header, first = text.splitlines()[0], text.splitlines()[1]
    assert header.startswith("location,station,provider,parameter,value,unit,")
    assert "New Delhi" in first
    assert "sample" in text
    assert "µg/m³" in text or "ug/m" in text


def test_station_measurements_are_paged(api):
    client, _app = api
    location_id = client.get("/api/v1/locations", params={"q": "delhi"}).json()["results"][0]["id"]
    stations = client.get(f"/api/v1/locations/{location_id}/stations").json()
    station_id = stations[0]["id"]
    page = client.get(f"/api/v1/stations/{station_id}/measurements", params={"limit": 5, "parameter": "pm25"})
    assert page.status_code == 200
    body = page.json()
    assert body["limit"] == 5
    assert len(body["results"]) == 5
    assert all(item["parameter"] == "pm25" for item in body["results"])
    assert all(item["value"] != 0 for item in body["results"])


def test_forecast_is_cached_and_labeled_as_a_model(api, monkeypatch):
    client, _app = api
    location_id = client.get("/api/v1/locations", params={"q": "pune"}).json()["results"][0]["id"]
    calls = {"count": 0}
    moment = datetime(2026, 3, 2, 0, tzinfo=timezone.utc)

    def fake_air(self, latitude, longitude):
        calls["count"] += 1
        return [
            ForecastPoint("pm25", 40.0, "µg/m³", moment, "air_quality"),
            ForecastPoint("co", 0.4, "mg/m³", moment, "air_quality"),
        ]

    def fake_weather(self, latitude, longitude):
        return [ForecastPoint("temperature", 27.0, "°C", moment, "weather")]

    monkeypatch.setattr("app.providers.openmeteo.OpenMeteoClient.air_quality_forecast", fake_air)
    monkeypatch.setattr("app.providers.openmeteo.OpenMeteoClient.hourly_weather", fake_weather)

    first = client.get(f"/api/v1/locations/{location_id}/forecast")
    second = client.get(f"/api/v1/locations/{location_id}/forecast")
    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["count"] == 1
    assert first.json()["cache"] == "miss"
    assert second.json()["cache"] == "hit"
    assert "not a monitoring-station" in first.json()["note"].lower()
    assert first.json()["points"][0]["kind"] in {"air_quality", "weather"}
    assert all(point["kind"] != "observation" for point in first.json()["points"])


def test_scheduled_job_refreshes_only_popular_cities(api, monkeypatch):
    _client, application = api
    called = []

    def fake_refresh(session, location, openaq, weather, hours=48):
        called.append(location.id)
        return {
            "status": "success",
            "message": "ok",
            "stations_updated": 0,
            "measurements_stored": 0,
        }

    monkeypatch.setattr("app.jobs.refresh_popular.refresh_location", fake_refresh)
    session = application.state.session_factory()
    try:
        from app.models import Location
        from app.jobs.refresh_popular import refresh_popular_cities

        skipped = session.query(Location).filter(Location.name == "Ahmedabad").one()
        skipped.is_popular = False
        session.flush()
        popular_ids = {row.id for row in session.query(Location).filter(Location.is_popular.is_(True))}
        refresh_popular_cities(session, None, None)
        assert set(called) == popular_ids
        assert skipped.id not in called
    finally:
        session.close()


def test_metrics_describe_the_cache(api):
    client, _app = api
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["popular_locations"] == 8
    assert body["on_demand_locations"] == 0
    assert body["measurements"] > 0
    assert "stateless" in body["note"].lower()


def test_discover_reuses_a_place_at_the_same_coordinates(api):
    _client, application = api
    from app.providers.openmeteo import Place
    from app.services.dashboard import discover_location

    class Geo:
        def geocode(self, name):
            return [
                Place(
                    name=name,
                    country="India",
                    country_code="IN",
                    latitude=19.09457,
                    longitude=74.73843,
                    timezone="Asia/Kolkata",
                )
            ]

    session = application.state.session_factory()
    try:
        first = discover_location(session, "Ahmednagar", Geo())
        session.commit()
        second = discover_location(session, "Ahilyanagar", Geo())
        session.commit()
        assert len(first) == 1
        assert first[0].id == second[0].id
    finally:
        session.close()


def test_compare_fetches_a_city_with_no_stored_readings(api, monkeypatch):
    client, application = api
    from app.models import Location

    session = application.state.session_factory()
    try:
        location = Location(
            name="Testville",
            city="Testville",
            country="India",
            latitude=19.1,
            longitude=74.7,
            timezone="Asia/Kolkata",
            is_popular=False,
        )
        session.add(location)
        session.commit()
        new_id = location.id
    finally:
        session.close()

    calls = {"count": 0}
    end = datetime(2026, 3, 1, 12, tzinfo=timezone.utc)

    class FakeOpenAQ:
        def nearby_stations(self, latitude, longitude, limit=3):
            calls["count"] += 1
            return [
                RemoteStation(
                    external_id="555",
                    name="Testville Monitor",
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
                    value=42,
                    unit="µg/m³",
                    measured_at=end_hour - timedelta(hours=offset),
                )
                for offset in range(20)
            ]

    class FakeWeather:
        def current_weather(self, latitude, longitude):
            return WeatherObservation(
                temperature_c=28,
                humidity_percent=40,
                wind_speed_kmh=8,
                wind_direction_deg=90,
                precipitation_mm=0,
                recorded_at=end,
            )

    class Http:
        def close(self):
            return None

    monkeypatch.setattr(
        "app.routers.compare.open_clients",
        lambda settings: (Http(), FakeOpenAQ(), FakeWeather()),
    )
    delhi = client.get("/api/v1/locations", params={"q": "delhi"}).json()["results"][0]["id"]
    response = client.get("/api/v1/compare", params={"ids": f"{delhi},{new_id}"})
    assert response.status_code == 200
    body = response.json()
    found = next(item for item in body["locations"] if item["location"]["name"] == "Testville")
    assert found["data_origin"] == "openaq"
    assert found["summary_station"] == "Testville Monitor"
    pm25 = next(item for item in found["pollutants"] if item["parameter"] == "pm25")
    assert pm25["value"] == 42
    again = client.get("/api/v1/compare", params={"ids": f"{delhi},{new_id}"})
    assert again.status_code == 200
    assert calls["count"] == 1


def _store_old_openaq_reading(application, name: str, value: float) -> int:
    from app.models import Location, Measurement, Sensor, Station
    from app.timeutils import db_time

    session = application.state.session_factory()
    try:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        location = Location(
            name=name,
            city=name,
            country="India",
            latitude=19.2,
            longitude=74.8,
            timezone="Asia/Kolkata",
            is_popular=False,
        )
        session.add(location)
        session.flush()
        station = Station(
            location_id=location.id,
            provider="openaq",
            external_id=f"{name}-station",
            name=f"{name} Monitor",
            latitude=19.2,
            longitude=74.8,
            is_monitor=True,
        )
        session.add(station)
        session.flush()
        sensor = Sensor(station_id=station.id, external_id=f"{name}-pm25", parameter="pm25", unit="µg/m³")
        session.add(sensor)
        session.flush()
        session.add(
            Measurement(
                sensor_id=sensor.id,
                value=value,
                unit="µg/m³",
                measured_at=db_time(now),
                fetched_at=db_time(now - timedelta(hours=3)),
                source="openaq",
                averaging_period="1h",
            )
        )
        session.commit()
        return location.id
    finally:
        session.close()


def test_expired_dashboard_refreshes_once_then_reuses_the_cache(api, monkeypatch):
    client, application = api
    location_id = _store_old_openaq_reading(application, "Cacheville", 11)
    calls = {"count": 0}

    class FakeOpenAQ:
        def nearby_stations(self, latitude, longitude, limit=3):
            calls["count"] += 1
            return [
                RemoteStation(
                    external_id="Cacheville-station",
                    name="Cacheville Monitor",
                    latitude=latitude,
                    longitude=longitude,
                    is_monitor=True,
                    sensors=[RemoteSensor("cache-pm25", "pm25", "µg/m³")],
                )
            ]

        def hourly_observations(self, sensor, start, end_time):
            end_hour = end_time.replace(minute=0, second=0, microsecond=0)
            return [
                HourlyObservation(
                    sensor_external_id=sensor.external_id,
                    parameter=sensor.parameter,
                    value=77,
                    unit="µg/m³",
                    measured_at=end_hour,
                )
            ]

    class FakeWeather:
        def current_weather(self, latitude, longitude):
            return WeatherObservation(
                temperature_c=25,
                humidity_percent=40,
                wind_speed_kmh=5,
                wind_direction_deg=10,
                precipitation_mm=0,
                recorded_at=datetime.now(timezone.utc),
            )

    class Http:
        def close(self):
            return None

    monkeypatch.setattr(
        "app.clients.open_clients",
        lambda settings: (Http(), FakeOpenAQ(), FakeWeather()),
    )
    monkeypatch.setattr(
        "app.routers.locations.open_clients",
        lambda settings: (Http(), FakeOpenAQ(), FakeWeather()),
    )
    first = client.get(f"/api/v1/locations/{location_id}/overview")
    assert first.status_code == 200
    stored = next(item for item in first.json()["pollutants"] if item["parameter"] == "pm25")
    assert stored["value"] == 11
    updated = stored
    deadline = time.perf_counter() + 3
    while time.perf_counter() < deadline:
        second = client.get(f"/api/v1/locations/{location_id}/overview")
        assert second.status_code == 200
        updated = next(item for item in second.json()["pollutants"] if item["parameter"] == "pm25")
        if calls["count"] == 1 and updated["value"] == 77:
            break
        time.sleep(0.05)
    assert calls["count"] == 1
    assert updated["value"] == 77


def test_provider_failure_keeps_the_stored_reading_and_marks_it_stale(api, monkeypatch):
    client, application = api
    location_id = _store_old_openaq_reading(application, "Staleville", 11)
    calls = {"count": 0}

    class FakeOpenAQ:
        def nearby_stations(self, latitude, longitude, limit=3):
            calls["count"] += 1
            raise RuntimeError("provider down")

    class Http:
        def close(self):
            return None

    monkeypatch.setattr(
        "app.clients.open_clients",
        lambda settings: (Http(), FakeOpenAQ(), None),
    )
    monkeypatch.setattr(
        "app.routers.locations.open_clients",
        lambda settings: (Http(), FakeOpenAQ(), None),
    )
    first = client.get(f"/api/v1/locations/{location_id}/overview")
    assert first.status_code == 200
    body = first.json()
    pm25 = next(item for item in body["pollutants"] if item["parameter"] == "pm25")
    assert pm25["value"] == 11
    deadline = time.perf_counter() + 3
    while calls["count"] < 1 and time.perf_counter() < deadline:
        time.sleep(0.05)
    # The failed fetch records itself after the provider call returns.
    time.sleep(0.3)
    second = client.get(f"/api/v1/locations/{location_id}/overview")
    assert second.status_code == 200
    kept = next(item for item in second.json()["pollutants"] if item["parameter"] == "pm25")
    assert kept["value"] == 11
    assert calls["count"] == 1


def test_half_hour_reading_lands_on_the_chart_hour():
    from app.services.dashboard import value_at_hour

    hour = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
    points = [(datetime(2026, 11, 11, 12, 30, tzinfo=timezone.utc), 41.2)]
    assert value_at_hour(points, hour) == 41.2
    assert value_at_hour(points, hour.replace(hour=11)) is None

