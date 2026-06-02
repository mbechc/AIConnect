# AI Connect Backend

Self-hosted controller PoC for M5Atom Lite RS232 console bridges.

## Services

- `api`: FastAPI controller API
- `mcp`: Model Context Protocol server for AI-assisted operations
- `postgres`: persistent registry, claim, session, and audit storage
- `emqx`: MQTT broker, prepared for TLS on `8883`
- `caddy`: HTTPS reverse proxy for the API

## First Boot

```sh
git clone https://github.com/mbechc/AIConnect.git
cd AIConnect/backend
cp .env.example .env
vi .env
docker compose up -d --build
docker compose ps
```

Smoke check after deploy:

```sh
./scripts/smoke-check.sh
```

Before starting the stack, replace every `change-me` value in `.env`. At minimum set:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`, using the same PostgreSQL password
- `API_ADMIN_TOKEN`
- `MQTT_BACKEND_PASSWORD`
- `MQTT_PROVISIONING_PASSWORD`
- `EMQX_DASHBOARD_PASSWORD`

Default host bindings keep the API, MCP, and EMQX dashboard on `127.0.0.1`. Caddy exposes the public HTTPS API. If you deliberately want to expose an admin surface directly, set the matching bind host to `0.0.0.0`:

- `API_BIND_HOST`
- `MCP_BIND_HOST`
- `EMQX_DASHBOARD_BIND_HOST`

Health checks:

```sh
curl -H "Authorization: Bearer $API_ADMIN_TOKEN" http://127.0.0.1:8000/health
curl -H "Authorization: Bearer $API_ADMIN_TOKEN" http://127.0.0.1:8000/ready
```

Public API should be served by Caddy at:

```text
https://mqtts.itego.dk
```

MCP endpoint, bound on the host network:

```text
http://<backend-host>:8001/mcp
```

MQTT TLS endpoint:

```text
mqtts://mqtts.itego.dk:8883
```

## Deploy And Upgrade

The deployable backend is fully described by this directory:

- `compose.yaml`
- `.env.example`
- `api/`
- `caddy/`
- `db/migrations/`
- `emqx/`
- `scripts/`
- `certs/README.md`

Runtime secrets and certificates are intentionally not committed:

- `.env`
- `certs/*.crt`
- `certs/*.key`
- `certs/*.pem`

Upgrade from Git:

```sh
cd /opt/aiconnect
git pull --ff-only
docker compose up -d --build
docker compose ps
```

The `migrate` service applies every SQL file in `db/migrations/` on each deploy before `api`, `mcp`, and `emqx` start. Migrations must remain idempotent because they are also used for fresh database initialization.

## MQTT Authentication

EMQX requires username/password authentication. Credentials are checked against PostgreSQL:

- Backend workers use `MQTT_BACKEND_USERNAME` / `MQTT_BACKEND_PASSWORD`.
- Unclaimed Bridges use `MQTT_PROVISIONING_USERNAME` / `MQTT_PROVISIONING_PASSWORD`.
- Claimed Bridges use per-device credentials generated during claim and stored by the Bridge until factory reset.

The provisioning credential is only allowed to publish `aic/v1/claim/request` and subscribe to `aic/v1/claim/response/{clientid}`. The Bridge must use its `device_id` as MQTT client id during provisioning so the response topic lines up.

Claimed Bridge credentials are only valid while the device row is `claimed`; disabled/revoked devices disappear from the EMQX auth views. Device ACL rows are scoped to `aic/v1/devices/{device_id}/...`.

## MCP Operations

The MCP server is intended to be the AI-facing operational frontend. It runs side-by-side with the API and exposes tools for:

- initial platform summary
- organization and site configuration
- claim-code creation for device onboarding
- device health and presence checks
- serial session open, transmit, close, and log inspection

The REST API remains the stable control plane. MCP tools should preserve the same tenant, claim, device-state, and MQTT topic contracts as the API.

## Topic Prefix

All MQTT topics are versioned under:

```text
aic/v1
```

Bootstrap claim topics:

- Device publishes: `aic/v1/claim/request`
- Backend publishes: `aic/v1/claim/response/{device_id}`

Claim request payload:

```json
{
  "device_id": "...",
  "efuse_mac": "...",
  "claim_code": "...",
  "firmware_version": "...",
  "hardware_model": "m5atom-lite-rs232"
}
```

Accepted claim responses keep the same fields as the shared device contract and include per-device MQTT credentials plus `status_topic` and `heartbeat_topic`.

Device-origin keepalive/presence topic:

- Device publishes heartbeat: `aic/v1/devices/{device_id}/heartbeat`

Heartbeat payload:

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

The backend updates `devices.last_seen_at` using server time for valid claimed-device messages on heartbeat, status, device event, and session-origin topics. API device responses derive `online`, `presence`, and `seconds_since_last_seen` from `last_seen_at`; online truth is not stored permanently.

Session direction:

- `tx`: backend to device serial port
- `rx`: device serial port to backend

## Admin API

All `/v1/*` routes require `Authorization: Bearer $API_ADMIN_TOKEN`.

- `POST /v1/organizations`
- `GET /v1/organizations`
- `PATCH /v1/organizations/{organization_id}`
- `POST /v1/sites`
- `GET /v1/sites`
- `PATCH /v1/sites/{site_id}`
- `POST /v1/claim-codes`
- `GET /v1/claim-codes`
- `POST /v1/claim-codes/{claim_code_id}/revoke`
- `GET /v1/devices`
- `GET /v1/devices/{device_id}`
- `POST /v1/devices/{device_id}/disable`
- `POST /v1/devices/{device_id}/factory-reset`

Claim codes must be site-bound, random, one-time-use, and short-lived. The device never chooses organization or site; the operator assigns that through the backend by creating the claim code for a site.

## Factory Reset

Admins and MCP operators can request a physical Bridge factory reset:

```sh
curl -X POST \
  -H "Authorization: Bearer $API_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason":"operator-request","delete_record":false}' \
  http://127.0.0.1:8000/v1/devices/DEVICE_ID/factory-reset
```

If the device is currently claimed and online, the backend publishes:

```text
aic/v1/devices/{device_id}/commands/factory-reset
```

Payload:

```json
{
  "command": "factory_reset",
  "device_id": "...",
  "reason": "...",
  "requested_at": "<backend-server-time>",
  "delete_record": false
}
```

The backend immediately revokes the device, clears stored MQTT credential material, marks active sessions failed with `factory-reset-requested`, and writes an audit event. The first implementation preserves device/session/event/audit history even when `delete_record` is requested; `delete_record` is passed to the Bridge command but no hard database delete is performed.

## Serial Audit Logging

Serial sessions are the audit trail for AI/operator interaction with the real device behind the Bridge. The backend logs:

- every backend-to-device serial input as `tx`
- every device-to-backend serial output as `rx`
- lifecycle events such as open requested, active, closed, failed, and factory reset requested

Serial log rows include session id, device id, actor type, optional actor id, direction, payload base64, text preview, byte count, metadata, and backend-created timestamp. Claim codes and MQTT passwords must not be written to serial logs.

## Manual Claim Verification

1. Confirm MQTT TLS is reachable:

   ```sh
   openssl s_client -connect mqtts.itego.dk:8883 -servername mqtts.itego.dk -brief </dev/null
   ```

2. Create an organization and site through the API.
3. Create a claim code with `site_id`.
4. Configure the device with controller host `mqtts.itego.dk` and the generated claim code.
5. Watch for audit rows:

   ```sh
   docker exec aiconnect-postgres-1 psql -U aiconnect -d aiconnect \
     -c "select actor_id, action, target_id, payload_json, created_at from audit_events order by id desc limit 20;"
   ```

6. Confirm the device appears as `claimed` and the claim code moved to `used`.

## PoC Security Notes

- Change all values in `.env`.
- Do not expose PostgreSQL.
- Keep EMQX dashboard bound to localhost or firewall protected.
- Use TLS on MQTT before field devices connect.
- Claim codes are stored as SHA-256 hashes.
- Do not log claim codes or issued MQTT passwords.
- EMQX uses PostgreSQL-backed authentication and authorization so issued credentials and device state (`claimed`, `disabled`, `revoked`) are enforced by the broker.
- Manual MQTT auth checks:
  - anonymous connection must fail
  - wrong password must fail
  - provisioning credential can only use claim topics
  - claimed credential can only use its own device topics
  - revoked credential must fail on reconnect
