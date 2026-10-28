from __future__ import annotations

import bcrypt
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy import select, desc
from sqlalchemy.orm import Session, selectinload

from app.models import CommunitySensor, CommunitySensorReading
from app.routers.locations import get_db
from app.schemas import (
    CommunitySensorOut,
    CommunitySensorReadingOut,
    CommunitySensorReadingSubmit,
    CommunitySensorRegister,
)
from app.timeutils import utcnow

router = APIRouter(prefix="/community", tags=["community_sensors"])


def _sensor_to_out(sensor: CommunitySensor, latest_reading: CommunitySensorReading | None = None) -> CommunitySensorOut:
    """Convert a CommunitySensor model to CommunitySensorOut schema."""
    reading_out = None
    if latest_reading:
        reading_out = CommunitySensorReadingOut(
            sensor_id=latest_reading.sensor_id,
            sequence_number=latest_reading.sequence_number,
            pm25=latest_reading.pm25,
            pm10=latest_reading.pm10,
            temperature=latest_reading.temperature,
            humidity=latest_reading.humidity,
            recorded_at=latest_reading.recorded_at,
            received_at=latest_reading.received_at,
            quality_status=latest_reading.quality_status,
        )
    return CommunitySensorOut(
        id=sensor.id,
        name=sensor.name,
        latitude=sensor.latitude,
        longitude=sensor.longitude,
        sensor_type=sensor.sensor_type,
        status=sensor.status,
        created_at=sensor.created_at,
        last_seen=sensor.last_seen,
        latest_reading=reading_out,
    )


def _verify_token(db: Session, sensor_id: str, token: str) -> CommunitySensor | None:
    """Verify bearer token and return sensor if valid."""
    sensor = db.get(CommunitySensor, sensor_id)
    if not sensor:
        return None
    if not bcrypt.checkpw(token.encode('utf-8'), sensor.auth_token_hash.encode('utf-8')):
        return None
    return sensor


@router.post("/sensors", status_code=status.HTTP_201_CREATED)
def register_sensor(data: CommunitySensorRegister, db: Session = Depends(get_db)):
    """Register a new community sensor and return authentication token."""
    # Check if sensor already exists
    existing = db.get(CommunitySensor, data.sensor_id)
    if existing:
        raise HTTPException(status_code=400, detail="Sensor ID already registered.")
    
    # Generate token and hash it using bcrypt
    token = secrets.token_urlsafe(24)
    token_hash = bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create sensor
    sensor = CommunitySensor(
        id=data.sensor_id,
        name=data.name,
        latitude=data.latitude,
        longitude=data.longitude,
        sensor_type=data.sensor_type,
        auth_token_hash=token_hash,
        status="active",
        created_at=utcnow(),
        last_seen=None,
    )
    db.add(sensor)
    db.commit()
    
    return {"sensor_id": sensor.id, "token": token, "message": "Sensor registered successfully. Store this token securely."}


