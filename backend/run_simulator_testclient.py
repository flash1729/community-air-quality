#!/usr/bin/env python3
"""
Run the sensor simulator using TestClient to bypass the need for a running backend.
This submits readings directly to the API routes.
"""

import json
import time
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.simulator.virtual_sensors import VirtualSensor

def main():
    print("=" * 60)
    print("SENSOR SIMULATOR (TestClient Mode)")
    print("=" * 60)
    
    # Load tokens
    tokens_path = Path(__file__).parent / "data" / "sensor_tokens.json"
    with open(tokens_path) as f:
        tokens = json.load(f)
    
    print(f"✓ Loaded {len(tokens)} sensor tokens")
    
    # Create TestClient
    client = TestClient(app)
    
    # Load sensor metadata from API
    response = client.get("/api/v1/community/sensors")
    if response.status_code != 200:
        print(f"✗ Failed to fetch sensors: {response.status_code}")
        return 1
    
    sensor_data = response.json()
    print(f"✓ Loaded {len(sensor_data)} sensors from API")
    
    # Create VirtualSensor instances
    sensors = []
    for s in sensor_data:
        sensor_id = s['id']
        if sensor_id in tokens:
            vs = VirtualSensor(
                sensor_id=sensor_id,
                name=s['name'],
                token=tokens[sensor_id],
                latitude=s['latitude'],
                longitude=s['longitude']
            )
            sensors.append(vs)
    
    print(f"✓ Created {len(sensors)} virtual sensors")
    
    # Simulate for 30 seconds
    print("\nStarting simulation (30 seconds)...")
    print("=" * 60)
    
    start_time = time.time()
    iteration = 0
    total_submitted = 0
    total_rejected = 0
    
    while time.time() - start_time < 30:
        iteration += 1
        print(f"\n[Iteration {iteration}]")
        
        for sensor in sensors:
            if not sensor.active:
                continue
            
            reading = sensor.generate_reading()
            
            # Submit to API
            response = client.post(
                "/api/v1/community/sensors/readings",
                json=reading,
                headers={"Authorization": f"Bearer {sensor.token}"}
            )
            
            if response.status_code == 201:
                total_submitted += 1
                print(f"  ✓ {sensor.sensor_id}: PM2.5={reading['pm25']:.1f}, PM10={reading['pm10']:.1f}")
            else:
                total_rejected += 1
                print(f"  ✗ {sensor.sensor_id}: {response.status_code} - {response.json().get('detail', 'Unknown error')}")
        
        # Wait before next iteration (5 seconds between readings)
        time.sleep(5)
    
    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)
    print(f"Total iterations: {iteration}")
    print(f"Readings submitted: {total_submitted}")
    print(f"Readings rejected: {total_rejected}")
    print(f"Success rate: {total_submitted / (total_submitted + total_rejected) * 100:.1f}%")
    print()
    
    return 0

if __name__ == "__main__":
    exit(main())
