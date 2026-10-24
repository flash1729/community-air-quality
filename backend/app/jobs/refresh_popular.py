"""Scheduled refresh for the popular-city list only.

Locally this is a separate process from the web server:

    python -m app.jobs.refresh_popular

Cloud Scheduler calls POST /api/v1/jobs/refresh-popular on this API.
The local command below runs the same function. Cities that are not marked
popular stay on the on-demand path.
"""

from __future__ import annotations

from sqlalchemy import select

from app.clients import open_clients
from app.config import get_settings
from app.database import create_session_factory
from app.models import Location
from app.services.ingest import refresh_location


def refresh_popular_cities(session, openaq, weather) -> list[dict]:
    locations = session.scalars(
        select(Location).where(Location.is_popular.is_(True)).order_by(Location.id)
    ).all()
    results = []
    for location in locations:
        outcome = refresh_location(session, location, openaq, weather)
        session.commit()
        results.append({"id": location.id, "name": location.name, **outcome})
    return results


def main() -> None:
    settings = get_settings()
    factory = create_session_factory(settings.database_url)
    session = factory()
    http, openaq, weather = open_clients(settings)
    try:
        results = refresh_popular_cities(session, openaq, weather)
    finally:
        session.close()
        http.close()
    if not results:
        print("No popular cities are configured.")
        return
    for item in results:
        print(f"{item['name']}: {item['status']} — {item['message']}")


if __name__ == "__main__":
    main()
