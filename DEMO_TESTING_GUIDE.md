# Community Sensor Network - Demo Testing Guide

## 🚀 Quick Start

### Step 1: Restart Backend (Required - One Time)

The backend is currently running but needs to be restarted to load the new community sensor endpoints.

**In a terminal, run:**

```bash
# Stop the old backend
sudo pkill -f "uvicorn app.main:app"

# Start the new backend with community sensor routes
cd /home/vishwas/Desktop/CC/community-air-quality/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Verify backend is ready:**
```bash
curl http://localhost:8000/api/v1/community/sensors
```

You should see JSON with an empty `sensors` array or existing sensor data.

---

### Step 2: Start the Virtual Sensor Simulator

**In a new terminal:**

```bash
cd /home/vishwas/Desktop/CC/community-air-quality/backend
python -m app.simulator.virtual_sensors
```

**You'll see the interactive CLI:**
```
========================================
   Community Sensor Network Simulator
========================================

Commands:
  start              - Start sensor simulation
  pause              - Pause simulation
  resume             - Resume simulation
  stop               - Stop simulation
  spike <sensor_id>  - Trigger pollution spike (e.g., spike SENSOR_001)
  disconnect <id>    - Disconnect a sensor
  reconnect <id>     - Reconnect a sensor
  status             - Show current status
  quit               - Exit simulator

>
```

**Type:** `start` and press Enter

You should see sensors sending data:
```
[SENSOR_001] Sending: PM2.5=35.2, PM10=56.8, Temp=28.4°C, Humidity=62.3%
[SENSOR_002] Sending: PM2.5=42.1, PM10=68.5, Temp=29.1°C, Humidity=58.7%
✓ Successfully submitted 10 readings
```

---

### Step 3: Open the Community Network Dashboard

**Current Status:**
- ✅ Frontend is running on **http://localhost:3001**
- ⏳ Backend needs restart (see Step 1)

**Open in your browser:**
```
http://localhost:3001/community
```

---

## 🎬 Demo Testing Scenarios

### Scenario 1: View Live Sensor Data

**What to do:**
1. Open http://localhost:3001/community
2. Watch the dashboard metrics update every 5 seconds
3. Observe the map with 10 sensor markers across Bengaluru

**What you'll see:**
- **Total Sensors:** 10
- **Online Sensors:** 10 (when simulator is running)
- **Offline Sensors:** 0
- **Map markers** color-coded by PM2.5 levels:
  - 🟢 Green: < 30 µg/m³ (Good)
  - 🟡 Yellow: 30-60 µg/m³ (Moderate)
  - 🟠 Orange: 60-100 µg/m³ (Unhealthy for Sensitive)
  - 🔴 Red: > 100 µg/m³ (Unhealthy)
  - ⚫ Grey: Offline

---

### Scenario 2: View Sensor Details

**What to do:**
1. Click on any marker on the map (e.g., Koramangala Sensor 1)
2. View the sensor details panel on the right

**What you'll see:**
- Sensor name and location
- Latest PM2.5 and PM10 readings
- Temperature and humidity
- Last seen timestamp
- Status: Online
- Historical chart showing PM2.5 and PM10 trends over time

---

### Scenario 3: Simulate a Pollution Spike 🔥

This is the most impressive demo feature!

**What to do:**
1. In the simulator terminal, type: `spike SENSOR_001`
2. Watch the simulator output show increased readings
3. Switch to the browser and observe the changes

**What you'll see:**
1. **SENSOR_001 (Koramangala)** PM2.5 jumps from ~35 to ~120 µg/m³
2. Map marker turns **orange or red**
3. If you have that sensor selected, the chart shows a dramatic spike
4. Nearby sensors might show moderate increases
5. Distant sensors remain relatively unchanged

**This demonstrates:** Localized pollution event detection!

---

### Scenario 4: Simulate Sensor Failure

**What to do:**
1. In the simulator terminal, type: `disconnect SENSOR_005`
2. Wait 2+ minutes
3. Observe the dashboard

**What you'll see:**
1. SENSOR_005 (Marathahalli) stops sending data
2. After 2 minutes, its status changes to **Offline**
3. Map marker turns **grey**
4. Online sensors count decreases by 1
5. Offline sensors count increases by 1

**To restore:**
Type: `reconnect SENSOR_005`

---

### Scenario 5: Test Authentication

**What to do:**
Send a request with an invalid token:

```bash
curl -X POST http://localhost:8000/api/v1/community/sensors/readings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer INVALID_TOKEN" \
  -d '{
    "sensor_id": "SENSOR_001",
    "sequence_number": 999,
    "pm25": 50.0,
    "pm10": 80.0,
    "temperature": 28.5,
    "humidity": 65.0,
    "recorded_at": "2026-11-13T10:30:00Z"
  }'
