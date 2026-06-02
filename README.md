# AI Connect

AI Connect turns an M5Atom Lite RS232 device into a secure remote console bridge for equipment that is difficult, slow, or risky to reach physically. The intent is to give an operator controlled serial access through a backend they manage, without making the field device responsible for deciding who owns it or which organisation it belongs to.

Security is the centre of the design. A backend may serve multiple organisations, so device ownership, MQTT permissions, claim codes, and serial sessions must all be scoped by backend-controlled identity and state. A MAC address or eFuse value can identify hardware, but it is not treated as a secret and must not grant ownership by itself.

Devices start unclaimed. An authenticated backend operator creates a short-lived, one-time claim code for the correct organisation/site. The operator enters that code in the device setup UI. The device then publishes a claim request over MQTT with its device identity and the claim code. If the backend accepts the claim, it binds the device to the selected site, marks the code used, and returns per-device MQTT credentials.

After claiming, the device uses the issued credentials for normal operation. It publishes status, heartbeat, and serial-session messages under the shared topic prefix:

```text
aic/v1
```

The heartbeat is both operationally useful and network-friendly. The device sends an application heartbeat while connected so firewalls and NAT mappings stay fresh, and the backend updates `last_seen_at` using server time whenever it receives a valid device message. Online/offline state is derived from the freshness of `last_seen_at`; it is not stored as permanent truth.

The device setup and diagnostics UI focuses on what the field operator needs to know:

- Wi-Fi and backend/controller configuration
- device ID and firmware version
- claim state
- backend/MQTT connection state
- last successful backend contact
- last MQTT error or disconnect reason

If the operator can reach the setup UI, Wi-Fi access to the device is assumed to exist. The important diagnostic question is whether the device is connected to the backend.

Claim request:

```text
Topic: aic/v1/claim/request
```

```json
{
  "device_id": "...",
  "efuse_mac": "...",
  "claim_code": "...",
  "firmware_version": "...",
  "hardware_model": "m5atom-lite-rs232"
}
```

Claim response:

```text
Topic: aic/v1/claim/response/{device_id}
```

Accepted responses include per-device MQTT credentials and the assigned heartbeat/status topics. Rejected responses include a machine-readable reason so the device UI can show a useful state such as claim required, claim rejected, or backend not configured.

Heartbeat:

```text
Topic: aic/v1/devices/{device_id}/heartbeat
```

```json
{
  "device_id": "...",
  "seq": 123,
  "uptime_ms": 123456,
  "wifi_rssi": -62,
  "firmware_version": "...",
  "state": "claimed"
}
```

Suggested timing:

- MQTT protocol keepalive: 30-60 seconds
- application heartbeat: every 30 seconds
- backend stale/offline threshold: 90-120 seconds without a valid message

This repository contains both sides of the system:

- `src/`: M5Atom Lite firmware
- `include/`: firmware version and contract constants
- `platformio.ini`: PlatformIO device build configuration
- `backend/`: FastAPI, PostgreSQL, EMQX, and Caddy backend stack
- `backend/db/migrations/`: backend schema migrations
- `backend/api/app/claim_worker.py`: MQTT claim handling
- `backend/api/app/device_message_worker.py`: heartbeat/status/session-origin message handling

Build firmware:

```sh
./platformio.sh run
```

Monitor device serial output:

```sh
./platformio.sh device monitor
```

Start the backend:

```sh
cd backend
cp .env.example .env
vi .env
docker compose up -d --build
```

Check backend health:

```sh
curl -H "Authorization: Bearer $API_ADMIN_TOKEN" http://127.0.0.1:8000/health
curl -H "Authorization: Bearer $API_ADMIN_TOKEN" http://127.0.0.1:8000/ready
```

The backend README has service-level details, API routes, and manual claim verification steps:

```text
backend/README.md
```

Current contract constants:

- firmware version: `0.2.2`
- contract version: `aic/v1`
- hardware model: `m5atom-lite-rs232`

Production hardening still matters before real field deployment:

- MQTT TLS must be enabled and validated.
- PostgreSQL must not be publicly exposed.
- claim codes must stay random, hashed at rest, short-lived, and one-time-use.
- issued MQTT passwords and claim codes must not be logged.
- broker authentication/authorization must enforce device state and topic scope.
- disabled or revoked devices must not be allowed to publish as claimed devices.