@router.post("/sensors/readings", status_code=status.HTTP_201_CREATED)
def submit_reading(
    data: CommunitySensorReadingSubmit,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """Submit a new sensor reading with Bearer token authentication."""
    # Extract and verify token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    
    token = authorization.removeprefix("Bearer ").strip()
    sensor = _verify_token(db, data.sensor_id, token)
    
    if not sensor:
        raise HTTPException(status_code=401, detail="Invalid sensor ID or token.")
    
    if sensor.status != "active":
        raise HTTPException(status_code=403, detail="Sensor is not active.")
    
    # Validate measurements
    if data.pm25 < 0 or data.pm10 < 0:
        raise HTTPException(status_code=400, detail="PM2.5 and PM10 must be non-negative.")
    
    if data.pm25 >= 500:
        raise HTTPException(status_code=400, detail="PM2.5 value out of reasonable range (must be < 500).")
    
    if data.pm10 >= 1000:
        raise HTTPException(status_code=400, detail="PM10 value out of reasonable range (must be < 1000).")
    
    if data.humidity is not None and (data.humidity < 0 or data.humidity > 100):
        raise HTTPException(status_code=400, detail="Humidity must be between 0 and 100.")
    
    # Check for duplicate sequence number
    existing = db.scalar(
        select(CommunitySensorReading)
        .where(CommunitySensorReading.sensor_id == data.sensor_id)
        .where(CommunitySensorReading.sequence_number == data.sequence_number)
    )
    if existing:
        raise HTTPException(status_code=400, detail="Duplicate sequence number.")
    
    # Create reading
    reading = CommunitySensorReading(
        sensor_id=data.sensor_id,
        sequence_number=data.sequence_number,
        pm25=data.pm25,
        pm10=data.pm10,
        temperature=data.temperature,
        humidity=data.humidity,
        recorded_at=data.recorded_at,
        received_at=utcnow(),
        quality_status="accepted",
    )
    db.add(reading)
    
    # Update sensor last_seen
    sensor.last_seen = utcnow()
    
    db.commit()
    
    return {"message": "Reading accepted.", "sensor_id": data.sensor_id, "sequence_number": data.sequence_number}


@router.get("/sensors", response_model=list[CommunitySensorOut])
def list_sensors(db: Session = Depends(get_db)):
    """List all community sensors with their latest readings."""
    sensors = db.scalars(select(CommunitySensor)).all()
    
    result = []
    for sensor in sensors:
        # Get latest reading for each sensor
        latest_reading = db.scalar(
            select(CommunitySensorReading)
            .where(CommunitySensorReading.sensor_id == sensor.id)
            .order_by(desc(CommunitySensorReading.recorded_at))
            .limit(1)
        )
        result.append(_sensor_to_out(sensor, latest_reading))
    
    return result


@router.get("/sensors/{sensor_id}", response_model=CommunitySensorOut)
def get_sensor(sensor_id: str, db: Session = Depends(get_db)):
    """Get details of a specific sensor with its latest reading."""
    sensor = db.get(CommunitySensor, sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found.")
    
    latest_reading = db.scalar(
        select(CommunitySensorReading)
        .where(CommunitySensorReading.sensor_id == sensor_id)
        .order_by(desc(CommunitySensorReading.recorded_at))
        .limit(1)
    )
    
    return _sensor_to_out(sensor, latest_reading)


@router.get("/sensors/{sensor_id}/readings", response_model=list[CommunitySensorReadingOut])
def get_sensor_readings(
    sensor_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
):
    """Get paginated readings for a sensor with optional time range filtering."""
    sensor = db.get(CommunitySensor, sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found.")
    
    query = select(CommunitySensorReading).where(CommunitySensorReading.sensor_id == sensor_id)
    
    if start:
        query = query.where(CommunitySensorReading.recorded_at >= start)
    if end:
        query = query.where(CommunitySensorReading.recorded_at <= end)
    
    query = query.order_by(desc(CommunitySensorReading.recorded_at)).offset(offset).limit(limit)
    
    readings = db.scalars(query).all()
    
    return [
        CommunitySensorReadingOut(
            sensor_id=r.sensor_id,
            sequence_number=r.sequence_number,
            pm25=r.pm25,
            pm10=r.pm10,
            temperature=r.temperature,
            humidity=r.humidity,
            recorded_at=r.recorded_at,
            received_at=r.received_at,
            quality_status=r.quality_status,
        )
        for r in readings
    ]


@router.get("/map")
def get_map_data(db: Session = Depends(get_db)):
    """Get all sensors with latest readings formatted for map display."""
    sensors = db.scalars(select(CommunitySensor)).all()
    
    map_data = []
    for sensor in sensors:
        latest_reading = db.scalar(
            select(CommunitySensorReading)
            .where(CommunitySensorReading.sensor_id == sensor.id)
            .order_by(desc(CommunitySensorReading.recorded_at))
            .limit(1)
        )
        
        sensor_data = {
            "id": sensor.id,
            "name": sensor.name,
            "latitude": sensor.latitude,
            "longitude": sensor.longitude,
            "sensor_type": sensor.sensor_type,
            "status": sensor.status,
            "last_seen": sensor.last_seen,
        }
        
        if latest_reading:
            sensor_data["latest_reading"] = {
                "pm25": latest_reading.pm25,
                "pm10": latest_reading.pm10,
                "temperature": latest_reading.temperature,
                "humidity": latest_reading.humidity,
                "recorded_at": latest_reading.recorded_at,
            }
        else:
            sensor_data["latest_reading"] = None
        
        map_data.append(sensor_data)
    
    return {"sensors": map_data}
