# Backend Prompt: AI Connect Bridge Diagnostic Tools

Implement the backend side for asynchronous Bridge diagnostics. The Bridge firmware side will implement `ping`, `dns_lookup`, and `tcp_connect`.

Scope:

- Backend only: API/MCP request handling, authorization, MQTT command publishing, result ingestion, storage, timeout handling, and audit logging.
- Do not change Bridge onboarding, claim, heartbeat, serial session, or factory reset contracts.
- Only claimed devices may receive diagnostic commands.
- The authenticated backend operator chooses the organisation/site/device. The Bridge never chooses tenant ownership.

MQTT command topic:

```text
aic/v1/devices/{device_id}/commands/diagnostic
```

Command payload:

```json
{
  "command": "diagnostic",
  "device_id": "...",
  "request_id": "...",
  "tool": "ping",
  "args": {
    "host": "8.8.8.8",
    "count": 4,
    "timeout_ms": 1000
  },
  "requested_at": "<backend-server-time>"
}
```

Supported tools:

- `dns_lookup`
  - args: `host`, optional `timeout_ms`
- `tcp_connect`
  - args: `host`, `port`, optional `timeout_ms`
- `ping`
  - args: `host`, optional `count`, optional `timeout_ms`

Bridge result topic:

```text
aic/v1/devices/{device_id}/events
```

Result payload:

```json
{
  "device_id": "...",
  "event": "diagnostic_result",
  "request_id": "...",
  "tool": "ping",
  "status": "completed",
  "uptime_ms": 123456,
  "duration_ms": 4021,
  "wifi_rssi": -62,
  "result": {
    "host": "8.8.8.8",
    "resolved_ip": "8.8.8.8",
    "sent": 4,
    "received": 4,
    "loss_percent": 0,
    "min_ms": 12,
    "avg_ms": 18,
    "max_ms": 31
  }
}
```

Rejected/failed payloads use the same topic and event with:

```json
{
  "device_id": "...",
  "event": "diagnostic_result",
  "request_id": "...",
  "tool": "tcp_connect",
  "status": "failed",
  "uptime_ms": 123456,
  "duration_ms": 1000,
  "wifi_rssi": -62,
  "reason": "connection timeout",
  "result": {
    "host": "example.com",
    "port": 443
  }
}
```

Backend requirements:

- Enforce operator authorization: operator -> organisation/site -> device.
- Publish diagnostics only to claimed, enabled devices.
- Generate globally unique `request_id`.
- Store request and result records with org/site/device/request/tool/status/timestamps.
- Mark a request timed out if no result arrives within the backend timeout window.
- Ingest only results from valid claimed-device MQTT credentials and authorized device topics.
- Treat `request_id` as idempotency key for result processing.
- Audit all requested diagnostics, rejected commands, completed results, failed results, and timeouts.
- Redact nothing sensitive in these payloads because no secrets are included, but do not add credentials to command or result payloads.
- Rate limit diagnostic commands per operator and per device.

Security constraints:

- Do not expose arbitrary command execution.
- Do not allow wildcard/global diagnostic commands.
- Do not allow diagnostics for unclaimed, disabled, or unauthorized devices.
- Do not allow Bridge-supplied org/site fields to influence storage or authorization.
- Backend must derive org/site from its own device record.

Contract Impact:

- MQTT topics changed: yes, add `aic/v1/devices/{device_id}/commands/diagnostic`
- JSON fields changed: yes, add diagnostic command/result payloads
- Database schema changed: yes, backend should add diagnostic request/result storage
- Device persisted settings changed: no
- Bridge update required: yes, subscribe to diagnostic command and publish `diagnostic_result` events
