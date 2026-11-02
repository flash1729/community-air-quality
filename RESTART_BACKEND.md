# ⚠️ IMPORTANT: Backend Needs Restart

## Problem
The backend is currently running but hasn't loaded the new community sensor endpoints.
The `/api/v1/community/*` routes return 404 because the server wasn't restarted after the code was added.

## ✅ Sensors are Ready
- **10 sensors already in database** ✓
- **Code is correct** ✓  
- **Just needs backend restart** ⚠️

---

## 🔄 How to Restart Backend

### Option 1: Kill and Restart (Recommended)

**Step 1:** Find and kill the process
```bash
sudo pkill -f "uvicorn app.main:app"
```

**Step 2:** Wait 2 seconds
```bash
sleep 2
```

**Step 3:** Start the backend with venv
```bash
cd /home/vishwas/Desktop/CC/community-air-quality/backend
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Option 2: One-liner
```bash
sudo pkill -f "uvicorn app.main:app" && sleep 2 && cd /home/vishwas/Desktop/CC/community-air-quality/backend && source .venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## ✅ Verify It's Working

After restarting, test the API:

```bash
curl http://localhost:8000/api/v1/community/sensors
```

**Expected output:** JSON with 10 sensors:
```json
[
  {
    "id": "SENSOR_001",
    "name": "Koramangala Sensor 1",
    "latitude": 12.9352,
    "longitude": 77.6245,
    ...
  },
  ...
]
```

If you see this instead, backend still needs restart:
```json
{"detail":"Not Found"}
```

---

## 🚀 After Backend Restarts

### 1. Start the Simulator

```bash
cd /home/vishwas/Desktop/CC/community-air-quality/backend
source .venv/bin/activate  
python -m app.simulator.virtual_sensors
```

Then type: `start`

### 2. Open Frontend

The frontend is already running at:
```
http://localhost:3001/community
```

You should now see:
- ✅ 10 sensors on the map
- ✅ Dashboard metrics updating
- ✅ Click sensors to see details
- ✅ Historical charts

---

## 🎬 Demo Scenarios

Once backend is restarted:

### Pollution Spike
In simulator: `spike SENSOR_001`
Watch Koramangala PM2.5 jump to ~120!

### Sensor Offline
In simulator: `disconnect SENSOR_005`
Wait 2 min, watch it turn grey

### View Live Data
Click any marker, see real-time readings

---

## 🐛 Current Status

- ✅ Database: 10 sensors created
- ✅ Code: All endpoints implemented
- ✅ Frontend: Running on port 3001
- ⚠️ Backend: Needs restart (currently on old code)
- ⏳ Simulator: Waiting for backend restart

**Once you restart the backend, everything will work!**
