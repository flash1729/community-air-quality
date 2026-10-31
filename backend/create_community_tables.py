#!/usr/bin/env python3
"""
Script to create community sensor tables in the database.
Run this if the backend was started before the community sensor feature was added.
"""

from sqlalchemy import create_engine
from app.models import Base
from app.config import get_settings

def main():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    # Create all tables (only creates missing ones)
    Base.metadata.create_all(engine)
    
    print("✓ Community sensor tables created successfully")
    print("  - community_sensors")
    print("  - community_sensor_readings")

if __name__ == "__main__":
    main()
