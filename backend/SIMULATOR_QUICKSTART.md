# Virtual Sensor Simulator - Quick Start Guide

## Overview

The virtual sensor simulator mimics real IoT air quality sensors submitting measurements to the backend API. It supports both system sensors (the original 10 Bengaluru sensors) and user-contributed sensors registered through the web UI.

## Running the Simulator

### Basic Usage

```bash
cd /home/vishwas/Desktop/CC/community-air-quality/backend
source .venv/bin/activate
python -m app.simulator.virtual_sensors --api-url http://localhost:8000
```

The simulator:
- Loads sensor tokens from `data/sensor_tokens.json`
- Fetches sensor metadata (including coordinates) from the API
- Submits readings every 5-10 seconds with coordinates included
- Shows sensor_id, sequence_number, PM2.5, and HTTP status for each submission

### Running Contributed Sensors

To simulate a user-contributed sensor:

#### 1. Register the sensor via web UI

1. Open http://localhost:3000/community
2. Click "Add Sensor" button
3. Fill in the form:
   - Sensor name: e.g., "My Home Sensor"
   - Hardware ID: e.g., "ESP32-HOME001"
   - Hardware model: e.g., "ESP32 + PMS5003"
   - Contributor name: e.g., "Your Name"
4. Click "Register Sensor"
5. Copy the sensor ID and authentication token from the success dialog

#### 2. Add credentials to tokens file

Edit `backend/data/sensor_tokens.json` and add your new sensor:

```json
{
  "SENSOR_001": "existing_token_here...",
  "SENSOR_002": "existing_token_here...",
  ...
  "SENSOR_011": "YOUR_NEW_TOKEN_HERE"
}
```

Replace `YOUR_NEW_TOKEN_HERE` with the token from the registration dialog.

#### 3. Run the simulator

```bash
python -m app.simulator.virtual_sensors --api-url http://localhost:8000
```

The simulator will:
- Automatically detect the new sensor
- Fetch its metadata from the API
- Start submitting readings with coordinates
- The sensor will appear on the map after the first reading

**Note:** The simulator loads location coordinates from the backend API. For contributed sensors, the first reading updates the sensor's location on the backend, which the simulator then uses for subsequent readings.

## How It Works

### Coordinates in Readings

All readings include latitude and longitude:

```json
{
  "sensor_id": "SENSOR_011",
  "sequence_number": 1,
  "pm25": 42.5,
  "pm10": 68.2,
  "temperature": 29.4,
  "humidity": 65.0,
  "latitude": 12.9352,
  "longitude": 77.6245,
  "recorded_at": "2024-11-13T08:30:00Z"
}
```

The simulator:
1. Fetches sensor metadata from `/api/v1/community/sensors`
2. Extracts latitude and longitude for each sensor
3. Includes these coordinates in every reading submission

For system sensors (SENSOR_001 through SENSOR_010), coordinates are fixed at registration. For contributed sensors, the first reading sets the sensor's location, and subsequent readings use those coordinates.

## Scenarios

### Pollution Spike

Temporarily increase PM2.5 by 40-80 for 60 seconds:

```bash
python -m app.simulator.virtual_sensors --spike SENSOR_011 --duration 60
```

Then run the simulator normally to submit the elevated readings.

### Sensor Disconnect

Stop a sensor from submitting readings:

```bash
python -m app.simulator.virtual_sensors --disconnect SENSOR_011
```

The sensor will not appear online in the frontend.

### Sensor Reconnect

Resume submissions from a disconnected sensor:

```bash
python -m app.simulator.virtual_sensors --reconnect SENSOR_011
```

## Verification

### Check readings stored

```bash
curl http://localhost:8000/api/v1/community/sensors/SENSOR_011/readings | jq
```

### Check sensor location updated

```bash
curl http://localhost:8000/api/v1/community/sensors/SENSOR_011 | jq '.latitude, .longitude'
```

### Check sensor on map

```bash
curl http://localhost:8000/api/v1/community/map | jq '.sensors[] | select(.id=="SENSOR_011")'
```

## Troubleshooting

### "Failed to fetch sensor metadata from API"

The backend isn't running or the API endpoint is incorrect. Start the backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### "401 Unauthorized" for contributed sensor

The token in `sensor_tokens.json` doesn't match the backend. Re-register the sensor or copy the correct token.

### Contributed sensor doesn't appear on map

1. Check that the simulator is running and submitting readings successfully (look for `✓` in simulator output)
2. Check that latitude and longitude are included in the reading (API will accept it if they are)
3. Refresh the frontend - sensors appear on map after first valid reading with coordinates

### Sensor shows "Awaiting first data"

The simulator hasn't submitted any readings yet, or submissions are failing. Check simulator output for errors.

## CLI Options

```bash
python -m app.simulator.virtual_sensors --help
```

- `--api-url`: Backend API base URL (default: http://localhost:8001)
- `--tokens-file`: Path to sensor tokens JSON file (default: data/sensor_tokens.json)
- `--spike SENSOR_ID`: Trigger pollution spike
- `--disconnect SENSOR_ID`: Stop sensor submissions
- `--reconnect SENSOR_ID`: Resume sensor submissions
- `--duration SECONDS`: Duration for spike scenario (default: 60)

## Implementation Details

The simulator:
- Generates gradual PM2.5 changes (±5 per iteration)
- Maintains PM10 at 1.3-2.0× PM2.5
- Temperature: 22-36°C (±1°C per iteration)
- Humidity: 35-85% (±3% per iteration)
- Sequence numbers increment monotonically
- Handles API errors gracefully
- Includes coordinates from sensor metadata in every reading
