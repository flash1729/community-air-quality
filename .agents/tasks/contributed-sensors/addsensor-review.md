# Add Sensor modal above the map, and random Bengaluru locations for new simulated sensors

The Add Sensor modal now renders through a portal on `document.body` at `z-[2000]`, which puts it above Leaflet's panes and controls. It uses the app's own primitives (`SectionHeading`, `Banner`, `.field`, `.btn`, `bg-surface-solid`), and it still has exactly the four requested fields. New sensors get a random Bengaluru location from the simulated device, not from the backend. When `SIMULATOR_AUTO_PROVISION` is on (default off, on in `docker-compose.yml`), registration writes the new token into a shared tokens file. The compose `simulator` service reloads that file every round, picks a random point in lat 12.85–13.10 / lon 77.50–77.75, saves it to `sensor_locations.json`, and posts readings only through the HTTP ingestion endpoint. The proxy keeps the `API_INTERNAL_URL` fix and now forwards `content-type`. Without that header, UI registrations failed with 422.

Watch for: on a fresh Docker volume the compose simulator has no seed-sensor tokens, so SENSOR_001..010 stop reporting until someone copies the files in by hand (confirmed). The host-side simulator and the compose simulator conflict over sequence numbers if both run (confirmed, documented). Every sensor still shows Offline because of a timezone parsing bug that predates this change (confirmed, out of scope).

**Verdict**: APPROVED

## High-level view

The modal portals to `document.body` above Leaflet's stacking contexts. While the dialog is open, every other body child is `inert` and body scroll is locked. Escape and backdrop clicks both close it, which also resets the form. Focus does not go back to the Add Sensor button when the dialog closes, and Escape works even while a submit is in flight.

The device chooses its own location, so registration still collects none and the backend learns coordinates only from readings. The simulator looks for a location in this order: the locations file, then the coordinates the backend already holds, then a random point at least 0.005° from every known sensor. The chosen point is saved and survives restarts. The weak spot is bootstrapping. Seed-sensor tokens reach the compose volume only through a manual copy step.

The backend-to-simulator handoff is a plaintext tokens file on the shared `air-data` volume. Auto-provisioning is off by default and the compose comment marks it as demo-only, which keeps credential exposure limited to local development. If writing the file fails, registration still succeeds and the backend only logs a warning. In that case the user's sensor would sit at "Awaiting first data" with no visible cause.

<details>
<summary>Issues (6)</summary>

1. **Seed tokens missing on a fresh volume** — `backend/data/` is gitignored and the Dockerfile only runs `mkdir -p /app/data`, so a clean `docker compose up` gives the simulator no tokens for SENSOR_001..010. Only contributed sensors would report. Bootstrap the volume from the seed step, or document the `docker compose cp` step in the README. Non-blocking (confirmed).
2. **Duplicate simulators** — if the host-side simulator runs alongside the compose one, they send the same seed-sensor sequence numbers and one of them gets `400 Duplicate sequence number`. Add the "stop the host simulator" note to the run docs, not only to verification.md. Non-blocking (confirmed).
3. **Silent provisioning failure** — if `provision_simulator_token` fails, the backend only logs a warning and returns success, so the sensor never reports and the UI gives no reason. Acceptable for a demo. Consider surfacing it in the response message. Non-blocking (confirmed).
4. **Focus not restored on close** — the modal focuses its first field on open but does not return focus to the Add Sensor button on close. Save `document.activeElement` on open and refocus it in the effect cleanup. Non-blocking (confirmed).
5. **Escape during submit loses the token** — if Escape is pressed while registration is in flight, the dialog closes and the request still succeeds, but the user never sees the token that is shown only once. Ignore Escape and backdrop clicks while `isSubmitting`. Non-blocking (confirmed).
6. **Per-process provisioning lock** — `_lock` serializes writes only within one process. Running uvicorn with multiple workers could drop a token entry when two registrations race. Use a file lock if multi-worker is ever enabled. Non-blocking (likely).

</details>

<details>
<summary>Details</summary>

### Portal, inert background and close behavior

The inert effect skips elements that are already inert, so its cleanup won't undo another component's inert state. Escape and backdrop clicks can close the dialog while a submit is in flight (confirmed). The request still finishes and calls `onSuccess`, so the sensor list refreshes, but the user never sees the token that is shown only once. Focus moves to the first input on open but is not restored to the trigger on close (confirmed).

### Simulator sync and location persistence

```
register (backend) ──writes──▶ /app/data/sensor_tokens.json ◀──reads every round── simulator
                                                                   │
                         /app/data/sensor_locations.json ◀──writes new random point
                                                                   │
                                     POST /api/v1/community/sensors/readings ──▶ backend
```

When the backend is unreachable, `sync_sensors` waits a round before starting new sensors instead of starting them at sequence 1, which avoids a burst of duplicate-sequence rejections. If 200 attempts all fail the separation check, `random_bengaluru_location` returns its last candidate anyway. The lock in `provision_simulator_token` is per process, so running uvicorn with multiple workers could lose a token entry if two registrations write at the same moment (likely). Compose runs a single worker today.

### Fresh-volume bootstrap gap

The coder's "one-time data step" seeded `sensor_tokens.json` and `sensor_locations.json` into the volume with `docker compose cp`. Nothing in the repo reproduces that step. `.gitignore` excludes `backend/data/`, and the image only creates an empty `/app/data`. On a fresh clone, the compose simulator starts with no tokens file, logs that it will keep checking, and reports only for sensors registered afterward. The ten Bengaluru seed sensors would stay without new readings. Their stored locations don't change, so the "seed sensors unaffected" requirement holds for location but not for liveness.

### Test coverage

The new tests cover provisioning on and off, random points staying inside the bounds and away from existing points, and a location persisting and being reused across a simulated restart. The coder recorded 34 passed. Not tested: sequence-number resume from `latest_reading`, deferral while the backend is unreachable, sensors stopping when they are removed from the tokens file, and the modal's Escape, backdrop and inert behavior (covered only by the manual headless-Chrome run).

### Out-of-scope observation

The coder flagged that the API emits naive UTC timestamps, which the browser parses as IST, so every sensor shows Offline. This predates the change and was correctly left alone, but it breaks the "show connection status" requirement from the original feature request and should be its own follow-up.

</details>

<details>
<summary>File map</summary>

- `frontend/src/components/community/AddSensorModal.tsx`: portal, inert/scroll lock, Escape/backdrop close, restyle with app primitives, field config array
- `frontend/src/app/community/page.tsx`: Add Sensor button uses `btn btn-primary` + `Plus` icon
- `frontend/src/app/api/v1/[...path]/route.ts`: `API_INTERNAL_URL` base, forwards `content-type`
- `backend/app/config.py`: `simulator_auto_provision`, `simulator_tokens_file`
- `backend/app/routers/community_sensors.py`: calls provisioning after registration commit
- `backend/app/simulator/provisioning.py`: atomic JSON write, token provisioning
- `backend/app/simulator/virtual_sensors.py`: per-round reload, random Bengaluru location, sequence resume
- `backend/tests/test_simulator_provisioning.py`: three new tests
- `docker-compose.yml`: auto-provision env on backend, new `simulator` service

Full diff: `git show 4032284`

</details>
