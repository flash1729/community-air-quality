"""Seed script for community sensors.

Creates 10 virtual sensors across Bengaluru with authentication tokens.
Stores plaintext tokens in backend/data/sensor_tokens.json for simulator use.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path

import bcrypt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import create_session_factory
from app.models import CommunitySensor
from app.timeutils import utcnow

SENSORS = [
    {
        "id": "SENSOR_001",
        "name": "Koramangala Sensor 1",
        "latitude": 12.9352,
        "longitude": 77.6245,
    },
    {
        "id": "SENSOR_002",
        "name": "Indiranagar Sensor 2",
        "latitude": 12.9716,
        "longitude": 77.6412,
    },
    {
        "id": "SENSOR_003",
        "name": "HSR Layout Sensor 3",
        "latitude": 12.9116,
        "longitude": 77.6382,
    },
    {
        "id": "SENSOR_004",
        "name": "Whitefield Sensor 4",
        "latitude": 12.9698,
        "longitude": 77.7499,
    },
    {
        "id": "SENSOR_005",
        "name": "Marathahalli Sensor 5",
        "latitude": 12.9591,
        "longitude": 77.6974,
    },
    {
        "id": "SENSOR_006",
        "name": "Electronic City Sensor 6",
        "latitude": 12.8458,
        "longitude": 77.6603,
    },
    {
        "id": "SENSOR_007",
        "name": "Jayanagar Sensor 7",
        "latitude": 12.9250,
        "longitude": 77.5937,
    },
    {
        "id": "SENSOR_008",
        "name": "MG Road Sensor 8",
        "latitude": 12.9759,
        "longitude": 77.6061,
    },
    {
        "id": "SENSOR_009",
        "name": "Hebbal Sensor 9",
        "latitude": 13.0358,
        "longitude": 77.5970,
    },
    {
        "id": "SENSOR_010",
        "name": "Yelahanka Sensor 10",
        "latitude": 13.1007,
        "longitude": 77.5963,
    },
]


def seed_community_sensors(session: Session, bcrypt_rounds: int = 12) -> dict[str, str]:
    """Seed community sensors and return mapping of sensor_id to plaintext token."""
    tokens = {}
    sensors_to_add = []
    sensors_to_update = []
    
    for sensor_data in SENSORS:
        # Check if sensor already exists
        existing = session.get(CommunitySensor, sensor_data["id"])
        if existing:
            print(f"Sensor {sensor_data['id']} already exists.", end="")
            # Update source if it's NULL or empty
            if not existing.source or existing.source == '':
                existing.source = 'seed'
                existing.hardware_id = None
                existing.hardware_model = None
                existing.contributor_name = None
                sensors_to_update.append(existing)
                print(" Updating source='seed'.")
            else:
                print(" Skipping.")
            continue
        
        # Generate token and hash it using bcrypt
        token = secrets.token_urlsafe(24)
        token_hash = bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt(rounds=bcrypt_rounds)).decode('utf-8')
        
        # Store plaintext token for later export
        tokens[sensor_data["id"]] = token
        
        # Create sensor with source='seed'
        sensor = CommunitySensor(
            id=sensor_data["id"],
            name=sensor_data["name"],
            latitude=sensor_data["latitude"],
            longitude=sensor_data["longitude"],
            sensor_type="virtual",
            auth_token_hash=token_hash,
            status="active",
            source="seed",
            hardware_id=None,
            hardware_model=None,
            contributor_name=None,
            created_at=utcnow(),
            last_seen=None,
        )
        sensors_to_add.append(sensor)
    
    if sensors_to_add:
        session.add_all(sensors_to_add)
        session.commit()
        print(f"Created {len(sensors_to_add)} community sensors.")
    
    if sensors_to_update:
        session.commit()
        print(f"Updated {len(sensors_to_update)} existing sensors.")
    
    if not sensors_to_add and not sensors_to_update:
        print("No new sensors to create or update.")
    
    return tokens


def main():
    """Main entry point for seed script."""
    settings = get_settings()
    session_factory = create_session_factory(settings.database_url)
    
    with session_factory() as session:
        tokens = seed_community_sensors(session)
    
    # Write tokens to file
    if tokens:
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        
        tokens_file = data_dir / "sensor_tokens.json"
        with open(tokens_file, "w") as f:
            json.dump(tokens, f, indent=2)
        
        print(f"Wrote {len(tokens)} tokens to {tokens_file}")
    else:
        print("No new tokens to write.")


if __name__ == "__main__":
    main()
