# Virtual Sensor Simulator

This simulator creates virtual IoT air quality sensors that submit realistic measurements to the Community Air Quality backend API.

## Prerequisites

1. Backend API must be running:
   ```bash
   cd backend
   source .venv/bin/activate
   uvicorn app.main:app --reload --port 8000
   ```

2. Sensors must be seeded (creates `data/sensor_tokens.json`):
   ```bash
   cd backend
   source .venv/bin/activate
   python -m app.seed_community_sensors
   ```

## Basic Usage

Run the simulator with default settings (submits readings every 5-10 seconds):

```bash
cd backend
source .venv/bin/activate
python -m app.simulator.virtual_sensors
```

The simulator will:
- Load 10 virtual sensors from `data/sensor_tokens.json`
- Fetch sensor metadata from the API
- Generate realistic measurements with gradual changes
- Submit authenticated readings every 5-10 seconds
- Log each submission with sensor ID, sequence number, and HTTP status

Press `Ctrl+C` to stop.

## Command Line Options

### API URL
Specify a different backend URL:
```bash
python -m app.simulator.virtual_sensors --api-url http://192.168.1.100:8000
```

### Tokens File
Use a different tokens file:
```bash
python -m app.simulator.virtual_sensors --tokens-file /path/to/tokens.json
```

### Pollution Spike Scenario
Trigger a pollution spike for a specific sensor:
```bash
python -m app.simulator.virtual_sensors --spike SENSOR_001 --duration 60
```
This raises PM2.5 by 40-80 µg/m³ for 60 seconds, then restores to normal levels.

### Disconnect Sensor
Mark a sensor as inactive (stops submissions):
```bash
python -m app.simulator.virtual_sensors --disconnect SENSOR_002
```

### Reconnect Sensor
Reactivate a disconnected sensor:
```bash
python -m app.simulator.virtual_sensors --reconnect SENSOR_002
```

## Measurement Behavior

### Gradual Changes
Measurements change gradually over time (not random jumps):
- **PM2.5**: ±5 µg/m³ per reading, bounded [10, 120]
- **PM10**: 1.3-2.0 × PM2.5, calculated per reading
- **Temperature**: ±1°C per reading, bounded [22, 36]
- **Humidity**: ±3% per reading, bounded [35, 85]

### Realistic Baselines
Each sensor initializes with realistic baseline values:
- PM2.5: 20-80 µg/m³
- PM10: 1.5-2.0 × initial PM2.5
- Temperature: 22-30°C
- Humidity: 40-70%

## Output Format

Normal operation:
```
✓ SENSOR_001 seq=42 PM2.5=45.23 status=201
✓ SENSOR_002 seq=38 PM2.5=67.89 status=201
✓ SENSOR_003 seq=51 PM2.5=34.12 status=201
```

API errors:
```
✗ SENSOR_004 seq=25 status=401 error=Invalid authentication token
✗ SENSOR_005 seq=30 error=ConnectionError: Failed to connect
```

Statistics (every 10 rounds):
```
📊 Stats: 98/100 successful (98.0%)
```

Spike events:
```
🔥 SENSOR_001 SPIKE triggered: PM2.5 45.2 → 98.7 for 60s
✓ SENSOR_001 SPIKE ended, restoring PM2.5 to ~45.2
```

## Testing

Run the test suite to verify simulator logic without API:
```bash
cd backend
./test_simulator.sh
```

This tests:
- Sensor loading
- Gradual change logic
- Spike scenarios
- Disconnect/reconnect functionality

## Architecture

### VirtualSensor Class
Each sensor maintains:
- **Identity**: sensor_id, name, token, coordinates
- **State**: PM2.5, PM10, temperature, humidity, sequence_number
- **Status**: active flag, spike timing

### Key Methods
- `generate_reading()`: Creates next reading with gradual changes
- `submit_reading(api_url)`: Authenticates and submits to API
- `trigger_spike(duration)`: Temporarily elevates PM2.5
- `check_spike_expiry()`: Restores normal levels after spike

### load_sensors()
1. Reads sensor tokens from JSON file
2. Fetches sensor metadata from GET /api/v1/community/sensors
3. Creates VirtualSensor instances
4. Returns list of initialized sensors

### Simulation Loop
1. Check for expired spikes on all sensors
2. Submit readings from active sensors
3. Log successes and failures
4. Sleep 5-10 seconds (random)
5. Repeat until Ctrl+C

## API Integration

### Authentication
Uses Bearer token authentication:
```
Authorization: Bearer {sensor_token}
```

### Endpoint
```
POST /api/v1/community/sensors/readings
Content-Type: application/json

{
  "sensor_id": "SENSOR_001",
  "sequence_number": 42,
  "pm25": 45.23,
  "pm10": 78.91,
  "temperature": 28.5,
  "humidity": 62.3,
  "recorded_at": "2024-01-15T10:30:00.000Z"
}
```

### Expected Responses
- **201**: Reading accepted
- **400**: Validation error (duplicate sequence, invalid values)
- **401**: Authentication failed (invalid token)
- **404**: Sensor not found

## Simulated Sensors

10 sensors across Bengaluru neighborhoods:

| Sensor ID   | Location       | Coordinates          |
|-------------|----------------|----------------------|
| SENSOR_001  | Koramangala    | (12.9352, 77.6245)   |
| SENSOR_002  | Indiranagar    | (12.9716, 77.6412)   |
| SENSOR_003  | HSR Layout     | (12.9116, 77.6382)   |
| SENSOR_004  | Whitefield     | (12.9698, 77.7499)   |
| SENSOR_005  | Marathahalli   | (12.9591, 77.6974)   |
| SENSOR_006  | Electronic City| (12.8458, 77.6603)   |
| SENSOR_007  | Jayanagar      | (12.9250, 77.5937)   |
| SENSOR_008  | MG Road        | (12.9759, 77.6061)   |
| SENSOR_009  | Hebbal         | (13.0358, 77.5970)   |
| SENSOR_010  | Yelahanka      | (13.1007, 77.5963)   |

## Error Handling

The simulator handles errors gracefully:
- **Network errors**: Logs and continues with other sensors
- **API errors**: Logs status code and continues
- **Invalid tokens**: Logs 401 and continues
- **Keyboard interrupt**: Displays final statistics and exits cleanly

No single sensor failure stops the entire simulation.
