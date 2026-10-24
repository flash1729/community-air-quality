from fastapi import APIRouter, Depends, HTTPException, Query

from app.clients import open_clients
from app.config import get_settings
from app.schemas import CompareOut
from app.services.analytics import compare_locations

from app.routers.locations import get_db

router = APIRouter(tags=["compare"])


@router.get("/compare", response_model=CompareOut)
def compare(
    ids: str = Query(..., min_length=1, max_length=40),
    db=Depends(get_db),
):
    parsed: list[int] = []
    for piece in ids.split(","):
        piece = piece.strip()
        if not piece:
            continue
        if not piece.isdigit():
            raise HTTPException(status_code=422, detail="ids must be a comma-separated list of location ids.")
        location_id = int(piece)
        if location_id not in parsed:
            parsed.append(location_id)
    if len(parsed) < 2:
        raise HTTPException(status_code=422, detail="Select at least two locations.")
    if len(parsed) > 4:
        raise HTTPException(status_code=422, detail="Compare at most four locations at a time.")
    settings = get_settings()
    http, openaq, weather = open_clients(settings)
    try:
        return compare_locations(db, parsed, settings, openaq=openaq, weather_client=weather)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        http.close()
