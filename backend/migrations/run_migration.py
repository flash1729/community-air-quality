"""Migration runner for database schema changes.

Executes SQL migration scripts against the SQLite database.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def run_migration(db_path: Path, sql_file: Path) -> None:
    """Execute SQL migration file against database."""
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)
    
    if not sql_file.exists():
        print(f"ERROR: Migration file not found at {sql_file}")
        sys.exit(1)
    
    print(f"Running migration: {sql_file.name}")
    print(f"Target database: {db_path}")
    
    # Read SQL file
    with open(sql_file, 'r') as f:
        sql_content = f.read()
    
    # Execute migration
    conn = sqlite3.connect(db_path)
    try:
        # Execute the entire script at once
        print(f"  Executing migration script...")
        conn.executescript(sql_content)
        print("✓ Migration completed successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


def main():
    """Main entry point."""
    # Determine paths
    backend_dir = Path(__file__).parent.parent
    db_path = backend_dir / "data" / "airquality.db"
    migrations_dir = Path(__file__).parent
    
    # Run the migration
    migration_file = migrations_dir / "001_add_contributed_sensor_fields.sql"
    run_migration(db_path, migration_file)
    
    # Verify schema changes
    print("\nVerifying schema changes...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check community_sensors columns
    cursor.execute("PRAGMA table_info(community_sensors)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"  community_sensors columns: {columns}")
    
    expected_new_cols = ['source', 'hardware_id', 'hardware_model', 'contributor_name']
    for col in expected_new_cols:
        if col in columns:
            print(f"  ✓ {col} column exists")
        else:
            print(f"  ✗ {col} column MISSING")
    
    # Check community_sensor_readings columns
    cursor.execute("PRAGMA table_info(community_sensor_readings)")
    reading_columns = [row[1] for row in cursor.fetchall()]
    print(f"  community_sensor_readings columns: {reading_columns}")
    
    if 'latitude' in reading_columns and 'longitude' in reading_columns:
        print(f"  ✓ latitude and longitude columns exist in readings")
    else:
        print(f"  ✗ coordinate columns MISSING in readings")
    
    # Verify existing sensors have source='seed'
    cursor.execute("SELECT id, source, latitude, longitude FROM community_sensors")
    sensors = cursor.fetchall()
    print(f"\n  Existing sensors:")
    
    invalid_coords = []
    for sensor_id, source, lat, lon in sensors:
        print(f"    {sensor_id}: source={source}, lat={lat}, lon={lon}")
        # Validate that seed sensors have valid coordinates (Finding #6)
        if source == 'seed' and (lat is None or lon is None):
            invalid_coords.append(sensor_id)
    
    if invalid_coords:
        print(f"\n  ⚠ WARNING: Seed sensors with NULL coordinates: {invalid_coords}")
        print(f"  These sensors will not appear on the map until coordinates are set.")
    
    conn.close()
    print("\n✓ Verification complete")


if __name__ == "__main__":
    main()