```

**What you'll see:**
```json
{"detail": "Invalid sensor token"}
```

**This demonstrates:** Security - only authenticated sensors can submit data!

---

### Scenario 6: View Multiple Sensors Simultaneously

**What to do:**
1. Keep the simulator running continuously
2. Watch the map update every 5 seconds
3. Click different sensors to compare their readings

**What you'll see:**
- Gradual changes in PM2.5/PM10 (not random jumps)
- Different patterns across different locations
- Traffic-heavy areas (MG Road, Hebbal) might show higher readings
- Residential areas (Jayanagar, HSR Layout) might show lower readings

---

## 📊 All 10 Sensor Locations

| Sensor ID | Location | Coordinates | Area Type |
|-----------|----------|-------------|-----------|
| SENSOR_001 | Koramangala Sensor 1 | 12.9352°N, 77.6245°E | Residential |
| SENSOR_002 | Indiranagar Sensor 1 | 12.9716°N, 77.6412°E | Residential |
| SENSOR_003 | HSR Layout Sensor 1 | 12.9116°N, 77.6382°E | Residential |
| SENSOR_004 | Whitefield Sensor 1 | 12.9698°N, 77.7499°E | Commercial |
| SENSOR_005 | Marathahalli Sensor 1 | 12.9591°N, 77.6974°E | Traffic-heavy |
| SENSOR_006 | Electronic City Sensor 1 | 12.8458°N, 77.6603°E | Industrial |
| SENSOR_007 | Jayanagar Sensor 1 | 12.9250°N, 77.5937°E | Residential |
| SENSOR_008 | MG Road Sensor 1 | 12.9759°N, 77.6061°E | Traffic-heavy |
| SENSOR_009 | Hebbal Sensor 1 | 13.0358°N, 77.5970°E | Traffic-heavy |
| SENSOR_010 | Yelahanka Sensor 1 | 13.1007°N, 77.5963°E | Residential |

---

## 🛠️ Simulator CLI Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `start` | Begin sending sensor data | `start` |
| `pause` | Pause data transmission | `pause` |
| `resume` | Resume after pause | `resume` |
| `stop` | Stop simulator (can restart with `start`) | `stop` |
| `spike <sensor_id>` | Trigger pollution spike | `spike SENSOR_001` |
| `disconnect <sensor_id>` | Simulate sensor offline | `disconnect SENSOR_005` |
| `reconnect <sensor_id>` | Bring sensor back online | `reconnect SENSOR_005` |
| `status` | Show current state | `status` |
| `quit` | Exit simulator | `quit` |

---

## 🔍 API Endpoints for Manual Testing

### 1. List All Sensors
```bash
curl http://localhost:8000/api/v1/community/sensors
```

### 2. Get Sensor Details
```bash
curl http://localhost:8000/api/v1/community/sensors/SENSOR_001
```

### 3. Get Sensor Reading History
```bash
curl http://localhost:8000/api/v1/community/sensors/SENSOR_001/readings?limit=20
```

### 4. Get Map Data
```bash
curl http://localhost:8000/api/v1/community/map
```

### 5. Submit Reading (Authenticated)
```bash
# Get token from backend/data/sensor_tokens.json
TOKEN="your_sensor_token_here"

curl -X POST http://localhost:8000/api/v1/community/sensors/readings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "sensor_id": "SENSOR_001",
    "sequence_number": 1000,
    "pm25": 45.5,
    "pm10": 72.3,
    "temperature": 29.0,
    "humidity": 63.5,
    "recorded_at": "2026-11-13T10:30:00Z"
  }'
```

---

## 🎥 Suggested Demo Flow

### Opening (1 minute)
**"Official monitoring stations can't cover every neighborhood. Our Community Sensor Network changes that."**

1. Show the empty map or just official stations
2. Explain the problem: limited coverage, no neighborhood-level data

### The Solution (2 minutes)
**"We've deployed a network of community-operated air quality sensors."**

1. Open http://localhost:3001/community
2. Show 10 sensors across Bengaluru
3. Explain: "Each dot is an independent device with its own identity"
4. Click a sensor: "Real-time PM2.5, PM10, temperature, humidity"

### Live Data (2 minutes)
**"These sensors report every few seconds. Watch the readings update."**

1. Keep the page open
2. Point out: "Values change gradually, not randomly"
3. Show historical chart: "We track trends over time"
4. Show different sensors have different patterns

### Pollution Event (2 minutes)
**"Now watch what happens during a localized pollution event."**

1. Trigger: `spike SENSOR_001`
2. Watch Koramangala sensor spike to 120+ µg/m³
3. Point out: "Nearby sensors show moderate increase"
4. Point out: "Distant sensors unchanged"
5. **"This helps identify pollution hotspots!"**

### Reliability (1 minute)
**"The system handles sensor failures gracefully."**

1. Disconnect a sensor
2. Show offline detection
3. Show authentication rejection

### Closing (1 minute)
**"Complete IoT architecture: Device → Authentication → Validation → Database → Visualization"**

1. Explain this is a virtual simulator
2. Explain real ESP32 + PMS5003 sensors can replace the simulator
3. Same API, same architecture

---

## ✅ Success Checklist

Before your demo, verify:

- [ ] Backend restarted and responding to `/api/v1/community/sensors`
- [ ] 10 sensors seeded in database
- [ ] Simulator starts without errors
- [ ] Frontend accessible at http://localhost:3001/community
- [ ] Map displays 10 markers
- [ ] Dashboard metrics update every 5 seconds
- [ ] Clicking a marker shows details
- [ ] Historical chart displays
- [ ] Pollution spike command works
- [ ] Sensor disconnect/offline detection works

---

## 🐛 Troubleshooting

### Backend shows 404 for community endpoints
**Solution:** Backend not restarted. Run Step 1 above.

### Simulator can't connect
**Solution:** Check backend is running on port 8000.

### Frontend doesn't show sensors
**Solution:** Check browser console for errors. Verify backend is responding.

### Sensors not updating
**Solution:** Check simulator is in "running" state. Type `status` to verify.

### All sensors show offline
**Solution:** Simulator not sending data. Type `start` in simulator.

---

## 🎉 You're Ready!

The Community Sensor Network demonstrates:
- ✅ Complete IoT data flow
- ✅ Real-time monitoring
- ✅ Localized pollution detection
- ✅ Authentication and security
- ✅ Failure handling
- ✅ Production-ready architecture

Enjoy your demo! 🚀
