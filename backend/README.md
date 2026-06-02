# AI Connect Backend

Self-hosted controller PoC for M5Atom Lite RS232 console bridges.

## Services

- `api`: FastAPI controller API
- `postgres`: persistent registry, claim, session, and audit storage
- `emqx`: MQTT broker, prepared for TLS on `8883`
- `caddy`: HTTPS reverse proxy for the API

## First Boot

```sh
cp .env.example .env
vi .env
docker compose up -d --build
docker compose ps
```

Health checks:

```sh
curl -H "Authorization: Bearer $API_ADMIN_TOKEN" http://127.0.0.1:8000/health
curl -H "Authorization: Bearer $API_ADMIN_TOKEN" http://127.0.0.1:8000/ready
```

Public API should be served by Caddy at:

```text
https://mqtts.itego.dk
```

MQTT TLS endpoint:

```text
mqtts://mqtts.itego.dk:8883
```

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
- `POST /v1/sites`
- `GET /v1/sites`
- `POST /v1/claim-codes`
- `GET /v1/claim-codes`
- `POST /v1/claim-codes/{claim_code_id}/revoke`
- `GET /v1/devices`
- `GET /v1/devices/{device_id}`
- `POST /v1/devices/{device_id}/disable`
- `POST /v1/devices/{device_id}/revoke`

Claim codes must be site-bound, random, one-time-use, and short-lived. The device never chooses organization or site; the operator assigns that through the backend by creating the claim code for a site.

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
- Current PoC ACL constrains topic shape by MQTT client id. Production must switch EMQX to PostgreSQL-backed authentication and authorization so issued credentials and device state (`claimed`, `disabled`, `revoked`) are enforced by the broker.
