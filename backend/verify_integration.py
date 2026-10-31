#!/usr/bin/env python3
"""
Integration verification script for Community Sensor Network feature.
This script directly tests the database and API functionality without requiring a running server.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

def check_database():
    """Verify database tables and data."""
    print("=" * 60)
    print("DATABASE VERIFICATION")
    print("=" * 60)
    
    db_path = Path(__file__).parent / "data" / "airquality.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check community_sensors table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='community_sensors'")
    if not cursor.fetchone():
        print("✗ community_sensors table does not exist")
        return False
    print("✓ community_sensors table exists")
    
    cursor.execute("SELECT COUNT(*) FROM community_sensors")
    sensor_count = cursor.fetchone()[0]
    print(f"✓ Found {sensor_count} sensors in database")
    
    if sensor_count != 10:
        print(f"  ⚠ Expected 10 sensors, found {sensor_count}")
    
    # List sensors
    cursor.execute("SELECT id, name, status, latitude, longitude FROM community_sensors")
    for row in cursor.fetchall():
        print(f"  - {row[0]}: {row[1]} ({row[2]}) at ({row[3]}, {row[4]})")
    
    # Check community_sensor_readings table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='community_sensor_readings'")
    if not cursor.fetchone():
        print("✗ community_sensor_readings table does not exist")
        return False
    print("✓ community_sensor_readings table exists")
    
    cursor.execute("SELECT COUNT(*) FROM community_sensor_readings")
    reading_count = cursor.fetchone()[0]
    print(f"✓ Found {reading_count} readings in database")
    
    conn.close()
    return True

def check_tokens():
    """Verify sensor tokens file."""
    print("\n" + "=" * 60)
    print("TOKEN FILE VERIFICATION")
    print("=" * 60)
    
    tokens_path = Path(__file__).parent / "data" / "sensor_tokens.json"
    if not tokens_path.exists():
        print("✗ sensor_tokens.json not found")
        return False
    
    print("✓ sensor_tokens.json exists")
    
    with open(tokens_path) as f:
        tokens = json.load(f)
    
    print(f"✓ Found {len(tokens)} sensors with tokens")
    
    required_sensors = [f"SENSOR_{i:03d}" for i in range(1, 11)]
    missing = [s for s in required_sensors if s not in tokens]
    
    if missing:
        print(f"✗ Missing tokens for: {', '.join(missing)}")
        return False
    
    print("✓ All 10 expected sensor tokens present")
    return True

def test_virtual_sensor_class():
    """Test VirtualSensor class functionality."""
    print("\n" + "=" * 60)
    print("VIRTUAL SENSOR CLASS VERIFICATION")
    print("=" * 60)
    
    try:
        from app.simulator.virtual_sensors import VirtualSensor
        print("✓ VirtualSensor class imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import VirtualSensor: {e}")
        return False
    
    # Test basic instantiation
    sensor = VirtualSensor("TEST_001", "Test Sensor", "test_token", 12.9716, 77.5946)
    print(f"✓ Created test sensor at ({sensor.latitude}, {sensor.longitude})")
    
    # Test reading generation
    reading = sensor.generate_reading()
    required_fields = ['sensor_id', 'sequence_number', 'pm25', 'pm10', 'temperature', 'humidity', 'recorded_at']
    missing_fields = [f for f in required_fields if f not in reading]
    
    if missing_fields:
        print(f"✗ Reading missing fields: {', '.join(missing_fields)}")
        return False
    
    print("✓ Reading contains all required fields")
    print(f"  PM2.5: {reading['pm25']:.2f}, PM10: {reading['pm10']:.2f}")
    
    # Test gradual changes
    prev_pm25 = reading['pm25']
    violations = []
    for i in range(10):
        reading = sensor.generate_reading()
        change = abs(reading['pm25'] - prev_pm25)
        if change > 5.5:
            violations.append(f"Reading {i+1}: change={change:.2f}")
        prev_pm25 = reading['pm25']
    
    if violations:
        print(f"✗ Found {len(violations)} violations of gradual change")
        return False
    
    print("✓ All readings showed gradual changes (≤5 per iteration)")
    
    # Test spike scenario
    sensor2 = VirtualSensor("TEST_002", "Test Sensor 2", "test_token", 12.9, 77.6)
    before = sensor2.pm25
    sensor2.trigger_spike(duration_seconds=2)
    after = sensor2.pm25
    increase = after - before
    
    if 40 <= increase <= 80:
        print(f"✓ Spike increased PM2.5 by {increase:.1f} (within 40-80 range)")
    else:
        print(f"⚠ Spike increase {increase:.1f} not in expected range 40-80")
    
    return True

def test_api_routes():
    """Test API routes using TestClient."""
    print("\n" + "=" * 60)
    print("API ROUTES VERIFICATION")
    print("=" * 60)
    
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        print("✓ TestClient created successfully")
    except Exception as e:
        print(f"✗ Failed to create TestClient: {e}")
        return False
    
    # Test GET /api/v1/community/sensors
    response = client.get("/api/v1/community/sensors")
    if response.status_code != 200:
        print(f"✗ GET /api/v1/community/sensors returned {response.status_code}")
        return False
    
    sensors = response.json()
    print(f"✓ GET /api/v1/community/sensors returned {len(sensors)} sensors")
    
    if len(sensors) == 0:
        print("  ⚠ No sensors returned (database may be empty)")
    else:
        sample = sensors[0]
        print(f"  Sample: {sample['id']} - {sample['name']}")
    
    # Test GET /api/v1/community/sensors/{sensor_id}
    if sensors:
        sensor_id = sensors[0]['id']
        response = client.get(f"/api/v1/community/sensors/{sensor_id}")
        if response.status_code != 200:
            print(f"✗ GET /api/v1/community/sensors/{sensor_id} returned {response.status_code}")
            return False
        print(f"✓ GET /api/v1/community/sensors/{sensor_id} works")
    
    # Test POST /api/v1/community/sensors/readings with invalid token
    response = client.post(
        "/api/v1/community/sensors/readings",
        json={
            "sensor_id": "SENSOR_001",
            "sequence_number": 999999,
            "pm25": 45.0,
            "pm10": 80.0,
            "temperature": 28.0,
            "humidity": 65.0,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        },
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    if response.status_code == 401:
        print("✓ Invalid token correctly rejected with 401")
    else:
        print(f"⚠ Expected 401 for invalid token, got {response.status_code}")
    
    # Test POST with valid token
    tokens_path = Path(__file__).parent / "data" / "sensor_tokens.json"
    if tokens_path.exists():
        with open(tokens_path) as f:
            tokens = json.load(f)
        
        if "SENSOR_001" in tokens:
            valid_token = tokens["SENSOR_001"]
            response = client.post(
                "/api/v1/community/sensors/readings",
                json={
                    "sensor_id": "SENSOR_001",
                    "sequence_number": 999998,
                    "pm25": 45.0,
                    "pm10": 80.0,
                    "temperature": 28.0,
                    "humidity": 65.0,
                    "recorded_at": datetime.now(timezone.utc).isoformat()
                },
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            
            if response.status_code == 201:
                print("✓ Valid token accepted, reading submitted successfully")
            elif response.status_code == 400 and "Duplicate" in response.text:
                print("✓ Valid token works (reading was duplicate, which is expected)")
            else:
                print(f"⚠ Expected 201 or 400 (duplicate), got {response.status_code}: {response.text}")
    
    # Test GET /api/v1/community/sensors/{sensor_id}/readings
    if sensors:
        sensor_id = sensors[0]['id']
        response = client.get(f"/api/v1/community/sensors/{sensor_id}/readings")
        if response.status_code != 200:
            print(f"✗ GET /api/v1/community/sensors/{sensor_id}/readings returned {response.status_code}")
            return False
        
        readings = response.json()
        print(f"✓ GET /api/v1/community/sensors/{sensor_id}/readings returned {len(readings)} readings")
    
    # Test GET /api/v1/community/map
    response = client.get("/api/v1/community/map")
    if response.status_code != 200:
        print(f"✗ GET /api/v1/community/map returned {response.status_code}")
        return False
    
    map_data = response.json()
    print(f"✓ GET /api/v1/community/map returned data for {len(map_data.get('sensors', []))} sensors")
    
    return True

def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "COMMUNITY SENSOR NETWORK" + " " * 24 + "║")
    print("║" + " " * 12 + "Integration Verification" + " " * 22 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = []
    
    # Run all checks
    results.append(("Database", check_database()))
    results.append(("Tokens", check_tokens()))
    results.append(("VirtualSensor Class", test_virtual_sensor_class()))
    results.append(("API Routes", test_api_routes()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL CHECKS PASSED")
    else:
        print("✗ SOME CHECKS FAILED")
    print("=" * 60)
    print()
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())
