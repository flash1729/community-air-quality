"""HTTP entry for the popular-city refresh.

Cloud Scheduler calls this route on the same API service that serves the dashboard.
A second container would have its own database file, and the website would not see it.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.clients import open_clients
from app.config import get_settings
from app.jobs.refresh_popular import refresh_popular_cities
from app.routers.locations import get_db

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/refresh-popular")
def refresh_popular(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    expected = settings.scheduler_token
    provided = request.headers.get("x-scheduler-token", "")
    if not expected or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Scheduler token is missing or incorrect.")
    http, openaq, weather = open_clients(settings)
    try:
        results = refresh_popular_cities(db, openaq, weather)
    finally:
        http.close()
    return {"refreshed": len(results), "results": results}
